"""天线参数模型"""
from dataclasses import dataclass


@dataclass
class Antenna:
    """天线参数"""
    antenna_type: str = "AAU5313"          # 天线型号
    azimuth: float = 0.0                   # 方位角 (0-360°)
    mechanical_tilt: float = 2.0           # 机械下倾角
    electrical_tilt: float = 6.0           # 电子下倾角
    height: float = 45.0                   # 天线挂高 (m)
    band: str = "3.5GHz"                   # 频段
    power: float = 200.0                   # 发射功率 (W)
    gain: float = 24.0                     # 天线增益 (dBi)
    beamwidth_h: float = 65.0              # 水平波束宽度 (°)
    beamwidth_v: float = 15.0              # 垂直波束宽度 (°)

    def to_dict(self) -> dict:
        return {
            "type": self.antenna_type,
            "azimuth": self.azimuth,
            "mechanicalTilt": self.mechanical_tilt,
            "electricalTilt": self.electrical_tilt,
            "height": self.height,
            "band": self.band,
            "power": self.power,
            "gain": self.gain,
            "beamwidthH": self.beamwidth_h,
            "beamwidthV": self.beamwidth_v,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Antenna':
        field_map = {
            "type": "antenna_type",
            "azimuth": "azimuth",
            "mechanicalTilt": "mechanical_tilt",
            "electricalTilt": "electrical_tilt",
            "height": "height",
            "band": "band",
            "power": "power",
            "gain": "gain",
            "beamwidthH": "beamwidth_h",
            "beamwidthV": "beamwidth_v",
        }
        kwargs = {}
        for src_key, dst_key in field_map.items():
            if src_key in d:
                kwargs[dst_key] = d[src_key]
        return cls(**kwargs)
