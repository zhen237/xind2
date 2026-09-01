"""greenfield 模式：由机房 + 管线网络自动合成 FTTH 设计（#5 Phase B）

输入：
  - room(s)        机房锚点（OLT 落点），来自 design_dock.machine_rooms
  - area_poly      设计区域面（[lon,lat] 外环）
  - pipelines      已布置管线（design_dock.generated_pipelines，Pipeline 对象，含 .coordinates）
  - buildings      可选：[lon,lat] 建筑轮廓中心；缺省时在区域内合成网格

输出（与 ftth/deliverables/ftth_json.py 字段兼容的设计产物，标注为「示意/设计产物」）：
  {
    "ZNRO": [ {lon,lat,name} ],            # OLT 覆盖范围节点（落机房）
    "FD":   [ {lon,lat,name} ],            # 光分纤箱级联点（沿管线取样）
    "IMB":  [ {lon,lat,name} ],            # 楼栋（覆盖对象）
    "CABLE":[ {coordinates:[[lon,lat]...], kind:"trunk"|"drop"} ],  # 光缆
    "stats": {...}
  }

设计原则：
  - 纯 Python，不依赖 shapely（离线/无第三方库环境可用）；点面判定用射线法。
  - 仅 greenfield 调用，brownfield 路径字节级不变。
  - 产物为「示意性设计」，供演示与出图，不作为竣工依据。
"""
import math
from typing import Dict, List, Optional, Tuple

Splitter = dict  # {lon,lat,name}


def _haversine_km(lon1, lat1, lon2, lat2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_in_polygon(lon, lat, poly: List[List[float]]) -> bool:
    """射线法判断点是否在多边形内（poly 为 [lon,lat] 外环闭合/不闭合均可）。"""
    if len(poly) < 3:
        return False
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i][0], poly[i][1]
        xj, yj = poly[j][0], poly[j][1]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def _bbox(poly: List[List[float]]) -> Tuple[float, float, float, float]:
    lons = [p[0] for p in poly]
    lats = [p[1] for p in poly]
    return min(lons), min(lats), max(lons), max(lats)


def _synth_buildings(area_poly: List[List[float]], grid_m: float = 90,
                      cap: int = 200) -> List[List[float]]:
    """在区域面内合成建筑轮廓中心网格（经纬度近似网格）。"""
    minx, miny, maxx, maxy = _bbox(area_poly)
    # 经纬度 → 米 近似（中纬度处）
    midlat = (miny + maxy) / 2
    dlon_m = 111320.0 * math.cos(math.radians(midlat))
    dlat_m = 110540.0
    pts: List[List[float]] = []
    lon = minx
    while lon <= maxx:
        lat = miny
        while lat <= maxy:
            if _point_in_polygon(lon, lat, area_poly):
                pts.append([lon, lat])
            lat += grid_m / dlat_m
        lon += grid_m / dlon_m
        if len(pts) >= cap:
            break
    return pts[:cap]


def _pipeline_nodes(pipelines) -> List[List[float]]:
    """从 Pipeline 对象列表抽取去重后的管线节点 [lon,lat]。"""
    seen = set()
    nodes: List[List[float]] = []
    for p in pipelines or []:
        coords = getattr(p, "coordinates", None) or []
        for c in coords:
            key = (round(c[0], 7), round(c[1], 7))
            if key not in seen:
                seen.add(key)
                nodes.append([c[0], c[1]])
    return nodes


def _nearest(pt: List[float], candidates: List[List[float]]) -> Optional[List[float]]:
    if not candidates:
        return None
    best, bd = None, float("inf")
    for c in candidates:
        d = _haversine_km(pt[0], pt[1], c[0], c[1])
        if d < bd:
            bd, best = d, c
    return best


def generate_ftth_design(
    rooms: List[dict],
    area_poly: List[List[float]],
    pipelines=None,
    buildings: Optional[List[List[float]]] = None,
    split_ratio: int = 8,
    building_grid_m: float = 90,
    fd_sample: int = 6,
) -> Dict:
    """合成 FTTH 设计。

    Args:
        rooms: 机房列表，每项 dict 含 room_id/name/longitude/latitude（MachineRoom.to_dict 兼容）。
        area_poly: 设计区域面 [lon,lat] 外环。
        pipelines: Pipeline 对象列表（含 .coordinates）；用于沿管线布放 FD 与主干走线。
        buildings: 可选建筑中心 [lon,lat]；缺省合成网格。
        split_ratio: 分光比（示意）。
        building_grid_m: 建筑合成网格间距（米）。
        fd_sample: 每隔多少管线节点取一个 FD（仅当 pipelines 非空）。
    """
    if not rooms:
        raise ValueError("greenfield 生成 FTTH 设计需要先布置至少 1 个机房（OLT 锚点）")
    if not area_poly or len(area_poly) < 3:
        raise ValueError("greenfield 生成 FTTH 设计需要先框选设计区域")

    # OLT 节点（取第一个机房为 OLT 局站，其余为接入机房）
    znro = []
    for i, r in enumerate(rooms):
        znro.append({
            "lon": float(r.get("longitude", 0)),
            "lat": float(r.get("latitude", 0)),
            "name": r.get("name", f"OLT-{r.get('room_id','?')}") if i == 0
                    else r.get("name", f"机房-{r.get('room_id','?')}"),
        })
    olt = znro[0]
    room_pts = [(z["lon"], z["lat"]) for z in znro]

    # FD（光分纤箱）：优先沿管线节点取样；无管线则在 OLT 附近生成单级
    nodes = _pipeline_nodes(pipelines)
    if nodes:
        fd_pts = nodes[::max(1, fd_sample)]
    else:
        fd_pts = [[olt["lon"] + 0.001, olt["lat"] + 0.001]]
    fd = [{"lon": p[0], "lat": p[1], "name": f"FD-{i+1:02d}"} for i, p in enumerate(fd_pts)]

    # 建筑（覆盖对象）
    if buildings is None:
        buildings = _synth_buildings(area_poly, grid_m=building_grid_m)
    imb = [{"lon": b[0], "lat": b[1], "name": f"楼栋-{i+1:03d}"} for i, b in enumerate(buildings)]

    # 光缆：主干 各FD→最近机房（#5：FD 接入最近基站下方的机房）；入户 FD→各楼栋
    cable = []
    for f in fd:
        tgt = _nearest([f["lon"], f["lat"]], room_pts) or (olt["lon"], olt["lat"])
        cable.append({
            "coordinates": [[tgt[0], tgt[1]], [f["lon"], f["lat"]]],
            "kind": "trunk",
        })
    # 每个楼栋挂到最近 FD（不足时用 OLT 兜底）
    drop_targets = fd if fd else [olt]
    for b in imb:
        tgt = _nearest([b["lon"], b["lat"]], [(d["lon"], d["lat"]) for d in drop_targets]) \
            or (olt["lon"], olt["lat"])
        cable.append({
            "coordinates": [[b["lon"], b["lat"]], [tgt[0], tgt[1]]],
            "kind": "drop",
        })

    trunk_len = sum(_haversine_km(c["coordinates"][0][0], c["coordinates"][0][1],
                                  c["coordinates"][1][0], c["coordinates"][1][1])
                     for c in cable if c["kind"] == "trunk")
    drop_len = sum(_haversine_km(c["coordinates"][0][0], c["coordinates"][0][1],
                                 c["coordinates"][1][0], c["coordinates"][1][1])
                   for c in cable if c["kind"] == "drop")

    return {
        "ZNRO": znro,
        "FD": fd,
        "IMB": imb,
        "CABLE": cable,
        "stats": {
            "olt_count": len(znro),
            "fd_count": len(fd),
            "building_count": len(imb),
            "trunk_cables": sum(1 for c in cable if c["kind"] == "trunk"),
            "drop_cables": sum(1 for c in cable if c["kind"] == "drop"),
            "trunk_length_km": round(trunk_len, 3),
            "drop_length_km": round(drop_len, 3),
            "split_ratio": split_ratio,
            "note": "greenfield 设计产物（示意），非竣工依据",
        },
    }
