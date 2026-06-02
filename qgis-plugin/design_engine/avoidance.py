"""障碍物避让 — 基于OSM/土地利用数据的站点选址约束"""
import json
from typing import List, Tuple, Optional
from shapely.geometry import Point, Polygon, shape


class AvoidanceChecker:
    """站点选址避让检查器"""

    def __init__(self):
        self.avoidance_polygons = []  # List[(geometry, rule_name, buffer_m)]

    def load_geojson(self, geojson_path: str, rule_name: str, buffer_m: float = 20.0):
        """
        从GeoJSON文件加载避让区域。

        Args:
            geojson_path: GeoJSON文件路径
            rule_name: 规则名称（如"建筑避让"）
            buffer_m: 缓冲区半径 (m)
        """
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)

        buffer_deg = buffer_m / 111000.0  # 近似转换米到度
        for feature in geojson.get('features', []):
            try:
                geom = shape(feature['geometry'])
                if geom.is_valid:
                    buffered = geom.buffer(buffer_deg)
                    self.avoidance_polygons.append((buffered, rule_name, buffer_m))
            except Exception:
                continue  # 跳过无效几何

    def load_osm_buildings(self, geojson_path: str, buffer_m: float = 20.0):
        """加载OSM建筑轮廓作为避让区域"""
        self.load_geojson(geojson_path, "建筑避让", buffer_m)

    def load_water_bodies(self, geojson_path: str, buffer_m: float = 50.0):
        """加载水体区域"""
        self.load_geojson(geojson_path, "水体避让", buffer_m)

    def load_power_lines(self, geojson_path: str, buffer_m: float = 50.0):
        """加载电力线路"""
        self.load_geojson(geojson_path, "电力线避让", buffer_m)

    def add_manual_polygon(self, coords: List[Tuple[float, float]], rule_name: str, buffer_m: float = 0):
        """
        手动添加避让多边形。

        Args:
            coords: 多边形坐标 [(lon, lat), ...]
            rule_name: 规则名称
            buffer_m: 缓冲区半径 (m)
        """
        polygon = Polygon(coords)
        if polygon.is_valid:
            buffer_deg = buffer_m / 111000.0
            buffered = polygon.buffer(buffer_deg) if buffer_m > 0 else polygon
            self.avoidance_polygons.append((buffered, rule_name, buffer_m))

    def is_site_valid(self, lon: float, lat: float) -> Tuple[bool, List[str]]:
        """
        检查站点位置是否有效。

        Args:
            lon: 经度
            lat: 纬度

        Returns:
            (是否有效, 冲突原因列表)
        """
        point = Point(lon, lat)
        conflicts = []
        for geom, rule_name, buffer_m in self.avoidance_polygons:
            try:
                if geom.contains(point):
                    conflicts.append(f"{rule_name}（{buffer_m}m缓冲区）")
            except Exception:
                continue
        return (len(conflicts) == 0, conflicts)

    def filter_valid_sites(self, sites: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """过滤出有效的站点坐标"""
        valid = []
        for lon, lat in sites:
            ok, reasons = self.is_site_valid(lon, lat)
            if ok:
                valid.append((lon, lat))
        return valid

    def get_avoidance_summary(self) -> dict:
        """获取避让规则汇总"""
        summary = {}
        for geom, rule_name, buffer_m in self.avoidance_polygons:
            if rule_name not in summary:
                summary[rule_name] = {"count": 0, "buffer_m": buffer_m}
            summary[rule_name]["count"] += 1
        return summary
