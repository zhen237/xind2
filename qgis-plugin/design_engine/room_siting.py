# -*- coding: utf-8 -*-
"""机房自动选址 + 容量规划引擎 (T6)

驱动因素（对应 FR-8）：
- 覆盖缺口：基于 Okumura-Hata 模型计算每个栅格的 RSRP，低于阈值即盲区
- 供电可达：候选点需在电源点（或既有站点簇）一定半径内
- 传输可达：候选点需经路网（复用 T3）或直线距离可达骨干/汇聚点
- 容量规划：估算单机房可服务站点数（RU 容量）与全网所需机房数

纯标准库实现，不依赖 QGIS，可在沙箱单测。
覆盖计算复用 coverage.py；路网几何复用 road_network.py（T3）。
"""

import math
from typing import List, Dict, Optional, Tuple

try:
    from .coverage import (
        okumura_hata_path_loss,
        calculate_rsrp,
        power_w_to_dbm,
    )
except ImportError:
    from coverage import (
        okumura_hata_path_loss,
        calculate_rsrp,
        power_w_to_dbm,
    )

try:
    from .road_network import haversine, route_between
except ImportError:
    from road_network import haversine, route_between


def _rsrp_at(
    frequency_mhz: float,
    distance_km: float,
    tx_height_m: float,
    rx_height_m: float,
    environment: str,
    tx_power_dbm: float,
    antenna_gain_dbi: float,
    shadow_fade_db: float,
) -> float:
    """单个 (站点→点) 的 RSRP（dBm）。"""
    path_loss = okumura_hata_path_loss(
        frequency_mhz, max(distance_km, 0.01),
        tx_height_m, rx_height_m, environment,
    )
    return calculate_rsrp(tx_power_dbm, antenna_gain_dbi, path_loss, 0.0, shadow_fade_db)


def build_coverage_grid(
    sites: List[Dict],
    frequency_mhz: float = 2100.0,
    tx_power_w: float = 20.0,
    antenna_gain_dbi: float = 18.0,
    rx_height_m: float = 1.5,
    shadow_fade_db: float = 8.0,
    environment: str = "URBAN",
    radius_km: float = 2.0,
    resolution_m: int = 80,
) -> Dict:
    """生成全网覆盖栅格，返回每格的最大 RSRP。

    Args:
        sites: 站点列表 [{'longitude','latitude','towerHeight'}]
        （其余为全局射频参数）

    Returns:
        {
          'cells': [{'lon','lat','rsrp'}],   # 仅保留有覆盖（rsrp>=threshold 由调用方裁）
          'rsrp_threshold_dbm': -110,
          'resolution_m': int,
          'bounds': (min_lon,min_lat,max_lon,max_lat),
        }
    """
    tx_power_dbm = power_w_to_dbm(tx_power_w)

    # 合并所有站点的覆盖半径，确定栅格范围
    if not sites:
        return {"cells": [], "rsrp_threshold_dbm": -110,
                "resolution_m": resolution_m, "bounds": (0, 0, 0, 0)}

    lons = [float(s["longitude"]) for s in sites]
    lats = [float(s["latitude"]) for s in sites]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # 栅格步长（度）
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians((min_lat + max_lat) / 2.0)))
    lat_per_km = 1.0 / 111.0
    step_lon = (resolution_m / 1000.0) * lon_per_km
    step_lat = (resolution_m / 1000.0) * lat_per_km

    cell_map: Dict[Tuple[int, int], Dict] = {}
    for s in sites:
        slon, slat = float(s["longitude"]), float(s["latitude"])
        th = float(s.get("towerHeight", 30))
        steps = int(radius_km * 1000 / resolution_m)
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                d_lon = i * step_lon
                d_lat = j * step_lat
                lon, lat = slon + d_lon, slat + d_lat
                d_km = math.sqrt((i * resolution_m / 1000.0) ** 2 +
                                 (j * resolution_m / 1000.0) ** 2)
                if d_km > radius_km:
                    continue
                rsrp = _rsrp_at(frequency_mhz, d_km, th, rx_height_m,
                                environment, tx_power_dbm, antenna_gain_dbi,
                                shadow_fade_db)
                key = (int(round(lon / step_lon)), int(round(lat / step_lat)))
                prev = cell_map.get(key)
                if prev is None or rsrp > prev["rsrp"]:
                    cell_map[key] = {
                        "lon": round(lon, 7),
                        "lat": round(lat, 7),
                        "rsrp": round(rsrp, 1),
                    }

    return {
        "cells": list(cell_map.values()),
        "rsrp_threshold_dbm": -110,
        "resolution_m": resolution_m,
        "bounds": (min_lon, min_lat, max_lon, max_lat),
    }


def detect_coverage_gaps(grid: Dict, rsrp_threshold_dbm: float = -110) -> List[Dict]:
    """从覆盖栅格中识别盲区（最大 RSRP 低于阈值）。"""
    return [c for c in grid.get("cells", []) if c["rsrp"] < rsrp_threshold_dbm]


def cluster_centroids(points: List[Dict], k: int) -> List[Dict]:
    """对点集做简单 k-means，返回 k 个簇质心（候选机房位置）。

    纯标准库实现；点数不足 k 时返回去重后的点本身。
    """
    if not points:
        return []
    if len(points) <= k:
        # 直接以每个点作为候选
        return [{"lon": round(p["lon"], 7), "lat": round(p["lat"], 7)} for p in points]

    # 初始化：均匀取 k 个种子
    seeds = [points[i * len(points) // k] for i in range(k)]
    centroids = [{"lon": s["lon"], "lat": s["lat"]} for s in seeds]

    for _ in range(10):
        clusters = [[] for _ in centroids]
        for p in points:
            best = min(range(len(centroids)),
                       key=lambda ci: haversine(p["lon"], p["lat"],
                                               centroids[ci]["lon"], centroids[ci]["lat"]))
            clusters[best].append(p)
        new_centroids = []
        for ci, members in enumerate(clusters):
            if members:
                mlon = sum(m["lon"] for m in members) / len(members)
                mlat = sum(m["lat"] for m in members) / len(members)
                new_centroids.append({"lon": mlon, "lat": mlat})
            else:
                new_centroids.append(centroids[ci])  # 空簇保留
        if new_centroids == centroids:
            break
        centroids = new_centroids

    return [{"lon": round(c["lon"], 7), "lat": round(c["lat"], 7)} for c in centroids]


def _evaluate_candidate(
    candidate: Dict,
    sites: List[Dict],
    hub: Dict,
    grid: Dict,
    params: Dict,
) -> Dict:
    """评估单个候选机房的可行性与容量。"""
    clon, clat = candidate["lon"], candidate["lat"]

    service_radius_m = params["service_radius_m"]
    power_reach_m = params["power_reach_m"]
    transmission_reach_m = params["transmission_reach_m"]
    power_supply_points = params.get("power_supply_points") or []
    road_segments = params.get("road_segments")
    capacity_per_room = params["capacity_per_room"]

    # 1) 服务站点
    served = []
    for s in sites:
        if haversine(clon, clat, float(s["longitude"]), float(s["latitude"])) <= service_radius_m:
            served.append(s.get("siteId", s.get("site_id", "")))

    # 2) 覆盖缺口修复量（候选服务半径内的盲区点数）
    gap_fixed = 0
    for c in grid.get("gap_cells", []):
        if haversine(clon, clat, c["lon"], c["lat"]) <= service_radius_m:
            gap_fixed += 1

    # 3) 供电可达
    if power_supply_points:
        power_feasible = any(
            haversine(clon, clat, float(p["longitude"]), float(p["latitude"])) <= power_reach_m
            for p in power_supply_points
        )
        power_assumed = False
    else:
        # 无电源点数据：假定城区供电普遍可达，但标记为假设
        power_feasible = True
        power_assumed = True

    # 4) 传输可达（复用 T3 路网；无路网则直线距离）
    transmission_distance_m = haversine(clon, clat, hub["longitude"], hub["latitude"])
    transmission_feasible = transmission_distance_m <= transmission_reach_m
    if road_segments:
        res = route_between(
            (clon, clat), (hub["longitude"], hub["latitude"]),
            road_segments, algorithm="dijkstra", snap=True,
        )
        if res["found"]:
            transmission_distance_m = res["distance_m"]
            transmission_feasible = transmission_distance_m <= transmission_reach_m

    capacity_ru = min(capacity_per_room, len(served)) if served else 0
    is_recommended = bool(power_feasible and transmission_feasible and served)

    return {
        "id": candidate.get("id", "ROOM-CAND"),
        "longitude": round(clon, 7),
        "latitude": round(clat, 7),
        "served_sites": served,
        "served_count": len(served),
        "coverage_gap_points_fixed": gap_fixed,
        "power_feasible": power_feasible,
        "power_assumed": power_assumed,
        "transmission_feasible": transmission_feasible,
        "transmission_distance_m": round(transmission_distance_m, 1),
        "capacity_ru": capacity_ru,
        "is_recommended": is_recommended,
    }


def select_room_sites(
    sites: List[Dict],
    frequency_mhz: float = 2100.0,
    tx_power_w: float = 20.0,
    antenna_gain_dbi: float = 18.0,
    rx_height_m: float = 1.5,
    shadow_fade_db: float = 8.0,
    environment: str = "URBAN",
    radius_km: float = 2.0,
    resolution_m: int = 80,
    rsrp_threshold_dbm: float = -110,
    candidate_count: int = 2,
    service_radius_m: float = 3000.0,
    power_reach_m: float = 5000.0,
    transmission_reach_m: float = 8000.0,
    capacity_per_room: int = 12,
    power_supply_points: Optional[List[Dict]] = None,
    road_segments: Optional[List[List[Tuple[float, float]]]] = None,
) -> Dict:
    """机房自动选址主入口。

    Args:
        sites: 站点列表 [{'siteId','longitude','latitude','towerHeight'}]
        其余为射频/规划参数。

    Returns:
        {
          'candidates': [ 候选机房评估 ],
          'summary': { total_sites, gap_points, candidate_count,
                       recommended_count, rooms_needed },
        }
    """
    site_nodes = [{
        "siteId": s.get("siteId", s.get("site_id", "S%d" % i)),
        "longitude": float(s["longitude"]),
        "latitude": float(s["latitude"]),
        "towerHeight": float(s.get("towerHeight", s.get("tower_height", 30))),
    } for i, s in enumerate(sites)]

    if not site_nodes:
        return {"candidates": [], "summary": {
            "total_sites": 0, "gap_points": 0, "candidate_count": 0,
            "recommended_count": 0, "rooms_needed": 0}}

    grid = build_coverage_grid(
        site_nodes, frequency_mhz=frequency_mhz, tx_power_w=tx_power_w,
        antenna_gain_dbi=antenna_gain_dbi, rx_height_m=rx_height_m,
        shadow_fade_db=shadow_fade_db, environment=environment,
        radius_km=radius_km, resolution_m=resolution_m,
    )
    gaps = detect_coverage_gaps(grid, rsrp_threshold_dbm)
    grid["gap_cells"] = gaps

    # 骨干/汇聚点：取站点几何质心（真实系统中为既有核心机房，可传入）
    hub = {
        "longitude": sum(s["longitude"] for s in site_nodes) / len(site_nodes),
        "latitude": sum(s["latitude"] for s in site_nodes) / len(site_nodes),
    }

    params = {
        "service_radius_m": service_radius_m,
        "power_reach_m": power_reach_m,
        "transmission_reach_m": transmission_reach_m,
        "power_supply_points": power_supply_points,
        "road_segments": road_segments,
        "capacity_per_room": capacity_per_room,
    }

    # 候选位置：优先用盲区质心；无盲区则用站点簇质心（纯容量/汇聚目的）
    if gaps:
        seeds = cluster_centroids(gaps, candidate_count)
    else:
        seeds = cluster_centroids(
            [{"lon": s["longitude"], "lat": s["latitude"]} for s in site_nodes],
            candidate_count,
        )

    candidates = []
    for i, seed in enumerate(seeds):
        cand = dict(seed)
        cand["id"] = "ROOM-CAND-%d" % (i + 1)
        candidates.append(_evaluate_candidate(cand, site_nodes, hub, grid, params))

    recommended = [c for c in candidates if c["is_recommended"]]
    rooms_needed = max(1, -(-len(site_nodes) // capacity_per_room)) if site_nodes else 0

    return {
        "candidates": candidates,
        "summary": {
            "total_sites": len(site_nodes),
            "gap_points": len(gaps),
            "candidate_count": len(candidates),
            "recommended_count": len(recommended),
            "rooms_needed": rooms_needed,
        },
    }

