# -*- coding: utf-8 -*-
"""road_network.py 单元测试（T3 验收支撑）

无需 QGIS / 第三方库，纯标准库即可运行：
    python qgis-plugin/design_engine/tests/test_road_network.py
"""

import math
import os
import sys

# 允许以脚本方式直接运行（不依赖包结构）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from design_engine.road_network import (  # noqa: E402
    RoadGraph,
    build_road_graph,
    route_between,
    haversine,
)


def _make_grid(origin_lon=0.0, origin_lat=0.0, n=3, step=1.0):
    """构造 n×n 道路网格（相邻节点间有一条路段）。"""
    segments = []
    nodes = {}
    for i in range(n):
        for j in range(n):
            nodes[(i, j)] = (origin_lon + j * step, origin_lat + i * step)
    # 横向
    for i in range(n):
        for j in range(n - 1):
            segments.append([nodes[(i, j)], nodes[(i, j + 1)]])
    # 纵向
    for j in range(n):
        for i in range(n - 1):
            segments.append([nodes[(i, j)], nodes[(i + 1, j)]])
    return nodes, segments


def test_build_graph_counts():
    _, segs = _make_grid(n=3)
    g = build_road_graph(segs)
    assert g.node_count() == 9, f"节点数应为9，实际{g.node_count()}"
    assert g.edge_count() == 12, f"边数应为12，实际{g.edge_count()}"


def test_dijkstra_follows_roads():
    """路网路由必须贴着路走（距离 > 直线距离，且为网格折线）。"""
    nodes, segs = _make_grid(n=3)
    start = nodes[(0, 0)]   # (0,0)
    end = nodes[(2, 2)]     # (2,2)
    res = route_between(start, end, segs, algorithm="dijkstra")
    assert res["found"], "应找到路网路径"
    assert res["snapped_start"] is False and res["snapped_end"] is False

    direct = haversine(*start, *end)
    assert res["distance_m"] > direct, (
        f"路网路径应长于直线: road={res['distance_m']:.0f} > direct={direct:.0f}"
    )
    # 路径顶点数应 > 2（折线，非直线两点）
    assert len(res["coordinates"]) > 2, "路网路径应为多段折线"
    # 校验每一段都落在道路节点上（除首尾端点）
    for i in range(1, len(res["coordinates"]) - 1):
        assert res["coordinates"][i] in segs[0] or any(
            res["coordinates"][i] in s for s in segs
        ), "中间点必须是道路顶点"


def test_dijkstra_equals_astar():
    nodes, segs = _make_grid(n=4)
    start, end = nodes[(0, 0)], nodes[(3, 3)]
    d = route_between(start, end, segs, algorithm="dijkstra")
    a = route_between(start, end, segs, algorithm="astar")
    assert d["found"] and a["found"]
    assert abs(d["road_distance_m"] - a["road_distance_m"]) < 1e-6, (
        f"Dijkstra({d['road_distance_m']:.2f}) 应与 A*({a['road_distance_m']:.2f}) 等长"
    )


def test_snap_off_node():
    """起点不在路节点上时应被吸附到最近节点。"""
    nodes, segs = _make_grid(n=3)
    # 起点偏离 (0,0) 一点点
    start = (0.0001, 0.0001)
    end = nodes[(2, 2)]
    res = route_between(start, end, segs, algorithm="dijkstra", max_snap_m=3000)
    assert res["found"]
    assert res["snapped_start"] is True
    # 路径首段是从真实 start 到吸附节点
    assert res["coordinates"][0] == start


def test_no_road_fallback():
    """无路网数据时 found=False，调用方应回退。"""
    res = route_between((0, 0), (1, 1), [], algorithm="dijkstra")
    assert res["found"] is False


def test_snap_too_far():
    """超出 max_snap 视为路网未覆盖。"""
    nodes, segs = _make_grid(n=3)
    start = (50.0, 50.0)  # 离网格极远
    end = nodes[(2, 2)]
    res = route_between(start, end, segs, max_snap_m=3000)
    assert res["found"] is False


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {t.__name__} 异常: {e}")
    print(f"\n通过 {passed}/{len(tests)}")
    return passed == len(tests)


if __name__ == "__main__":
    ok = _run_all()
    sys.exit(0 if ok else 1)
