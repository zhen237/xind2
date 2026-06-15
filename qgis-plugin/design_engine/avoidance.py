"""障碍物避让 — 基于OSM/土地利用数据的站点选址约束

支持两种模式：
- Shapely模式：精确几何计算（推荐）
- Fallback模式：简单圆形/包围盒检测（无需额外依赖）
"""
import json
import math
from typing import List, Tuple, Dict, Any

# 尝试导入Shapely
try:
    from shapely.geometry import Point, Polygon, shape as shapely_shape
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


def _point_in_polygon_simple(lon: float, lat: float, polygon_coords: List[Tuple[float, float]]) -> bool:
    """射线法判断点是否在多边形内（fallback实现）"""
    n = len(polygon_coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _buffer_polygon_simple(coords: List[Tuple[float, float]], buffer_deg: float) -> List[Tuple[float, float]]:
    """简单缓冲区：将多边形各点向外扩展（fallback实现）"""
    if not coords:
        return coords
    # 计算中心点
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    # 向外扩展
    buffered = []
    for x, y in coords:
        dx = x - cx
        dy = y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            scale = (dist + buffer_deg) / dist
            buffered.append((cx + dx * scale, cy + dy * scale))
        else:
            buffered.append((x, y))
    return buffered


class SimplePolygon:
    """简单多边形封装（fallback模式）"""

    def __init__(self, coords: List[Tuple[float, float]]):
        self.coords = coords
        self._bbox = self._calc_bbox()

    def _calc_bbox(self):
        if not self.coords:
            return (0, 0, 0, 0)
        lons = [c[0] for c in self.coords]
        lats = [c[1] for c in self.coords]
        return (min(lons), min(lats), max(lons), max(lats))

    def contains(self, lon: float, lat: float) -> bool:
        # 先检查包围盒
        if not (self._bbox[0] <= lon <= self._bbox[2] and self._bbox[1] <= lat <= self._bbox[3]):
            return False
        return _point_in_polygon_simple(lon, lat, self.coords)

    def buffer(self, buffer_deg: float):
        buffered_coords = _buffer_polygon_simple(self.coords, buffer_deg)
        return SimplePolygon(buffered_coords)

    @property
    def is_valid(self):
        return len(self.coords) >= 3


class AvoidanceChecker:
    """站点选址避让检查器"""

    def __init__(self):
        self.avoidance_polygons: List[Tuple[Any, str, float]] = []  # List[(geometry, rule_name, buffer_m)]

    def load_geojson(self, geojson_path: str, rule_name: str, buffer_m: float = 20.0):
        """加载GeoJSON避让数据"""
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)

        buffer_deg = buffer_m / 111000.0
        for feature in geojson.get('features', []):
            try:
                geom_data = feature['geometry']
                if HAS_SHAPELY:
                    geom = shapely_shape(geom_data)
                    if geom.is_valid:
                        buffered = geom.buffer(buffer_deg)
                        self.avoidance_polygons.append((buffered, rule_name, buffer_m))
                else:
                    polygons_coords = self._extract_coords(geom_data)
                    for coords in polygons_coords:
                        if coords:
                            poly = SimplePolygon(coords)
                            if poly.is_valid:
                                buffered = poly.buffer(buffer_deg)
                                self.avoidance_polygons.append((buffered, rule_name, buffer_m))
            except Exception:
                continue

    def _extract_coords(self, geom_data: Dict) -> List[List[Tuple[float, float]]]:
        """从GeoJSON geometry提取坐标，返回多边形坐标列表的列表

        Returns:
            List[List[Tuple[float, float]]]:
            - Polygon: [[outer_ring_coords]]
            - MultiPolygon: [[ring_1], [ring_2], ...]
            - Point: [[point_coord]]
        """
        geom_type = geom_data.get('type', '')
        coords = geom_data.get('coordinates', [])

        if geom_type == 'Polygon' and coords:
            return [[(c[0], c[1]) for c in coords[0] if len(c) >= 2]]
        elif geom_type == 'MultiPolygon' and coords:
            result = []
            for polygon in coords:
                if polygon:
                    result.append([(c[0], c[1]) for c in polygon[0] if len(c) >= 2])
            return result
        elif geom_type == 'Point' and coords:
            return [[(coords[0], coords[1])]]
        return []

    def load_osm_buildings(self, geojson_path: str, buffer_m: float = 20.0):
        self.load_geojson(geojson_path, "建筑避让", buffer_m)

    def load_water_bodies(self, geojson_path: str, buffer_m: float = 50.0):
        self.load_geojson(geojson_path, "水体避让", buffer_m)

    def load_power_lines(self, geojson_path: str, buffer_m: float = 50.0):
        self.load_geojson(geojson_path, "电力线避让", buffer_m)

    def add_manual_polygon(self, coords: List[Tuple[float, float]], rule_name: str, buffer_m: float = 0):
        """手动添加避让多边形"""
        if HAS_SHAPELY:
            polygon = Polygon(coords)
            if polygon.is_valid:
                buffer_deg = buffer_m / 111000.0
                buffered = polygon.buffer(buffer_deg) if buffer_m > 0 else polygon
                self.avoidance_polygons.append((buffered, rule_name, buffer_m))
        else:
            poly = SimplePolygon(coords)
            if poly.is_valid:
                buffer_deg = buffer_m / 111000.0
                buffered = poly.buffer(buffer_deg) if buffer_m > 0 else poly
                self.avoidance_polygons.append((buffered, rule_name, buffer_m))

    def is_site_valid(self, lon: float, lat: float) -> Tuple[bool, List[str]]:
        """检查站点是否有效（不在避让区域内）"""
        conflicts = []
        for geom, rule_name, buffer_m in self.avoidance_polygons:
            try:
                if HAS_SHAPELY:
                    point = Point(lon, lat)
                    if geom.contains(point):
                        conflicts.append(f"{rule_name}（{buffer_m}m缓冲区）")
                else:
                    if geom.contains(lon, lat):
                        conflicts.append(f"{rule_name}（{buffer_m}m缓冲区）")
            except Exception:
                continue
        return (len(conflicts) == 0, conflicts)

    def filter_valid_sites(self, sites: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """过滤出有效站点"""
        valid = []
        for lon, lat in sites:
            ok, reasons = self.is_site_valid(lon, lat)
            if ok:
                valid.append((lon, lat))
        return valid

    def get_avoidance_summary(self) -> dict:
        """获取避让区域摘要"""
        summary = {}
        for geom, rule_name, buffer_m in self.avoidance_polygons:
            if rule_name not in summary:
                summary[rule_name] = {"count": 0, "buffer_m": buffer_m}
            summary[rule_name]["count"] += 1
        return summary
