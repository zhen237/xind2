"""馈线电缆数据模型（供 S3 智能审查 EL-001 弯曲半径 / EL-002 载流量比对）"""
from dataclasses import dataclass, field


@dataclass
class Cable:
    """通信基站馈线电缆（天线/设备至机房之间的电力/信号馈线）"""
    cable_id: str = ""                      # 电缆编码，如 "CABLE-001"
    name: str = ""                          # 电缆名称
    longitude: float = 0.0                  # 经度 (EPSG:4326)，用于 S1 定位
    latitude: float = 0.0                   # 纬度 (EPSG:4326)
    # ── S3 智能审查对齐字段（2026-08-30）──
    # 线缆声明 deviceType='communication_cable' → 命中 S3 CABLE_TYPE_MAP，触发
    #   EL-001 弯曲半径（cableDiameter + bendingRadius）
    #   EL-002 载流量（crossSection + actualCurrent + material）
    cable_type: str = "communication_cable"
    cable_diameter: float = 25.0            # 电缆外径(mm)；弯曲半径标准=15×该值
    bending_radius: float = 400.0           # 实测弯曲半径(mm)；≥15×缆径(375)才合规
    cross_section: float = 50.0             # 导体截面(mm²)；铜缆查表得额定载流量
    actual_current: float = 80.0            # 实测载流量(A)；≤额定/1.25 才合规
    material: str = "copper"                # 导体材质：copper / aluminum

    def to_dict(self) -> dict:
        """转为字典（camelCase 顶层字段，与前端 liftS3TopLevelFields 期望一致）"""
        return {
            'cableId': self.cable_id,
            'name': self.name,
            'longitude': self.longitude,
            'latitude': self.latitude,
            'deviceType': self.cable_type,
            'cableDiameter': self.cable_diameter,
            'bendingRadius': self.bending_radius,
            'crossSection': self.cross_section,
            'actualCurrent': self.actual_current,
            'material': self.material,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Cable':
        """从字典解析（兼容 camelCase / snake_case）"""
        return cls(
            cable_id=d.get('cableId') or d.get('cable_id', ''),
            name=d.get('name', ''),
            longitude=float(d.get('longitude', 0) or 0),
            latitude=float(d.get('latitude', 0) or 0),
            cable_type=d.get('deviceType') or d.get('cable_type', 'communication_cable'),
            cable_diameter=float(d.get('cableDiameter') or d.get('cable_diameter', 25.0) or 25.0),
            bending_radius=float(d.get('bendingRadius') or d.get('bending_radius', 400.0) or 400.0),
            cross_section=float(d.get('crossSection') or d.get('cross_section', 50.0) or 50.0),
            actual_current=float(d.get('actualCurrent') or d.get('actual_current', 80.0) or 80.0),
            material=d.get('material', 'copper'),
        )
