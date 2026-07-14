# -*- coding: utf-8 -*-
"""路网感知管线寻优引擎 (T3)

提供基于道路矢量数据的 Dijkstra / A* 最短路径算法，
消除原 `pipeline.py` 直线/曼哈顿启发式"非路网感知"的短板（规格 FR-6 / AC-3 点名）。

设计原则
--------
- **零第三方依赖**：仅用标准库 ``heapq`` + ``math``，不引入 networkx / numpy，
  避免给 QGIS 自带 Python 环境增加负担（项目已清理过 numpy 死依赖）。
- **与 QGIS 完全解耦**：核心算法只消费"路段列表"
  （``List[List[(lon, lat), ...]]``），由调用方负责把矢量图层转成路段。
  这样本模块可直接在沙箱用标准库单测，无需 QGIS。
- **优雅降级**：无路网数据时调用方回退直线/曼哈顿路由，不抛异常。
"""

from typing import List, Tuple, Dict, Optional, Callable
import math
import heapq

# 节点坐标散列精度（度）。7 位小数 ≈ 1cm，足以区分道路节点。
_NODE_PRECISION = 7


def _node_key(lon: float, lat: float) -> Tuple[float, float]:
    """把浮点坐标散列成稳定图节点键（去浮点抖动）。"""
    return (round(lon, _NODE_PRECISION), round(lat, _NODE_PRECISION))


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """两点间大圆距离（米），作为路网边的权重。"""
    R = 6371000.0  # 地球半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class RoadGraph:
    """无向带权路网图。

    节点为道路顶点（经纬度），边为相邻顶点间的路段，权重为 geodesic 距离（米）。
    """

    def __init__(self):
        self._nodes: Dict[Tuple[float, float], Tuple[float, float]] = {}   # key -> (lon, lat)
        self._adj: Dict[Tuple[float, float], List[Tuple[Tuple[float, float], float]]] = {}

    # ---- 建图 ----------------------------------------------------------------
    def add_segment(self, a: Tuple[float, float], b: Tuple[float, float]) -> None:
        """添加一条无向路段 a↔b。"""
        ka, kb = _node_key(*a), _node_key(*b)
        if ka not in self._nodes:
            self._nodes[ka] = a
        if kb not in self._nodes:
            self._nodes[kb] = b
        w = haversine(a[0], a[1], b[0], b[1])
        self._adj.setdefault(ka, []).append((kb, w))
        self._adj.setdefault(kb, []).append((ka, w))

    def add_road(self, vertices: List[Tuple[float, float]]) -> None:
        """添加一条由若干顶点连成的道路（逐段 add_segment）。"""
        for i in range(len(vertices) - 1):
            self.add_segment(vertices[i], vertices[i + 1])

    # ---- 查询 ----------------------------------------------------------------
    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return sum(len(neighbors) for neighbors in self._adj.values()) // 2

    def nearest_node(self, lon: float, lat: float) -> Optional[Tuple[float, float]]:
        """返回距离 (lon, lat) 最近的图节点键。

        采用经纬度平方平面近似（局部小区域内等价于实际距离排序），适合城市级路网。
        空图返回 None。
        """
        best: Optional[Tuple[float, float]] = None
        best_d = None
        for key in self._nodes:
            nlon, nlat = self._nodes[key]
            d = (nlon - lon) ** 2 + (nlat - lat) ** 2
            if best_d is None or d < best_d:
                best_d = d
                best = key
        return best

    def _reconstruct(self, prev: Dict, start: tuple, end: tuple) -> List[tuple]:
        path = [end]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path

    # ---- 最短路 --------------------------------------------------------------
    def dijkstra(self, start_key: tuple, end_key: tuple):
        """Dijkstra。返回 (节点键路径, 总距离米)；不可达返回 (None, inf)。"""
        if start_key not in self._nodes or end_key not in self._nodes:
            return None, float("inf")
        if start_key == end_key:
            return [start_key], 0.0

        dist: Dict[tuple, float] = {start_key: 0.0}
        prev: Dict[tuple, tuple] = {}
        visited = set()
        pq: List[Tuple[float, tuple]] = [(0.0, start_key)]

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == end_key:
                break
            for v, w in self._adj.get(u, []):
                if v in visited:
                    continue
                nd = d + w
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))

        if end_key not in dist:
            return None, float("inf")
        return self._reconstruct(prev, start_key, end_key), dist[end_key]

    def astar(self, start_key: tuple, end_key: tuple,
              heuristic: Optional[Callable] = None):
        """A*。默认启发式为到终点的 haversine 距离（可采纳，保证最优）。"""
        if start_key not in self._nodes or end_key not in self._nodes:
            return None, float("inf")
        if start_key == end_key:
            return [start_key], 0.0
        if heuristic is None:
            eg_lon, eg_lat = self._nodes[end_key]
            heuristic = lambda k: haversine(self._nodes[k][0], self._nodes[k][1], eg_lon, eg_lat)

        g: Dict[tuple, float] = {start_key: 0.0}
        prev: Dict[tuple, tuple] = {}
        visited = set()
        pq: List[Tuple[float, tuple]] = [(heuristic(start_key), start_key)]

        while pq:
            f, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == end_key:
                break
            for v, w in self._adj.get(u, []):
                if v in visited:
                    continue
                ng = g[u] + w
                if ng < g.get(v, float("inf")):
                    g[v] = ng
                    prev[v] = u
                    heapq.heappush(pq, (ng + heuristic(v), v))

        if end_key not in g:
            return None, float("inf")
        return self._reconstruct(prev, start_key, end_key), g[end_key]


def build_road_graph(segments: List[List[Tuple[float, float]]]) -> RoadGraph:
    """从路段列表构建路网图。

    Args:
        segments: 道路矢量，每条道路为顶点列表 ``[(lon, lat), ...]``。
                  支持 LineString（2 点）与 MultiLineString / 折线（多点）。

    Returns:
        RoadGraph
    """
    graph = RoadGraph()
    for seg in segments:
        if not seg or len(seg) < 2:
            continue
        graph.add_road(seg)
    return graph


def route_between(
    start: Tuple[float, float],
    end: Tuple[float, float],
    segments: List[List[Tuple[float, float]]],
    algorithm: str = "dijkstra",
    snap: bool = True,
    max_snap_m: float = 3000.0,
) -> Dict:
    """在路网上求 start→end 的最短敷设路径（路网感知）。

    Args:
        start: 起点 (lon, lat)，如基站坐标
        end: 终点 (lon, lat)，如机房坐标
        segments: 道路矢量路段列表
        algorithm: "dijkstra" 或 "astar"
        snap: 是否把起终点吸附到最近道路节点（站点通常不在路中心）
        max_snap_m: 允许的最大吸附距离（米），超出视为路网未覆盖 → found=False

    Returns:
        dict: {
            "found": bool,
            "coordinates": List[(lon, lat)],   # 完整路由（含起终点 + 路网节点）
            "distance_m": float,               # 实际敷设长度（含吸附段）
            "road_distance_m": float,          # 纯路网段长度
            "snapped_start": bool,
            "snapped_end": bool,
            "algorithm": str,
            "node_count": int,
        }
    """
    result = {
        "found": False,
        "coordinates": [start, end],
        "distance_m": haversine(*start, *end),
        "road_distance_m": 0.0,
        "snapped_start": False,
        "snapped_end": False,
        "algorithm": algorithm,
        "node_count": 0,
    }

    if not segments:
        return result

    graph = build_road_graph(segments)
    result["node_count"] = graph.node_count()
    if graph.node_count() == 0:
        return result

    if snap:
        sk = graph.nearest_node(*start)
        ek = graph.nearest_node(*end)
        if sk is None or ek is None:
            return result
        snap_start_m = haversine(*start, *graph._nodes[sk])
        snap_end_m = haversine(*end, *graph._nodes[ek])
        result["snapped_start"] = snap_start_m > 1.0
        result["snapped_end"] = snap_end_m > 1.0
        if snap_start_m > max_snap_m or snap_end_m > max_snap_m:
            # 站点离任何道路都太远，视为路网未覆盖
            return result
    else:
        sk = _node_key(*start)
        ek = _node_key(*end)
        if sk not in graph._nodes or ek not in graph._nodes:
            return result

    if algorithm == "astar":
        path, road_dist = graph.astar(sk, ek)
    else:
        path, road_dist = graph.dijkstra(sk, ek)

    if path is None:
        return result

    road_coords = [graph._nodes[k] for k in path]
    # 完整路由：起点 → [吸附段] → 路网节点路径 → [吸附段] → 终点
    coordinates = [start] + road_coords + [end]
    total = haversine(*start, *road_coords[0]) + road_dist + \
        haversine(*road_coords[-1], *end)

    result.update({
        "found": True,
        "coordinates": coordinates,
        "distance_m": round(total, 2),
        "road_distance_m": round(road_dist, 2),
    })
    return result
