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


def _line_segment_key(p1: Tuple[float, float], p2: Tuple[float, float]) -> str:
    """
    生成线段的唯一标识（无方向性）

    Args:
        p1, p2: 线段两端点坐标

    Returns:
        线段唯一标识字符串
    """
    # 按坐标排序，确保 (A,B) 和 (B,A) 生成相同的 key
    if p1 < p2:
        return f"{p1[0]:.7f},{p1[1]:.7f}-{p2[0]:.7f},{p2[1]:.7f}"
    else:
        return f"{p2[0]:.7f},{p2[1]:.7f}-{p1[0]:.7f},{p1[1]:.7f}"


def find_shared_segments(pipelines: List[Pipeline]) -> Dict[str, List[str]]:
    """
    查找管线之间的共享路段

    Args:
        pipelines: 管线列表

    Returns:
        共享路段字典 {segment_key: [pipeline_id1, pipeline_id2, ...]}
    """
    segment_map: Dict[str, List[str]] = {}

    for pipeline in pipelines:
        coords = pipeline.coordinates
        for i in range(len(coords) - 1):
            key = _line_segment_key(coords[i], coords[i + 1])
            if key not in segment_map:
                segment_map[key] = []
            segment_map[key].append(pipeline.pipeline_id)

    # 只保留被多条管线共享的路段
    shared_segments = {k: v for k, v in segment_map.items() if len(v) > 1}
    return shared_segments


def generate_shared_pipelines(
    sites: List[Dict],
    room_lon: float,
    room_lat: float,
    pipeline_type: PipelineType = PipelineType.DIRECT_BURIED,
    route_type: str = "direct"
) -> Tuple[List[Pipeline], Dict[str, List[str]]]:
    """
    生成多基站到机房的管线，自动识别共享路段

    Args:
        sites: 基站列表
        room_lon, room_lat: 机房坐标
        pipeline_type: 管线类型
        route_type: 路由类型

    Returns:
        (管线列表, 共享路段字典)
    """
    # 生成所有管线
    pipelines = generate_pipelines_for_sites(sites, room_lon, room_lat, pipeline_type, route_type)

    # 查找共享路段
    shared_segments = find_shared_segments(pipelines)

    # 标记共享信息
    for pipeline in pipelines:
        coords = pipeline.coordinates
        shared_count = 0
        for i in range(len(coords) - 1):
            key = _line_segment_key(coords[i], coords[i + 1])
            if key in shared_segments:
                shared_count += 1

        if shared_count > 0:
            pipeline.is_shared = True
            # 获取共享的其他管线 ID
            other_ids = set()
            for i in range(len(coords) - 1):
                key = _line_segment_key(coords[i], coords[i + 1])
                if key in shared_segments:
                    for pid in shared_segments[key]:
                        if pid != pipeline.pipeline_id:
                            other_ids.add(pid)
            pipeline.shared_with = list(other_ids)

    return pipelines, shared_segments


def calculate_shared_engineering_volume(
    pipelines: List[Pipeline],
    shared_segments: Dict[str, List[str]]
) -> Dict:
    """
    计算考虑共享的工程量（共享路段只计算一次）

    Args:
        pipelines: 管线列表
        shared_segments: 共享路段字典

    Returns:
        工程量汇总字典
    """
    # 收集所有路段及其长度
    segment_lengths: Dict[str, float] = {}
    segment_types: Dict[str, PipelineType] = {}

    for pipeline in pipelines:
        coords = pipeline.coordinates
        for i in range(len(coords) - 1):
            key = _line_segment_key(coords[i], coords[i + 1])
            if key not in segment_lengths:
                dist = calculate_distance(coords[i][0], coords[i][1],
                                          coords[i + 1][0], coords[i + 1][1])
                segment_lengths[key] = dist
                segment_types[key] = pipeline.pipeline_type

    # 计算去重后的总长度
    total_unique_length = sum(segment_lengths.values())
    shared_length = sum(segment_lengths[k] for k in shared_segments if k in segment_lengths)

    # 原始总长度（不去重）
    total_raw_length = sum(p.length_m for p in pipelines)

    volume = {
        "管线总数": len(pipelines),
        "原始总长度(m)": round(total_raw_length, 2),
        "去重后总长度(m)": round(total_unique_length, 2),
        "共享路段长度(m)": round(shared_length, 2),
        "节省长度(m)": round(total_raw_length - total_unique_length, 2),
        "节省比例(%)": round((total_raw_length - total_unique_length) / total_raw_length * 100, 1) if total_raw_length > 0 else 0,
        "共享路段数": len(shared_segments),
        "直埋管线长度(m)": 0,
        "管道管线长度(m)": 0,
        "架空管线长度(m)": 0,
    }

    # 按类型统计（去重后）
    for seg_key, seg_type in segment_types.items():
        length = segment_lengths[seg_key]
        if seg_type == PipelineType.DIRECT_BURIED:
            volume["直埋管线长度(m)"] += length
        elif seg_type == PipelineType.DUCT:
            volume["管道管线长度(m)"] += length
        elif seg_type == PipelineType.AERIAL:
            volume["架空管线长度(m)"] += length

    # 四舍五入
    for key in volume:
        if isinstance(volume[key], float):
            volume[key] = round(volume[key], 2)

    return volume


def calculate_pipeline_cost(pipeline: Pipeline) -> Dict:
    """
    计算单条管线成本

    Args:
        pipeline: 管线对象

    Returns:
        成本明细字典
    """
    config = PipelineConfig.cost_configs
    type_config = config[pipeline.pipeline_type]
    length = pipeline.length_m

    if length <= 0:
        return {"总成本(元)": 0}

    cost_detail = {
        "管线编号": pipeline.pipeline_id,
        "管线类型": pipeline.pipeline_type.value,
        "长度(m)": round(length, 2),
    }

    material_cost = 0  # 材料费
    construction_cost = 0  # 施工费

    if pipeline.pipeline_type == PipelineType.DIRECT_BURIED:
        # 光缆费
        cable_cost = length * type_config["光缆单价(元/m)"]
        cost_detail["光缆费(元)"] = round(cable_cost, 2)
        material_cost += cable_cost

        # 土方开挖费
        trench_width = pipeline.diameter_mm / 1000 + 0.6
        trench_depth = pipeline.depth_m + 0.1
        volume = length * trench_width * trench_depth
        dig_cost = volume * type_config["土方开挖单价(元/m³)"]
        backfill_cost = volume * type_config["回填单价(元/m³)"]
        cost_detail["土方开挖费(元)"] = round(dig_cost, 2)
        cost_detail["回填费(元)"] = round(backfill_cost, 2)
        construction_cost += dig_cost + backfill_cost

        # 标石
        stone_count = int(length / type_config["标石间距(m)"]) + 1
        stone_cost = stone_count * type_config["标石单价(元/个)"]
        cost_detail["标石数量(个)"] = stone_count
        cost_detail["标石费(元)"] = round(stone_cost, 2)
        material_cost += stone_cost

        # 接头盒
        joint_count = max(1, int(length / type_config["接头间距(m)"]))
        joint_cost = joint_count * type_config["接头盒单价(元/个)"]
        cost_detail["接头盒数量(个)"] = joint_count
        cost_detail["接头盒费(元)"] = round(joint_cost, 2)
        material_cost += joint_cost

    elif pipeline.pipeline_type == PipelineType.DUCT:
        # 管道费
        pipe_cost = length * type_config["管道单价(元/m)"]
        cost_detail["管道费(元)"] = round(pipe_cost, 2)
        material_cost += pipe_cost

        # 光缆费
        cable_cost = length * type_config["光缆单价(元/m)"]
        cost_detail["光缆费(元)"] = round(cable_cost, 2)
        material_cost += cable_cost

        # 土方开挖费（城市开挖成本更高）
        trench_width = 0.6  # 管道沟宽
        trench_depth = pipeline.depth_m + 0.2
        volume = length * trench_width * trench_depth
        dig_cost = volume * type_config["土方开挖单价(元/m³)"]
        backfill_cost = volume * type_config["回填单价(元/m³)"]
        cost_detail["土方开挖费(元)"] = round(dig_cost, 2)
        cost_detail["回填费(元)"] = round(backfill_cost, 2)
        construction_cost += dig_cost + backfill_cost

        # 人孔
        manhole_count = max(1, int(length / type_config["人孔间距(m)"]))
        manhole_cost = manhole_count * type_config["人孔单价(元/个)"]
        cost_detail["人孔数量(个)"] = manhole_count
        cost_detail["人孔费(元)"] = round(manhole_cost, 2)
        construction_cost += manhole_cost

        # 接头盒
        joint_count = max(1, int(length / type_config["接头间距(m)"]))
        joint_cost = joint_count * type_config["接头盒单价(元/个)"]
        cost_detail["接头盒数量(个)"] = joint_count
        cost_detail["接头盒费(元)"] = round(joint_cost, 2)
        material_cost += joint_cost

    elif pipeline.pipeline_type == PipelineType.AERIAL:
        # 光缆费
        cable_cost = length * type_config["光缆单价(元/m)"]
        cost_detail["光缆费(元)"] = round(cable_cost, 2)
        material_cost += cable_cost

        # 电杆
        pole_count = int(length / type_config["杆距(m)"]) + 1
        pole_cost = pole_count * type_config["电杆单价(元/根)"]
        cost_detail["电杆数量(根)"] = pole_count
        cost_detail["电杆费(元)"] = round(pole_cost, 2)
        material_cost += pole_cost

        # 拉线
        guy_count = int(length / 1000 * type_config["拉线比例"])
        guy_cost = guy_count * type_config["拉线单价(元/条)"]
        cost_detail["拉线数量(条)"] = guy_count
        cost_detail["拉线费(元)"] = round(guy_cost, 2)
        material_cost += guy_cost

        # 接头盒
        joint_count = max(1, int(length / type_config["接头间距(m)"]))
        joint_cost = joint_count * type_config["接头盒单价(元/个)"]
        cost_detail["接头盒数量(个)"] = joint_count
        cost_detail["接头盒费(元)"] = round(joint_cost, 2)
        material_cost += joint_cost

    # 小计
    cost_detail["材料费小计(元)"] = round(material_cost, 2)
    cost_detail["施工费小计(元)"] = round(construction_cost, 2)

    # 附加费
    subtotal = material_cost + construction_cost
    management_fee = subtotal * config["施工附加费率"]
    profit_fee = subtotal * config["利润费率"]
    tax_fee = subtotal * config["税金费率"]

    cost_detail["施工管理费(元)"] = round(management_fee, 2)
    cost_detail["利润(元)"] = round(profit_fee, 2)
    cost_detail["税金(元)"] = round(tax_fee, 2)

    # 总成本
    total_cost = subtotal + management_fee + profit_fee + tax_fee
    cost_detail["总成本(元)"] = round(total_cost, 2)

    return cost_detail


def calculate_total_cost(pipelines: List[Pipeline]) -> Dict:
    """
    计算管线总成本

    Args:
        pipelines: 管线列表

    Returns:
        总成本汇总字典
    """
    if not pipelines:
        return {"管线总数": 0, "总成本(元)": 0}

    all_costs = []
    for pipeline in pipelines:
        cost = calculate_pipeline_cost(pipeline)
        all_costs.append(cost)

    # 汇总
    summary = {
        "管线总数": len(pipelines),
        "总长度(m)": round(sum(p.length_m for p in pipelines), 2),
        "材料费合计(元)": round(sum(c.get("材料费小计(元)", 0) for c in all_costs), 2),
        "施工费合计(元)": round(sum(c.get("施工费小计(元)", 0) for c in all_costs), 2),
        "施工管理费合计(元)": round(sum(c.get("施工管理费(元)", 0) for c in all_costs), 2),
        "利润合计(元)": round(sum(c.get("利润(元)", 0) for c in all_costs), 2),
        "税金合计(元)": round(sum(c.get("税金(元)", 0) for c in all_costs), 2),
        "总成本(元)": round(sum(c.get("总成本(元)", 0) for c in all_costs), 2),
        "每米成本(元/m)": 0,
    }

    # 计算每米成本
    if summary["总长度(m)"] > 0:
        summary["每米成本(元/m)"] = round(summary["总成本(元)"] / summary["总长度(m)"], 2)

    # 按类型统计
    type_costs = {}
    for pipeline, cost in zip(pipelines, all_costs):
        type_name = pipeline.pipeline_type.value
        if type_name not in type_costs:
            type_costs[type_name] = {"长度(m)": 0, "成本(元)": 0, "数量": 0}
        type_costs[type_name]["长度(m)"] += pipeline.length_m
        type_costs[type_name]["成本(元)"] += cost.get("总成本(元)", 0)
        type_costs[type_name]["数量"] += 1

    # 四舍五入
    for type_name, data in type_costs.items():
        data["长度(m)"] = round(data["长度(m)"], 2)
        data["成本(元)"] = round(data["成本(元)"], 2)
        summary[f"类型_{type_name}"] = data

    return summary


def generate_pipeline_report_text(
    pipelines: List[Pipeline],
    title: str = "通信管线工程量及成本报表"
) -> str:
    """
    生成管线报表文本

    Args:
        pipelines: 管线列表
        title: 报表标题

    Returns:
        报表文本字符串
    """
    from datetime import datetime

    # 计算成本
    cost_summary = calculate_total_cost(pipelines)

    # 生成报表
    lines = []
    lines.append("=" * 60)
    lines.append(f"  {title}")
    lines.append("=" * 60)
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")

    # 一、工程概况
    lines.append("一、工程概况")
    lines.append("-" * 40)
    lines.append(f"  管线总数: {cost_summary['管线总数']} 条")
    lines.append(f"  总长度: {cost_summary['总长度(m)']:.2f} m")
    lines.append("")

    # 按类型统计
    lines.append("  按类型统计:")
    for key, value in cost_summary.items():
        if key.startswith("类型_"):
            type_name = key.replace("类型_", "")
            lines.append(f"    {type_name}: {value['数量']}条, {value['长度(m)']:.2f}m")
    lines.append("")

    # 二、管线明细
    lines.append("二、管线明细")
    lines.append("-" * 40)
    lines.append(f"{'编号':<10} {'类型':<8} {'起点':<12} {'终点':<12} {'长度(m)':<10} {'管径(mm)':<10}")
    lines.append("-" * 62)

    for p in pipelines:
        lines.append(
            f"{p.pipeline_id:<10} "
            f"{p.pipeline_type.value:<8} "
            f"{p.start_site_id:<12} "
            f"{p.end_site_id:<12} "
            f"{p.length_m:<10.2f} "
            f"{p.diameter_mm:<10}"
        )
    lines.append("")

    # 三、工程量汇总
    lines.append("三、工程量汇总")
    lines.append("-" * 40)

    for p in pipelines:
        if p.engineering_volume:
            lines.append(f"  [{p.pipeline_id}]")
            for key, value in p.engineering_volume.items():
                lines.append(f"    {key}: {value}")
    lines.append("")

    # 四、成本估算
    lines.append("四、成本估算")
    lines.append("-" * 40)
    lines.append(f"  材料费合计: {cost_summary['材料费合计(元)']:>12,.2f} 元")
    lines.append(f"  施工费合计: {cost_summary['施工费合计(元)']:>12,.2f} 元")
    lines.append(f"  施工管理费: {cost_summary['施工管理费合计(元)']:>12,.2f} 元")
    lines.append(f"  利润:       {cost_summary['利润合计(元)']:>12,.2f} 元")
    lines.append(f"  税金:       {cost_summary['税金合计(元)']:>12,.2f} 元")
    lines.append("-" * 40)
    lines.append(f"  总成本:     {cost_summary['总成本(元)']:>12,.2f} 元")
    lines.append(f"  每米成本:   {cost_summary['每米成本(元/m)']:>12,.2f} 元/m")
    lines.append("")

    # 五、成本明细
    lines.append("五、成本明细")
    lines.append("-" * 40)

    for p in pipelines:
        cost = calculate_pipeline_cost(p)
        lines.append(f"  [{p.pipeline_id}] {p.pipeline_type.value} - {p.length_m:.2f}m")
        for key, value in cost.items():
            if key not in ["管线编号", "管线类型", "长度(m)"]:
                if isinstance(value, float):
                    lines.append(f"    {key}: {value:,.2f}")
                else:
                    lines.append(f"    {key}: {value}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("  报表结束")
    lines.append("=" * 60)

    return "\n".join(lines)


def export_pipeline_report_csv(
    pipelines: List[Pipeline],
    output_path: str
) -> bool:
    """
    导出管线报表为CSV格式

    Args:
        pipelines: 管线列表
        output_path: 输出文件路径

    Returns:
        是否成功
    """
    import csv
    from datetime import datetime

    try:
        # 管线明细表
        detail_path = output_path.replace(".csv", "_明细表.csv")
        with open(detail_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 表头
            writer.writerow([
                "管线编号", "管线类型", "起始站点", "终止站点",
                "长度(m)", "埋深(m)", "管径(mm)", "材质", "容量(孔)",
                "是否共享", "共享管线"
            ])
            # 数据
            for p in pipelines:
                writer.writerow([
                    p.pipeline_id,
                    p.pipeline_type.value,
                    p.start_site_id,
                    p.end_site_id,
                    f"{p.length_m:.2f}",
                    f"{p.depth_m:.2f}",
                    p.diameter_mm,
                    p.material,
                    p.capacity,
                    "是" if p.is_shared else "否",
                    ",".join(p.shared_with) if p.shared_with else ""
                ])

        # 工程量表
        volume_path = output_path.replace(".csv", "_工程量表.csv")
        with open(volume_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 表头
            writer.writerow(["管线编号", "指标", "数值"])
            # 数据
            for p in pipelines:
                if p.engineering_volume:
                    for key, value in p.engineering_volume.items():
                        writer.writerow([p.pipeline_id, key, value])

        # 成本表
        cost_path = output_path.replace(".csv", "_成本表.csv")
        with open(cost_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 表头
            writer.writerow(["管线编号", "费用项目", "金额(元)"])
            # 数据
            for p in pipelines:
                cost = calculate_pipeline_cost(p)
                for key, value in cost.items():
                    if key not in ["管线编号", "管线类型", "长度(m)"]:
                        writer.writerow([p.pipeline_id, key, value])

        # 汇总表
        summary_path = output_path.replace(".csv", "_汇总表.csv")
        cost_summary = calculate_total_cost(pipelines)
        with open(summary_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["项目", "数值"])
            for key, value in cost_summary.items():
                if not key.startswith("类型_"):
                    writer.writerow([key, value])

        return True
    except Exception as e:
        print(f"导出CSV失败: {e}")
        return False
