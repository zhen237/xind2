"""CAD + GIS 数据融合引擎（FR-6 / FR-7）

融合规则（按需求文档 §4.3）：
  1. GIS 既有数据优先 —— GIS 要素全部保留；
  2. 同名同位置(<5m)去重 —— CAD 要素与 GIS 要素名称相同且几何距离 < 5m 时，
     丢弃 CAD 要素（保留 GIS）；
  3. 属性冲突标记 —— 名称相同、几何相近(≥5m 且 <50m)但属性不一致时，
     该要素 properties.fusion_conflict = "待人工审核"；
  4. 记录冲突数量 —— 输出统计（保留/去重/冲突/新增）。
"""

import math

DEDUP_TOLERANCE_M = 5.0        # 同名同位置去距离容差
CONFLICT_NEAR_M = 50.0         # 名称相同的“邻近”判定范围


def _feat_name(props):
    """要素名称：label / name / well 编号，任取其一。"""
    for key in ("label", "name", "编号", "well_no"):
        if props.get(key):
            return str(props[key])
    return None


def _nearest_distance_m(feat_a, feat_b):
    """两个经纬度要素顶点间的最小距离（米，球面近似）。"""
    best = float("inf")
    for geom in (feat_a["geometry"], feat_b["geometry"]):
        pass  # 占位，实际下方直接取坐标
    ca = _all_coords(feat_a["geometry"])
    cb = _all_coords(feat_b["geometry"])
    for (lon1, lat1) in ca:
        for (lon2, lat2) in cb:
            d = _haversine_m(lon1, lat1, lon2, lat2)
            if d < best:
                best = d
    return best


def _all_coords(geometry):
    gtype = geometry["type"]
    if gtype == "Point":
        return [geometry["coordinates"]]
    if gtype == "LineString":
        return geometry["coordinates"]
    if gtype == "Polygon":
        return geometry["coordinates"][0]
    # Multi* 兜底
    coords = []
    for part in geometry["coordinates"]:
        if isinstance(part[0], (int, float)):
            coords.append(part)
        else:
            coords.extend(part)
    return coords


def _haversine_m(lon1, lat1, lon2, lat2):
    r = 6378137.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _attr_conflict(props_a, props_b):
    """同名要素属性冲突判定：比较共有键值。"""
    keys = ("floors", "usage", "voltage_kv", "well_type", "road_class", "elevation")
    diffs = []
    for k in keys:
        va, vb = props_a.get(k), props_b.get(k)
        if va is not None and vb is not None and va != vb:
            diffs.append({"field": k, "gis_value": vb, "cad_value": va})
    return diffs


def fuse(cad_fc, gis_fc, dedup_tol_m=DEDUP_TOLERANCE_M):
    """融合 CAD 与 GIS 两个 GeoJSON FeatureCollection。

    返回 (merged_fc, stats)。merged_fc 中要素 properties 带 fusion_action：
      kept_gis / added_from_cad / deduped / conflict_review
    """
    cad_feats = cad_fc["features"] if isinstance(cad_fc, dict) else cad_fc
    gis_feats = gis_fc["features"] if isinstance(gis_fc, dict) else gis_fc

    merged = []
    stats = {"gis_kept": 0, "cad_added": 0, "deduped": 0,
             "conflict": 0, "conflict_details": []}

    # ① GIS 既有数据优先：全部保留
    for g in gis_feats:
        props = dict(g.get("properties") or {})
        props["fusion_action"] = "kept_gis"
        props["source"] = props.get("source", "GIS")
        merged.append({"type": "Feature", "geometry": g["geometry"],
                       "properties": props})
        stats["gis_kept"] += 1

    # ② ③ 逐个 CAD 要素判定
    for c in cad_feats:
        props = dict(c.get("properties") or {})
        name = _feat_name(props)
        action = "added_from_cad"
        min_d, near_gis = float("inf"), None
        for g in gis_feats:
            gname = _feat_name(g.get("properties") or {})
            if name and gname and name == gname:
                d = _nearest_distance_m(c, g)
                if d < min_d:
                    min_d, near_gis = d, g

        if near_gis is not None:
            if min_d < dedup_tol_m:
                # 同名同位置 → 去重，GIS 优先
                action = "deduped"
                stats["deduped"] += 1
            else:
                # 名称相同但不重叠：保留 CAD，但检查属性冲突
                diffs = _attr_conflict(props, near_gis.get("properties") or {})
                if diffs and min_d < CONFLICT_NEAR_M:
                    action = "conflict_review"
                    props["fusion_conflict"] = "待人工审核"
                    props["conflict_fields"] = diffs
                    stats["conflict"] += 1
                    stats["conflict_details"].append({
                        "name": name,
                        "distance_m": round(min_d, 2),
                        "fields": diffs,
                    })

        if action != "deduped":
            props["fusion_action"] = action
            props["source"] = props.get("source", "CAD")
            merged.append({"type": "Feature", "geometry": c["geometry"],
                           "properties": props})
            if action == "added_from_cad":
                stats["cad_added"] += 1

    merged_fc = {
        "type": "FeatureCollection",
        "name": "fusion_result",
        "fusion_stats": {
            "total_features": len(merged),
            "gis_kept": stats["gis_kept"],
            "cad_added": stats["cad_added"],
            "deduped": stats["deduped"],
            "conflict": stats["conflict"],
        },
        "conflict_details": stats["conflict_details"],
        "features": merged,
    }
    return merged_fc, stats
