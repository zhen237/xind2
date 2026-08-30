"""机房数据模型"""
from dataclasses import dataclass


@dataclass
class MachineRoom:
    """通信机房"""
    room_id: str                    # 机房编码，如 "ROOM-001"
    name: str                       # 机房名称
    longitude: float                # 经度 (EPSG:4326)
    latitude: float                 # 纬度 (EPSG:4326)
    room_type: str = "汇聚机房"     # 机房类型
    capacity: float = 50.0          # 容量(kVA)
    fibre_used: float = 6.0         # 光纤已用(芯)，供 S3 FT-001 容量校验
    power_supply: str = "AC220V"    # 供电方式

    def to_dict(self) -> dict:
        """转为字典（与 design_dock.py 中裸字典格式一致）"""
        return {
            'room_id': self.room_id,
            'name': self.name,
            'room_type': self.room_type,
            'longitude': self.longitude,
            'latitude': self.latitude,
            'capacity': self.capacity,            # 供电容量(kVA)；前端送审时映射为 S3 FT-001 capacity
            'power_supply': self.power_supply,
            # ── S3 智能审查对齐字段（2026-08-30）──
            # 通信机房声明 deviceType='communication_room' → FT-001 容量 + EL-003 接地；
            # fibreUsed 为已用光纤(芯)，与 capacity 共同判定是否超容。
            'deviceType': 'communication_room',
            'fibreUsed': self.fibre_used,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'MachineRoom':
        """从字典解析"""
        return cls(
            room_id=d.get('room_id', ''),
            name=d.get('name', ''),
            room_type=d.get('room_type', '汇聚机房'),
            longitude=d.get('longitude', 0),
            latitude=d.get('latitude', 0),
            capacity=d.get('capacity', 50.0),
            fibre_used=d.get('fibre_used', 6.0),
            power_supply=d.get('power_supply', 'AC220V'),
        )
