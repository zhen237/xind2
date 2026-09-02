"""图层分类与属性映射（FR-2 / FR-3）

按 cad_layer_mapping.yml 的图层模式匹配规则，把解析出的实体分类到
6 类标准要素（建筑轮廓/道路中心线/电力线路/管井/等高线/红线），
并按配置提取属性（楼层/用途/电压等级/高程等）。
"""

import fnmatch
import os
import re

import yaml

MAPPING_FILE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "cad_layer_mapping.yml")

SIX_TYPES = ("building_outline", "road_centerline", "power_line",
             "well_point", "contour", "redline")


def _point_in_polygon(px, py, pts):
    """射线法判断点是否在多边形内（含边界近似）。"""
    n, inside = len(pts), False
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > py) != (yj > py)) and \
                (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _text_feature_distance(tx, ty, feat):
    """文本点到要素的距离：点在（闭合）面内取 0，否则取最近顶点距离。"""
    pts = feat["points"]
    if feat["closed"] and len(pts) >= 3 and _point_in_polygon(tx, ty, pts):
        return 0.0
    return min(((px - tx) ** 2 + (py - ty) ** 2) ** 0.5 for (px, py) in pts)


def load_mapping(path=None):
    if path is None:
        path = MAPPING_FILE
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def match_feature_type(layer_name, mapping):
    """按图层名（不区分大小写）匹配要素类型，返回类型键或 None。"""
    low = layer_name.lower()
    for ftype, conf in mapping.get("feature_types", {}).items():
        for pattern in conf.get("layer_patterns", []):
            if fnmatch.fnmatch(low, pattern.lower()) or fnmatch.fnmatch(
                    low, ("*" + pattern.lower() + "*")):
                return ftype
    return None


def _extract_attr(rule, entity, layer_name):
    """按单条属性规则提取值：正则提取或缺省。"""
    if not isinstance(rule, dict):
        return rule
    pattern = rule.get("pattern")
    source = rule.get("from", "layer_name")
    if pattern:
        text = ""
        if source == "layer_name":
            text = layer_name
        elif source == "entity_text":
            text = entity.get("text") or ""
        elif source == "entity_elevation":
            try:
                return float(entity.get("elevation") or 0)
            except (TypeError, ValueError):
                return rule.get("default", 0)
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1) if m.groups() else m.group(0)
            try:
                return float(raw) if "." in str(raw) else int(raw)
            except ValueError:
                return raw
    if "default" in rule:
        return rule["default"]
    return None


def _geometry_for(entity, ftype, geom_conf):
    """由实体与配置几何类型决定 GeoJSON 几何类型。"""
    conf_geom = geom_conf  # Polygon / LineString / Point
    n = len(entity["points"])
    if conf_geom == "Point":
        return "Point"
    if conf_geom == "Polygon":
        # 闭合或 >=3 点的按面处理；仅 2 点的退化为线
        if entity["closed"] or n >= 3:
            return "Polygon"
        return "LineString"
    # LineString
    if n >= 2:
        return "LineString"
    return "Point"


def classify(entities, mapping=None):
    """把解析实体分类为 6 类要素 + other，返回按类型分组的要素列表。

    返回: {feature_type: [ {geometry_type, layer, properties, points,
                             closed, text, handle} ]}
    """
    if mapping is None:
        mapping = load_mapping()
    unmatched_policy = mapping.get("unmatched", "other")

    result = {t: [] for t in SIX_TYPES}
    result["other"] = []
    stats = {"matched": 0, "unmatched": 0, "text_attached": 0}

    # 文本实体先收集，最后就近挂到同类要素上（如管井编号）
    texts = [e for e in entities if e["type"] == "text"]
    geoms = [e for e in entities if e["type"] != "text"]

    for entity in geoms:
        ftype = match_feature_type(entity["layer"], mapping)
        if ftype is None:
            stats["unmatched"] += 1
            if unmatched_policy == "other":
                ftype = "other"
            else:
                continue
        else:
            stats["matched"] += 1

        conf = mapping["feature_types"].get(ftype, {})
        props = {
            "cad_layer": entity["layer"],
            "cad_handle": entity["handle"],
            "source": "CAD",
        }
        for key, rule in conf.get("attributes", {}).items():
            val = _extract_attr(rule, entity, entity["layer"])
            if val is not None:
                props[key] = val

        result[ftype].append({
            "geometry_type": _geometry_for(entity, ftype, conf.get("geometry", "LineString")),
            "layer": entity["layer"],
            "properties": props,
            "points": entity["points"],
            "closed": entity["closed"],
            "text": None,
            "handle": entity["handle"],
        })

    # 文本就近挂接：同一要素类型内、点在面内或 2 米容差
    tol = 2.0
    for t in texts:
        ftype = match_feature_type(t["layer"], mapping)
        if ftype is None:
            stats["unmatched"] += 1
            continue
        tx, ty = t["points"][0]
        best, best_d = None, tol
        for feat in result[ftype]:
            d = _text_feature_distance(tx, ty, feat)
            if d < best_d:
                best, best_d = feat, d
        if best is not None:
            best["properties"]["label"] = t["text"]
            stats["text_attached"] += 1
        else:
            # 附近无同类要素：作为独立点要素（如独立标注的管井）
            result[ftype].append({
                "geometry_type": "Point",
                "layer": t["layer"],
                "properties": {"cad_layer": t["layer"], "cad_handle": t["handle"],
                               "label": t["text"], "source": "CAD"},
                "points": t["points"],
                "closed": False, "text": t["text"], "handle": t["handle"],
            })

    stats["layers_output"] = {k: len(v) for k, v in result.items() if v}
    return result, stats
