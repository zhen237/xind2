"""设计持久化 — GeoJSON 格式的方案保存/加载"""

import json
import os
from models.site import Site


def save_design(sites, params, output_dir, name="design"):
    """将方案站点和参数保存为 GeoJSON 文件

    Args:
        sites: Site 对象列表
        params: 设计参数字典 (band, tower_height, grid_size 等)
        output_dir: 输出目录
        name: 方案名称 (不含扩展名)

    Returns:
        str: 保存的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    features = []
    for site in sites:
        features.append(site.to_geojson_feature())

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "params": params
    }

    filename = f"{name}.geojson"
    path = os.path.join(output_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    return path


def load_design(path):
    """从 GeoJSON 文件加载方案站点和参数

    Args:
        path: GeoJSON 文件路径

    Returns:
        tuple: (sites: list[Site], params: dict)
    """
    with open(path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)

    params = geojson.get('params', {})
    sites = []
    for feature in geojson.get('features', []):
        site = Site.from_geojson_feature(feature)
        sites.append(site)

    return sites, params


def list_designs(output_dir):
    """列出已保存的方案

    Args:
        output_dir: 方案存储目录

    Returns:
        list: [{name, site_count, path}, ...]
    """
    designs = []
    if not os.path.exists(output_dir):
        return designs

    for filename in sorted(os.listdir(output_dir)):
        if filename.endswith('.geojson'):
            path = os.path.join(output_dir, filename)
            with open(path, 'r', encoding='utf-8') as f:
                geojson = json.load(f)
            designs.append({
                'name': filename.replace('.geojson', ''),
                'site_count': len(geojson.get('features', [])),
                'path': path
            })

    return designs
