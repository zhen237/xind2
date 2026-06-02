"""站点数据模型"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Site:
    """通信基站站点"""
    site_id: str                           # 站点编码，如 "BTS-WH-001"
    name: str                              # 站点名称
    longitude: float                       # 经度 (EPSG:4326)
    latitude: float                        # 纬度 (EPSG:4326)
    site_type: str = "MACRO"               # MACRO/SMALL/INDOOR
    tower_type: str = "MONOPOLE"           # MONOPOLE/LATTICE/TOWER
    tower_height: float = 35.0             # 塔高 (m)
    scenario: str = "URBAN"                # URBAN/SUBURBAN/RURAL
    status: str = "PLANNED"                # PLANNED/APPROVED/BUILT
    antennas: List['Antenna'] = field(default_factory=list)
    properties: dict = field(default_factory=dict)

    def to_geojson_feature(self) -> dict:
        """转为GeoJSON Feature"""
        from .antenna import Antenna
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude]
            },
            "properties": {
                "siteId": self.site_id,
                "name": self.name,
                "siteType": self.site_type,
                "towerType": self.tower_type,
                "towerHeight": self.tower_height,
                "scenario": self.scenario,
                "antennas": [a.to_dict() for a in self.antennas],
                **self.properties
            }
        }

    @classmethod
    def from_geojson_feature(cls, feature: dict) -> 'Site':
        """从GeoJSON Feature解析"""
        from .antenna import Antenna
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [0, 0])
        return cls(
            site_id=props.get("siteId", ""),
            name=props.get("name", ""),
            longitude=coords[0],
            latitude=coords[1],
            site_type=props.get("siteType", "MACRO"),
            tower_type=props.get("towerType", "MONOPOLE"),
            tower_height=props.get("towerHeight", 35.0),
            scenario=props.get("scenario", "URBAN"),
            antennas=[Antenna.from_dict(a) for a in props.get("antennas", [])],
            properties={k: v for k, v in props.items()
                        if k not in ("siteId", "name", "siteType", "towerType",
                                     "towerHeight", "scenario", "antennas")}
        )

    def distance_to(self, other: 'Site') -> float:
        """计算到另一个站点的距离（km），使用Haversine公式"""
        import math
        R = 6371.0
        lat1, lat2 = math.radians(self.latitude), math.radians(other.latitude)
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
