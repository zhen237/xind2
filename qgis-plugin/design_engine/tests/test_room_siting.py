# -*- coding: utf-8 -*-
"""room_siting.py 单元测试（纯标准库，可在沙箱运行）

测试覆盖：
- 覆盖栅格生成与盲区识别
- 候选机房聚类与评估（供电/传输可达、容量）
- 无盲区时的容量型候选
- 路网驱动的传输可达判定
"""
import os
import sys
import unittest

# 让测试在沙箱内以 stdlib-only 方式运行（无 QGIS 依赖）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_engine.room_siting import (  # noqa: E402
    build_coverage_grid,
    detect_coverage_gaps,
    cluster_centroids,
    select_room_sites,
)


def _make_sites(n=4, spread=0.005):
    """在运城学院附近生成 n 个站点。"""
    base_lon, base_lat = 111.0, 35.0
    sites = []
    for i in range(n):
        sites.append({
            "siteId": "S%03d" % (i + 1),
            "longitude": base_lon + (i % 2) * spread,
            "latitude": base_lat + (i // 2) * spread,
            "towerHeight": 35,
        })
    return sites


class TestRoomSiting(unittest.TestCase):

    def test_build_coverage_grid_returns_cells(self):
        grid = build_coverage_grid(_make_sites(3), radius_km=1.0, resolution_m=100)
        self.assertGreater(len(grid["cells"]), 0)
        self.assertIn("bounds", grid)
        # 每个 cell 都有 rsrp 数值
        for c in grid["cells"][:10]:
            self.assertIn("rsrp", c)
            self.assertIsInstance(c["rsrp"], float)

    def test_detect_coverage_gaps_identifies_blind_zones(self):
        # 单站点 + 合理半径：在 -90dBm 服务边缘之外应识别为盲区
        sites = [{"siteId": "S1", "longitude": 111.0, "latitude": 35.0, "towerHeight": 35}]
        grid = build_coverage_grid(sites, radius_km=2.0, resolution_m=100)
        gaps = detect_coverage_gaps(grid, rsrp_threshold_dbm=-90)
        self.assertGreater(len(gaps), 0)
        for g in gaps:
            self.assertLess(g["rsrp"], -90)

    def test_cluster_centroids_count(self):
        pts = [{"lon": 111.0 + i * 0.001, "lat": 35.0} for i in range(20)]
        cents = cluster_centroids(pts, 3)
        self.assertEqual(len(cents), 3)
        for c in cents:
            self.assertIn("lon", c)
            self.assertIn("lat", c)

    def test_select_room_sites_recommends_feasible(self):
        sites = _make_sites(6, spread=0.01)
        result = select_room_sites(
            sites, radius_km=1.5, resolution_m=100,
            candidate_count=2, service_radius_m=3000,
        )
        self.assertEqual(result["summary"]["total_sites"], 6)
        self.assertGreaterEqual(len(result["candidates"]), 1)
        # 默认无电源点 → 供电可达为假设成立
        for c in result["candidates"]:
            self.assertTrue(c["power_feasible"])
            self.assertTrue(c["power_assumed"])
            self.assertIn("served_count", c)
            self.assertIn("is_recommended", c)

    def test_select_room_sites_with_road_transmission(self):
        sites = _make_sites(4, spread=0.008)
        # 一条贯穿站点的道路，使传输可达判定走 T3 路网
        road = [[(110.99, 34.99), (111.01, 35.01)]]
        result = select_room_sites(
            sites, radius_km=1.0, resolution_m=100,
            candidate_count=1, road_segments=road,
            transmission_reach_m=6000,
        )
        cands = result["candidates"]
        self.assertEqual(len(cands), 1)
        self.assertIn("transmission_distance_m", cands[0])

    def test_select_room_sites_empty(self):
        result = select_room_sites([])
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["summary"]["total_sites"], 0)

    def test_capacity_planning_rooms_needed(self):
        sites = _make_sites(10, spread=0.02)
        result = select_room_sites(
            sites, radius_km=2.0, resolution_m=120,
            candidate_count=2, capacity_per_room=4,
        )
        # 10 站点 / 容量 4 = 至少 3 个机房
        self.assertGreaterEqual(result["summary"]["rooms_needed"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
