"""正向智能规划设计器 (Forward Planning Engine).

与竣工 reverse 工程相反：本模块从「需求侧」出发，遮住已建好的箱位/缆路，
仅用住户需求点 (IMB) + 区域容量 (ZPM) + 固定局站 (SITE)，自动推导：

  1. 分层设施选址  PBO(终端箱) ← 住户聚类中心 ; BPE(分支箱) ← PBO 聚合 ; SITE 固定
  2. 容量规划      户数 → PBO 端口 ; 汇聚比 → BPE 芯数档位
  3. 树形路由      PBO 挂靠最近 BPE(配线) ; BPE 挂靠最近 SITE(主干)
  4. 对比评估      算法方案 vs 真实竣工 (箱数/缆长/覆盖率/聚类纯度)

纯标准库实现 (math + 自写 K-means)，无第三方依赖。
"""

import math
from collections import defaultdict

EARTH_R = 6371000.0  # 米


def haversine(a, b):
    """两点 (lon,lat) 大圆距离，单位米。"""
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(h)))


def _nearest(points, q):
    """返回 points 中离 q 最近的下标与距离。points: [(lon,lat), ...]"""
    best_i, best_d = 0, float("inf")
    for i, p in enumerate(points):
        d = haversine(p, q)
        if d < best_d:
            best_i, best_d = i, d
    return best_i, best_d


def kmeans(coords, k, n_iter=50, seed=7):
    """极简 K-means (K-means++ 初始化)。coords: [(lon,lat), ...]。
    返回 (centers[(lon,lat)...], labels[每个点所属簇])。k<=样本数时有效。"""
    n = len(coords)
    if n == 0:
        return [], []
    k = max(1, min(k, n))
    # K-means++ 初始化
    centers = [coords[seed % n]]
    while len(centers) < k:
        d2 = []
        for p in coords:
            best = min(haversine(p, c) ** 2 for c in centers)
            d2.append(best)
        total = sum(d2) or 1.0
        r = (seed * 2654435761 % 1000) / 1000.0 * total
        acc = 0.0
        for i, v in enumerate(d2):
            acc += v
            if acc >= r:
                centers.append(coords[i])
                break
        else:
            centers.append(coords[-1])
    labels = [0] * n
    for _ in range(n_iter):
        # 分配
        changed = False
        for i, p in enumerate(coords):
            bi, _ = _nearest(centers, p)
            if labels[i] != bi:
                labels[i] = bi
                changed = True
        # 更新
        for c in range(k):
            xs = [coords[i][0] for i in range(n) if labels[i] == c]
            ys = [coords[i][1] for i in range(n) if labels[i] == c]
            if xs:
                centers[c] = (sum(xs) / len(xs), sum(ys) / len(ys))
        if not changed and _ > 0:
            break
    return centers, labels


# 标准容量档位
PBO_PORT_TIERS = [10, 24, 48, 96]
BPE_CORE_TIERS = [144, 288, 576]


def _tier(value, tiers):
    for t in tiers:
        if value <= t:
            return t
    return tiers[-1]


def _zpm_of_point(lon, lat, zpm_shapes):
    """返回包含该点的 ZPM code (point-in-polygon)，无则 None。zpm_shapes: {code: [(lon,lat)...]}"""
    for code, poly in zpm_shapes.items():
        if _point_in_polygon(lon, lat, poly):
            return code
    return None


def _point_in_polygon(lon, lat, poly):
    """射线法。poly: [(lon,lat), ...] 闭合或不闭合均可。"""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def load_zpm_shapes(shape_dir):
    """用 pyshp 读 ZPM 多边形坐标。缺失返回 {}。"""
    try:
        import shapefile
    except ImportError:
        return {}
    import os
    path = os.path.join(shape_dir, "ZPM.shp")
    if not os.path.exists(path):
        return {}
    out = {}
    try:
        sf = shapefile.Reader(path)
        field_names = [f[0] for f in sf.fields[1:]]
        for rec in sf.shapeRecords():
            rd = rec.record
            if hasattr(rd, "as_dict"):
                d = rd.as_dict()
            elif hasattr(rd, "_asdict"):
                d = rd._asdict()
            else:
                d = {k: v for k, v in zip(field_names, rd)}
            code = d.get("CODE") or d.get("code")
            pts = [(p[0], p[1]) for p in rec.shape.points]
            if code and pts:
                out[code] = pts
    except Exception:
        return {}
    return out


DEFAULT_PARAMS = {
    "pbo_max_homes": 24,     # 单 PBO 目标覆盖户数 → 决定 PBO 数量
    "bpe_fanout": 6,         # 单 BPE 挂接的 PBO 数 → 决定 BPE 数量
    "split_ratio": 8,        # 汇聚比 → BPE 芯数 = 下级总户数 / split_ratio
    "coverage_radius_m": 350,  # PBO 覆盖半径 → 覆盖率判定
}


def plan_project(proj, shape_dir=None, params=None):
    """主入口：返回规划结果 dict。"""
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update({k: v for k, v in params.items() if k in DEFAULT_PARAMS})

    imbs = getattr(proj, "imbs", {}) or {}
    sites = getattr(proj, "sites", {}) or {}

    # ---- 需求点 ----
    demand = []
    for code, r in imbs.items():
        try:
            x = float(r.get("X"))
            y = float(r.get("Y"))
        except (TypeError, ValueError):
            continue
        homes = float(r.get("NB_LOC_RES") or r.get("NB_LOC_TOT") or 0) or 0
        demand.append({
            "code": code,
            "x": x, "y": y,
            "homes": int(homes),
            "real_bpe": (r.get("BPE_CODE") or "").strip() or None,
        })
    if not demand:
        return {"params": p, "demand_points": [], "planned_boites": [],
                "planned_cables": [], "comparison": {}, "error": "no demand points"}

    coords = [(d["x"], d["y"]) for d in demand]
    total_homes = sum(d["homes"] for d in demand)

    # ---- ZPM 归属 (决定 pm 域) ----
    zpm_shapes = load_zpm_shapes(shape_dir) if shape_dir else {}
    zpm_lookup = {}
    for d in demand:
        zpm_lookup[d["code"]] = _zpm_of_point(d["x"], d["y"], zpm_shapes)

    # ---- 1. PBO 选址 (住户聚类) ----
    k_pbo = max(1, math.ceil(total_homes / max(1, p["pbo_max_homes"]))) if total_homes else len(demand)
    k_pbo = min(k_pbo, len(demand))
    pbo_centers, pbo_labels = kmeans(coords, k_pbo)

    pbo_list = []
    pbo_by_label = defaultdict(list)
    for i, d in enumerate(demand):
        pbo_by_label[pbo_labels[i]].append(d)
    for lbl, members in pbo_by_label.items():
        cx, cy = pbo_centers[lbl]
        homes = sum(m["homes"] for m in members)
        near_site_i, _ = _nearest([(s.get("X"), s.get("Y")) for s in sites.values()], (cx, cy))
        site_codes = list(sites.keys())
        parent_site = site_codes[near_site_i] if site_codes else None
        zpm = zpm_lookup.get(members[0]["code"])
        pbo_list.append({
            "code": f"PLAN-PBO-{lbl+1:03d}",
            "type": "PBO",
            "x": cx, "y": cy,
            "homes": homes,
            "capacity_ports": _tier(max(homes, 1), PBO_PORT_TIERS),
            "members": [m["code"] for m in members],
            "parent_site": parent_site,
            "zpm": zpm,
        })

    # ---- 2. BPE 选址 (PBO 聚合) ----
    pbo_coords = [(b["x"], b["y"]) for b in pbo_list]
    k_bpe = max(1, math.ceil(len(pbo_list) / max(1, p["bpe_fanout"])))
    k_bpe = min(k_bpe, len(pbo_list))
    bpe_centers, bpe_labels = kmeans(pbo_coords, k_bpe)
    bpe_by_label = defaultdict(list)
    for i, b in enumerate(pbo_list):
        bpe_by_label[bpe_labels[i]].append(b)
    bpe_list = []
    for lbl, children in bpe_by_label.items():
        cx, cy = bpe_centers[lbl]
        homes = sum(c["homes"] for c in children)
        cores = math.ceil(homes / max(1, p["split_ratio"]))
        near_site_i, _ = _nearest([(s.get("X"), s.get("Y")) for s in sites.values()], (cx, cy))
        site_codes = list(sites.keys())
        parent_site = site_codes[near_site_i] if site_codes else None
        zpm = children[0]["zpm"]
        code = f"PLAN-BPE-{lbl+1:03d}"
        bpe_list.append({
            "code": code,
            "type": "BPE",
            "x": cx, "y": cy,
            "homes": homes,
            "capacity_cores": _tier(cores, BPE_CORE_TIERS),
            "children": [c["code"] for c in children],
            "parent_site": parent_site,
            "zpm": zpm,
        })
        for c in children:
            c["parent_bpe"] = code

    site_list = []
    for code, s in sites.items():
        try:
            sx, sy = float(s.get("X")), float(s.get("Y"))
        except (TypeError, ValueError):
            continue
        site_list.append({"code": code, "type": "SITE", "x": sx, "y": sy})

    # ---- 3. 树形路由 ----
    cables = []
    # PBO -> 最近 BPE (配线)
    for b in pbo_list:
        bi, d = _nearest([(c["x"], c["y"]) for c in bpe_list], (b["x"], b["y"]))
        tgt = bpe_list[bi]
        cables.append({
            "from": [b["x"], b["y"]],
            "to": [tgt["x"], tgt["y"]],
            "from_code": b["code"], "to_code": tgt["code"],
            "type": "DISTRIBUTION",
            "length_m": round(d),
        })
    # BPE -> 最近 SITE (主干)
    for c in bpe_list:
        si, d = _nearest([(s["x"], s["y"]) for s in site_list], (c["x"], c["y"]))
        tgt = site_list[si]
        cables.append({
            "from": [c["x"], c["y"]],
            "to": [tgt["x"], tgt["y"]],
            "from_code": c["code"], "to_code": tgt["code"],
            "type": "TRANSPORT",
            "length_m": round(d),
        })

    # ---- 4. 对比评估 ----
    comp = _evaluate(proj, pbo_list, bpe_list, cables, demand, p, zpm_lookup)

    return {
        "params": p,
        "demand_points": demand,
        "planned_boites": site_list + bpe_list + pbo_list,
        "planned_cables": cables,
        "comparison": comp,
        "zpm_shapes_available": bool(zpm_shapes),
    }


def _evaluate(proj, pbo_list, bpe_list, cables, demand, params, zpm_lookup):
    """算法 vs 真实竣工。"""
    boites = getattr(proj, "boites", {}) or {}
    real_pbo = sum(1 for b in boites.values() if (b.get("TYPE_BOITE") or b.get("TYPE") or "") == "PBO")
    real_bpe = sum(1 for b in boites.values() if (b.get("TYPE_BOITE") or b.get("TYPE") or "") == "BPE")
    # 真实缆长
    cables_real = getattr(proj, "cables", {}) or {}
    real_len = 0.0
    for c in cables_real.values():
        try:
            real_len += float(c.get("LONGUEUR") or 0) or 0.0
        except (TypeError, ValueError):
            pass
    if real_len == 0.0:  # 回退坐标算
        for c in cables_real.values():
            o = c.get("ORIGINE"); e = c.get("EXTREMITE")
            # 没有坐标则跳过
    plan_len = sum(c["length_m"] for c in cables)

    # 覆盖率：IMB 到其 PBO 距离 < coverage_radius
    pbo_coords = [(b["x"], b["y"]) for b in pbo_list]
    covered = 0
    for d in demand:
        _, dist = _nearest(pbo_coords, (d["x"], d["y"]))
        if dist <= params["coverage_radius_m"]:
            covered += 1
    coverage_rate = covered / len(demand) if demand else 0.0

    # 聚类纯度：每个 PBO 簇映射到占多数的真实 BPE_CODE
    purity = 0.0
    if demand and any(d["real_bpe"] for d in demand):
        correct = 0
        for b in pbo_list:
            votes = defaultdict(int)
            for mcode in b["members"]:
                rb = next((d["real_bpe"] for d in demand if d["code"] == mcode), None)
                if rb:
                    votes[rb] += 1
            if votes:
                majority = max(votes.values())
                correct += majority
        total_labeled = sum(1 for d in demand if d["real_bpe"])
        purity = correct / total_labeled if total_labeled else 0.0

    return {
        "pbo_planned": len(pbo_list),
        "pbo_real": real_pbo,
        "bpe_planned": len(bpe_list),
        "bpe_real": real_bpe,
        "cable_len_planned_m": round(plan_len),
        "cable_len_real_m": round(real_len),
        "coverage_rate": round(coverage_rate, 4),
        "cluster_purity": round(purity, 4),
        "demand_count": len(demand),
        "total_homes": sum(d["homes"] for d in demand),
    }


def export_plan_json(proj, out_path, shape_dir=None, params=None):
    import json
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    result = plan_project(proj, shape_dir=shape_dir, params=params)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from ftth.loader import load_dbf
    proj = load_dbf(r"docs/真实数据/Plan_de_récolement/Shape")
    res = plan_project(proj, shape_dir=r"docs/真实数据/Plan_de_récolement/Shape")
    import json
    print(json.dumps(res["comparison"], ensure_ascii=False, indent=2))
