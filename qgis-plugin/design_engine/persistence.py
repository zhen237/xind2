"""设计方案持久化 — 保存/加载为 GeoJSON + 参数 JSON"""
import json
import os
from datetime import datetime
from typing import List, Dict, Tuple

from models.site import Site


def save_design(sites: List[Site], params: Dict, output_dir: str, name: str = None) -> str:
    if name is None:
        name = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)

    features = [s.to_geojson_feature() for s in sites]
    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "name": name,
            "saved_at": datetime.now().isoformat(),
            "params": params,
        },
    }

    geojson_path = os.path.join(output_dir, f"{name}.geojson")
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    return geojson_path


def load_design(geojson_path: str) -> Tuple[List[Site], Dict]:
    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    sites = []
    for feat in geojson.get("features", []):
        try:
            sites.append(Site.from_geojson_feature(feat))
        except Exception:
            continue

    params = geojson.get("properties", {}).get("params", {})
    return sites, params


def list_designs(directory: str) -> List[Dict]:
    designs = []
    if not os.path.isdir(directory):
        return designs
    for fname in os.listdir(directory):
        if fname.endswith(".geojson"):
            fpath = os.path.join(directory, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                props = data.get("properties", {})
                designs.append({
                    "name": props.get("name", fname.replace(".geojson", "")),
                    "file": fpath,
                    "saved_at": props.get("saved_at", ""),
                    "site_count": len(data.get("features", [])),
                })
            except Exception:
                continue
    designs.sort(key=lambda d: d.get("saved_at", ""), reverse=True)
    return designs
