"""通信工程规则配置"""
from dataclasses import dataclass


@dataclass
class BandConfig:
    """频段配置"""
    frequency_mhz: float
    max_radius_km: float       # 最大覆盖半径
    ideal_isr_km: float        # 理想站间距 (Inter-Site Distance)
    propagation_model: str     # 使用的传播模型


# 默认频段参数
BAND_CONFIGS = {
    "700MHz": BandConfig(700, 5.0, 2.5, "Okumura-Hata"),
    "2.6GHz": BandConfig(2600, 2.0, 1.0, "Okumura-Hata"),
    "3.5GHz": BandConfig(3500, 1.0, 0.5, "UMa"),
    "4.9GHz": BandConfig(4900, 0.5, 0.3, "UMa"),
}

# 基站类型默认参数
DEFAULT_SITE_PARAMS = {
    "MACRO": {
        "tower_height_min": 25,
        "tower_height_max": 50,
        "antennas_per_sector": 1,
        "default_tower_height": 35.0,
        "default_sectors": 3,
    },
    "SMALL": {
        "tower_height_min": 10,
        "tower_height_max": 25,
        "antennas_per_sector": 1,
        "default_tower_height": 20.0,
        "default_sectors": 3,
    },
    "INDOOR": {
        "tower_height_min": 2,
        "tower_height_max": 5,
        "antennas_per_sector": 1,
        "default_tower_height": 3.0,
        "default_sectors": 0,  # 全向天线
    },
}

# 安全避让规则
AVOIDANCE_RULES = {
    "water": {"buffer_m": 50, "description": "水体缓冲区50m"},
    "protected_area": {"buffer_m": 100, "description": "生态保护区缓冲区100m"},
    "building": {"buffer_m": 20, "description": "建筑缓冲区20m"},
    "power_line": {"buffer_m": 50, "description": "电力线缓冲区50m"},
}

# 天线型号默认参数
ANTENNA_MODELS = {
    "AAU5313": {
        "band": "3.5GHz",
        "gain_dbi": 24.0,
        "beamwidth_h": 65.0,
        "beamwidth_v": 15.0,
        "max_power_w": 200.0,
    },
    "AAU5639": {
        "band": "2.6GHz",
        "gain_dbi": 22.0,
        "beamwidth_h": 65.0,
        "beamwidth_v": 15.0,
        "max_power_w": 160.0,
    },
    "RRU5301": {
        "band": "700MHz",
        "gain_dbi": 18.0,
        "beamwidth_h": 65.0,
        "beamwidth_v": 15.0,
        "max_power_w": 120.0,
    },
}
