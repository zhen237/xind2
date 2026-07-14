# -*- coding: utf-8 -*-
"""拓扑自动设计引擎 (T5)

支持 **星型(star) / 树型(tree) / 冗余(redundant)** 三种基站↔机房组网拓扑的自动生成。

设计对象：
- hub  ：中心节点（机房 / BBU 池 / 核心）
- sites：基站节点列表

输出结构：
- nodes：节点列表，每项 {"id","lon","lat","kind"}（kind∈ site|subhub|hub）
- edges：连接关系，每项 {"from","to","kind"}（kind∈ access|backhaul|ring）

纯标准库实现，不依赖 QGIS，可直接在沙箱单测。路网几何复用 T3 的 road_network。
"""

from typing import List, Dict, Optional, Tuple

try:
    from .road_network import haversine, route_between
except ImportError:
    from road_network import haversine, route_between


def _node(node_id: str, lon: float, lat: float, kind: str = "site") -> Dict:
    return {"id": node_id, "lon": lon, "lat": lat, "kind": kind}


# ============================================================
#  三种拓扑
# ============================================================

def design_star(sites: List[Dict], hub: Dict) -> Dict:
    """星型：每个基站直连中心节点（hub）。

    适用于站点少、对汇聚点依赖高的城域接入层。
    """
    edges = [{"from": s["id"], "to": hub["id"], "kind": "access"} for s in sites]
    return {"nodes": [dict(hub, kind="hub")] + [dict(s, kind="site") for s in sites],
            "edges": edges,
            "topology_type": "star"}


def design_tree(sites: List[Dict], hub: Dict, subhub_count: Optional[int] = None) -> Dict:
    """树型（分级汇聚）：基站→子汇聚点(subhub)→中心节点(hub)，两层树。

    适用于站点多、需分级收敛降低回传成本的场景。
    subhub 由站点中按经度均匀分布选取种子，其余站点就近归属。
    """
    if not sites:
        return {"nodes": [dict(hub)], "edges": [], "topology_type": "tree"}

    n = len(sites)
    k = subhub_count if subhub_count else max(1, n // 5)
    k = max(1, min(k, n))

    # 按经度排序后均匀取 k 个种子索引
    order_by_lon = sorted(range(n), key=lambda i: sites[i]["lon"])
    seed_idx = [order_by_lon[(i * n) // k] for i in range(k)]
    seed_site_ids = {sites[i]["id"] for i in seed_idx}

    subhubs = []
    for i, si in enumerate(seed_idx):
        sub = dict(sites[si])
        sub["id"] = "SUBHUB-%d" % (i + 1)
        sub["kind"] = "subhub"
        subhubs.append(sub)

    edges = []
    # 非种子站点就近归属 subhub
    for s in sites:
        if s["id"] in seed_site_ids:
            continue
        best = min(subhubs, key=lambda sh: haversine(s["lon"], s["lat"], sh["lon"], sh["lat"]))
        edges.append({"from": s["id"], "to": best["id"], "kind": "access"})
    # subhub 回传至 hub
    for sh in subhubs:
        edges.append({"from": sh["id"], "to": hub["id"], "kind": "backhaul"})

    return {"nodes": [dict(hub, kind="hub")] + [dict(s, kind="site") for s in sites] + subhubs,
            "edges": edges,
            "topology_type": "tree"}


def design_redundant(sites: List[Dict], hub: Dict) -> Dict:
    """冗余：星型接入 + 站点间环网(ring)，任一接入链路故障仍有备用路径。

    适用于对可靠性要求高的场景（如汇聚层双归）。
    """
    edges = [{"from": s["id"], "to": hub["id"], "kind": "access"} for s in sites]
    if len(sites) >= 3:
        # 按相对 hub 的方位角排序成环
        cx, cy = hub["lon"], hub["lat"]
        ring = sorted(sites, key=lambda s: __import__("math").atan2(
            s["lat"] - cy, s["lon"] - cx))
        for i in range(len(ring)):
            a = ring[i]
            b = ring[(i + 1) % len(ring)]
            edges.append({"from": a["id"], "to": b["id"], "kind": "ring"})
    return {"nodes": [dict(hub, kind="hub")] + [dict(s, kind="site") for s in sites],
            "edges": edges,
            "topology_type": "redundant"}


def design_topology(sites: List[Dict], hub: Dict,
                    topology_type: str = "star",
                    subhub_count: Optional[int] = None) -> Dict:
    """拓扑设计统一入口。

    Args:
        sites: 基站节点 [{"id","lon","lat"}, ...]
        hub: 中心节点 {"id","lon","lat"}
        topology_type: star | tree | redundant
        subhub_count: tree 模式下的子汇聚点数量（默认站点数//5）

    Returns:
        {"nodes":[...], "edges":[...], "topology_type":str}
    """
    if topology_type == "tree":
        return design_tree(sites, hub, subhub_count)
    if topology_type == "redundant":
        return design_redundant(sites, hub)
    # 默认 star
    return design_star(sites, hub)


# ============================================================
#  路网几何（复用 T3）
# ============================================================

def route_topology_edges(result: Dict,
                          road_segments: Optional[List[List[Tuple[float, float]]]] = None,
                          algorithm: str = "dijkstra") -> Dict:
    """为拓扑每条边计算地理路径（路网感知，复用 T3）。

    无 road_segments 时退化为直线 [from, to]，仅补充 distance_m（大圆距离）。

    Args:
        result: design_topology 的输出
        road_segments: 道路矢量路段（可选）
        algorithm: dijkstra | astar

    Returns:
        原 result 的浅拷贝，edges 每项附加 "coordinates" / "distance_m"
    """
    node_by_id = {nd["id"]: nd for nd in result["nodes"]}
    out = {"nodes": result["nodes"], "edges": [], "topology_type": result["topology_type"]}

    for edge in result["edges"]:
        a = node_by_id.get(edge["from"])
        b = node_by_id.get(edge["to"])
        coords = [(a["lon"], a["lat"]), (b["lon"], b["lat"])]
        distance_m = haversine(a["lon"], a["lat"], b["lon"], b["lat"])

        if road_segments and a and b:
            res = route_between((a["lon"], a["lat"]), (b["lon"], b["lat"]),
                                road_segments, algorithm=algorithm, snap=True)
            if res["found"]:
                coords = [(c[0], c[1]) for c in res["coordinates"]]
                distance_m = res["distance_m"]

        new_edge = dict(edge)
        new_edge["coordinates"] = coords
        new_edge["distance_m"] = round(distance_m, 2)
        out["edges"].append(new_edge)

    return out
