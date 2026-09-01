"""GeoJSON 输出（FR-1：标准 GeoJSON，含属性映射）"""

import json
import os


def feature_to_geojson_feature(feat, transformer=None):
    """内部要素 → GeoJSON Feature。transformer 为空则不转坐标。"""
    pts = feat["points"]
    if transformer is not None:
        pts = transformer.transform_points(pts)
    coords = [[round(x, 8), round(y, 8)] for (x, y) in pts]
    gtype = feat["geometry_type"]
    if gtype == "Point":
        geometry = {"type": "Point", "coordinates": coords[0]}
    elif gtype == "Polygon":
        ring = list(coords)
        # 闭合环：首尾相同
        if len(ring) >= 3 and ring[0] != ring[-1]:
            ring.append(ring[0])
        geometry = {"type": "Polygon", "coordinates": [ring]}
    else:
        geometry = {"type": "LineString", "coordinates": coords}
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": feat["properties"],
    }


def write_layer_geojson(path, features, source_crs, target_crs, crs_info=None):
    """把一组要素写为标准 GeoJSON FeatureCollection 文件。"""
    fc = {
        "type": "FeatureCollection",
        "name": os.path.splitext(os.path.basename(str(path)))[0],
        "crs_info": {
            "source_crs": str(source_crs),
            "target_crs": str(target_crs),
            **(crs_info or {}),
        },
        "features": features,
    }
    os.makedirs(os.path.dirname(os.path.abspath(str(path))), exist_ok=True)
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=1)
    return fc


def load_geojson(path):
    with open(str(path), "r", encoding="utf-8") as f:
        return json.load(f)
