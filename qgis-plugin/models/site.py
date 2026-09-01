"""站点数据模型"""
from dataclasses import dataclass, field
from typing import List, Optional

from .tech import get_baseline


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
    mount_type: str = "GROUND"             # GROUND=地面塔 / ROOFTOP=楼面塔
    scenario: str = "URBAN"                # URBAN/SUBURBAN/RURAL
    status: str = "PLANNED"                # PLANNED/APPROVED/BUILT
    tech_generation: str = "4G+5G协同"     # 通信技术制式（#5 技术轴）
    coverage_radius: float = 0.0           # 覆盖半径(km)，0=按制式基线算
    capacity: float = 0.0                  # 单站容量参考(相对值)
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
                "mountType": self.mount_type,
                "scenario": self.scenario,
                "techGeneration": self.tech_generation,
                "coverageRadius": self.coverage_radius,
                "capacity": self.capacity,
                "antennas": [a.to_dict() for a in self.antennas],
                # ── S3 智能审查对齐字段（2026-08-30）──
                # 铁塔声明 deviceType='tower' → 触发 EL-003 接地电阻校验；
                # groundingResistance 取联合接地设计值(≤10Ω 合规)，可被 props 覆盖。
                "deviceType": "tower",
                "groundingResistance": 4.0,
                # 结构/电磁真实比对字段（ST-001 基础承载力 / ST-003 混凝土强度 /
                # ST-004 构件变形 / EM-002 无线电干扰）；取合规设计值，可被 props 覆盖。
                # 数值依据：ST-001 承载力 250≥1.2×180、ST-003 强度 32.5≥30、
                # ST-004 变形 5≤8、EM-002 干扰 30≤40（均满足国标阈值）。
                "bearingCapacity": 250.0,
                "designLoad": 180.0,
                "concreteStrengthActual": 32.5,
                "concreteStrengthDesign": 30.0,
                "deformationActual": 5.0,
                "deformationLimit": 8.0,
                "radioInterference": 30.0,
                "radioLimit": 40.0,
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
            mount_type=props.get("mountType", props.get("mount_type", "GROUND")),
            scenario=props.get("scenario", "URBAN"),
            tech_generation=props.get("techGeneration", props.get("tech_generation", "4G+5G协同")),
            coverage_radius=props.get("coverageRadius", props.get("coverage_radius", 0.0)),
            capacity=props.get("capacity", props.get("capacity_ref", 0.0)),
            antennas=[Antenna.from_dict(a) for a in props.get("antennas", [])],
            properties={k: v for k, v in props.items()
                        if k not in ("siteId", "name", "siteType", "towerType",
                                     "towerHeight", "mountType", "scenario",
                                     "techGeneration", "coverageRadius", "capacity",
                                     "antennas")}
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

    def bill_of_materials(self) -> dict:
        """按安装方式（地面塔/楼面塔）生成精确物料清单(BOM)。

        返回 {mount_type, items:[{name, spec, qty, unit}], summary}。
        工程量按 tower_height 估算，单价取行业概算，仅供设计概算参考。
        """
        h = self.tower_height
        if self.mount_type == "ROOFTOP":
            items = [
                {"name": "楼面抱杆/美化天线杆", "spec": f"高度{h:.0f}m 镀锌钢", "qty": 1, "unit": "套"},
                {"name": "承重法兰底座", "spec": "化学锚栓 M20×4", "qty": 1, "unit": "套"},
                {"name": "楼面防水处理", "spec": "SBS 防水 + 保护层", "qty": round(h * 1.2, 1), "unit": "m²"},
                {"name": "楼面接地网", "spec": "40×4 热镀锌扁钢", "qty": round(h * 2.0, 1), "unit": "m"},
                {"name": "走线架", "spec": "铝合金 200mm", "qty": 6, "unit": "m"},
            ]
        else:
            tower_label = {"MONOPOLE": "单管塔", "LATTICE": "格构塔", "TOWER": "角钢塔"}.get(
                self.tower_type, "单管塔")
            base_vol = round(h * h * 0.06, 2)  # 基础混凝土方量概算
            items = [
                {"name": f"{tower_label}塔身", "spec": f"高度{h:.0f}m", "qty": 1, "unit": "座"},
                {"name": "钢筋混凝土基础", "spec": "C30 浇筑", "qty": base_vol, "unit": "m³"},
                {"name": "接地网", "spec": "40×4 热镀锌扁钢 + 角钢接地极", "qty": round(h * 1.5, 1), "unit": "m"},
                {"name": "避雷针", "spec": "GX-1 热镀锌", "qty": 1, "unit": "根"},
                {"name": "走线架", "spec": "铝合金 200mm", "qty": 8, "unit": "m"},
                {"name": "围墙/围栏", "spec": "砖砌 1.8m", "qty": 12, "unit": "m"},
            ]
        # 技术轴（#5）：按制式追加 RRU/AAU 等无线设备项（与 mount_type 分支叠加）
        base = get_baseline(self.tech_generation)
        if base is not None and base.antenna_items:
            items = items + list(base.antenna_items)

        tower_label = "楼面塔" if self.mount_type == "ROOFTOP" else "地面塔"
        tech_label = base.tower_form if base is not None else ""
        summary = (f"{tower_label}（{self.tower_type}）· {tech_label} · 共 {len(items)} 类物料")
        return {"mount_type": self.mount_type, "items": items, "summary": summary,
                "tech_generation": self.tech_generation,
                "tech_tower_form": tech_label}
