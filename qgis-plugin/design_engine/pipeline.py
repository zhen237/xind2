# -*- coding: utf-8 -*-
"""管线设计引擎

功能：
1. 管线路由自动规划（基站↔机房最短路径）
2. 管线路由避让
3. 管线工程量计算
"""

import math
from typing import List, Tuple, Dict, Optional

# 尝试相对导入，如果失败则使用绝对导入
try:
    from ..models.pipeline import Pipeline, PipelineType, PipelineConfig
except ImportError:
    from models.pipeline import Pipeline, PipelineType, PipelineConfig


def calculate_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    计算两点间距离（米）

    Args:
        lon1, lat1: 点1坐标
        lon2, lat2: 点2坐标

    Returns:
        距离（米）
    """
    R = 6371000  # 地球半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def generate_direct_route(
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    num_points: int = 10
) -> List[Tuple[float, float]]:
    """
    生成直线路径（带插值点）

    Args:
        start_lon, start_lat: 起点坐标
        end_lon, end_lat: 终点坐标
        num_points: 插值点数量

    Returns:
        路径坐标列表
    """
    coordinates = []
    for i in range(num_points + 1):
        ratio = i / num_points
        lon = start_lon + (end_lon - start_lon) * ratio
        lat = start_lat + (end_lat - start_lat) * ratio
        coordinates.append((round(lon, 7), round(lat, 7)))
    return coordinates


def generate_manhattan_route(
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    grid_size: float = 0.001
) -> List[Tuple[float, float]]:
    """
    生成曼哈顿路径（先水平后垂直，适合城市道路）

    Args:
        start_lon, start_lat: 起点坐标
        end_lon, end_lat: 终点坐标
        grid_size: 网格大小（度）

    Returns:
        路径坐标列表
    """
    coordinates = [(start_lon, start_lat)]

    # 先水平移动
    current_lon = start_lon
    while abs(current_lon - end_lon) > grid_size / 2:
        if current_lon < end_lon:
            current_lon += grid_size
        else:
            current_lon -= grid_size
        coordinates.append((round(current_lon, 7), round(start_lat, 7)))

    # 再垂直移动
    current_lat = start_lat
    while abs(current_lat - end_lat) > grid_size / 2:
        if current_lat < end_lat:
            current_lat += grid_size
        else:
            current_lat -= grid_size
        coordinates.append((round(end_lon, 7), round(current_lat, 7)))

    # 终点
    coordinates.append((end_lon, end_lat))
    return coordinates


def generate_pipeline_to_room(
    site_lon: float,
    site_lat: float,
    room_lon: float,
    room_lat: float,
    pipeline_type: PipelineType = PipelineType.DIRECT_BURIED,
    route_type: str = "direct"
) -> Pipeline:
    """
    生成基站到机房的管线

    Args:
        site_lon, site_lat: 基站坐标
        room_lon, room_lat: 机房坐标
        pipeline_type: 管线类型
        route_type: 路由类型（direct=直线, manhattan=曼哈顿）

    Returns:
        Pipeline对象
    """
    # 生成路径
    if route_type == "manhattan":
        coordinates = generate_manhattan_route(site_lon, site_lat, room_lon, room_lat)
    else:
        coordinates = generate_direct_route(site_lon, site_lat, room_lon, room_lat)

    # 获取配置
    config = PipelineConfig.type_configs[pipeline_type]

    # 创建管线
    pipeline = Pipeline(
        pipeline_id="",  # 由调用者设置
        start_site_id="",  # 由调用者设置
        end_site_id="",  # 由调用者设置
        pipeline_type=pipeline_type,
        coordinates=coordinates,
        depth_m=config["default_depth"],
        diameter_mm=config["default_diameter"],
        material=config["default_material"],
        capacity=config["default_capacity"],
    )

    # 计算长度和工程量
    pipeline.calculate_length()
    pipeline.calculate_engineering_volume()

    return pipeline


def generate_pipelines_for_sites(
    sites: List[Dict],
    room_lon: float,
    room_lat: float,
    pipeline_type: PipelineType = PipelineType.DIRECT_BURIED,
    route_type: str = "direct"
) -> List[Pipeline]:
    """
    为多个基站生成到机房的管线

    Args:
        sites: 基站列表 [{'site_id': str, 'longitude': float, 'latitude': float}, ...]
        room_lon, room_lat: 机房坐标
        pipeline_type: 管线类型
        route_type: 路由类型

    Returns:
        管线列表
    """
    pipelines = []

    for i, site in enumerate(sites):
        pipeline = generate_pipeline_to_room(
            site_lon=site['longitude'],
            site_lat=site['latitude'],
            room_lon=room_lon,
            room_lat=room_lat,
            pipeline_type=pipeline_type,
            route_type=route_type,
        )
        pipeline.pipeline_id = f"PL-{i+1:04d}"
        pipeline.start_site_id = site['site_id']
        pipeline.end_site_id = "ROOM-001"  # 默认机房ID
        pipelines.append(pipeline)

    return pipelines


def check_pipeline_avoidance(
    pipeline: Pipeline,
    avoidance_features: List[Dict]
) -> Tuple[bool, List[str]]:
    """
    检查管线是否与避让区域冲突

    Args:
        pipeline: 管线对象
        avoidance_features: 避让区域列表 (GeoJSON Feature格式)

    Returns:
        (是否有冲突, 冲突描述列表)
    """
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union

    conflicts = []

    # 创建管线几何
    if len(pipeline.coordinates) < 2:
        return False, []

    line = LineString(pipeline.coordinates)

    # 检查每个避让区域
    for feature in avoidance_features:
        geometry = feature.get('geometry', {})
        properties = feature.get('properties', {})
        feature_type = properties.get('type', 'unknown')

        # 获取缓冲距离
        buffer_m = PipelineConfig.avoidance_rules.get(feature_type, {}).get('buffer_m', 10)

        # 创建缓冲区（简化处理，用度数近似）
        buffer_deg = buffer_m / 111000  # 1度约111km

        if geometry.get('type') == 'Polygon':
            from shapely.geometry import shape
            polygon = shape(geometry)
            buffered = polygon.buffer(buffer_deg)

            if line.intersects(buffered):
                conflicts.append(f"管线与{feature_type}区域冲突（缓冲{buffer_m}m）")

        elif geometry.get('type') == 'Point':
            coords = geometry.get('coordinates', [0, 0])
            point = Point(coords)
            buffered = point.buffer(buffer_deg)

            if line.intersects(buffered):
                conflicts.append(f"管线与{feature_type}点冲突（缓冲{buffer_m}m）")

    return len(conflicts) > 0, conflicts


def optimize_pipeline_route(
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    avoidance_features: List[Dict],
    pipeline_type: PipelineType = PipelineType.DIRECT_BURIED
) -> List[Tuple[float, float]]:
    """
    优化管线路由，避开障碍物

    Args:
        start_lon, start_lat: 起点坐标
        end_lon, end_lat: 终点坐标
        avoidance_features: 避让区域列表
        pipeline_type: 管线类型

    Returns:
        优化后的路径坐标列表
    """
    # 简单实现：先尝试直线路径，如果有冲突则使用曼哈顿路径
    direct_coords = generate_direct_route(start_lon, start_lat, end_lon, end_lat)

    # 检查直线路径是否有冲突
    test_pipeline = Pipeline(
        pipeline_id="test",
        start_site_id="test",
        end_site_id="test",
        pipeline_type=pipeline_type,
        coordinates=direct_coords,
    )

    has_conflict, _ = check_pipeline_avoidance(test_pipeline, avoidance_features)

    if not has_conflict:
        return direct_coords

    # 有冲突，使用曼哈顿路径
    manhattan_coords = generate_manhattan_route(start_lon, start_lat, end_lon, end_lat)

    return manhattan_coords


def calculate_total_engineering_volume(pipelines: List[Pipeline]) -> Dict:
    """
    计算管线工程量汇总

    Args:
        pipelines: 管线列表

    Returns:
        工程量汇总字典
    """
    total_volume = {
        "管线总数": len(pipelines),
        "总长度(m)": 0,
        "直埋管线长度(m)": 0,
        "管道管线长度(m)": 0,
        "架空管线长度(m)": 0,
        "土方量(m³)": 0,
        "电杆数量": 0,
    }

    for pipeline in pipelines:
        total_volume["总长度(m)"] += pipeline.length_m

        if pipeline.pipeline_type == PipelineType.DIRECT_BURIED:
            total_volume["直埋管线长度(m)"] += pipeline.length_m
            if "土方量(m³)" in pipeline.engineering_volume:
                total_volume["土方量(m³)"] += pipeline.engineering_volume["土方量(m³)"]
        elif pipeline.pipeline_type == PipelineType.DUCT:
            total_volume["管道管线长度(m)"] += pipeline.length_m
        elif pipeline.pipeline_type == PipelineType.AERIAL:
            total_volume["架空管线长度(m)"] += pipeline.length_m
            if "电杆数量" in pipeline.engineering_volume:
                total_volume["电杆数量"] += pipeline.engineering_volume["电杆数量"]

    # 四舍五入
    for key in total_volume:
        if isinstance(total_volume[key], float):
            total_volume[key] = round(total_volume[key], 2)

    return total_volume
