"""线缆长度估算引擎 — Haversine 距离 + 竖井高度 + 预留系数。"""
import math
import logging
from typing import Optional

logger = logging.getLogger("s4-engine.cable")

FIXED_RF_JUMPER_M = 3.0       # 射频频线固定 3m
FIBER_SLACK_FACTOR = 1.2      # 光纤弯曲余量
RISER_HEIGHT_M = 5.0          # 默认竖井高度 (设备间→塔顶)


def haversine_m(lat1: float, lng1: float, alt1: float,
                lat2: float, lng2: float, alt2: float) -> float:
    """计算两点间三维距离（米）。水平用 Haversine，垂直取绝对值。"""
    R = 6371000.0  # 地球半径 (米)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    horizontal = R * c
    vertical = abs(alt2 - alt1)
    return math.sqrt(horizontal ** 2 + vertical ** 2)


def estimate_cable_length(device_coords: dict, target_coords: dict,
                          calc_method: str) -> Optional[dict]:
    """
    根据 calcMethod 估算单根线缆长度。

    - fixed_3m: 固定 3m
    - fixed_15m: 固定 15m
    - horizontal_distance_x1.2: 水平距 x 1.2
    - distance_plus_riser: 水平距 + 竖井高度
    - tower_to_ground: 塔顶到地面高度（取 alt 差）
    - rack_to_power: 机柜内部布线，固定 3m
    - rack_ground: 机柜/设备接地，固定 2m
    - short_ground: 短接地线，固定 2m
    - dist_to_power_panel: 到配电箱距离 + 2m
    - battery_to_power: 电池到电源，固定 2m
    - tower_top_to_bbu: 塔顶到 BBU，水平 + 塔高
    """
    dlat = device_coords.get("lat", 0)
    dlng = device_coords.get("lng", 0)
    dalt = device_coords.get("alt", 0)
    tlat = target_coords.get("lat", 0)
    tlng = target_coords.get("lng", 0)
    talt = target_coords.get("alt", 0)

    h_dist = haversine_m(dlat, dlng, dalt, tlat, tlng, talt)

    if calc_method == "fixed_3m":
        length = FIXED_RF_JUMPER_M
    elif calc_method == "fixed_15m":
        length = 15.0
    elif calc_method == "horizontal_distance_x1.2":
        # 仅算水平距离 x 1.2，忽略垂直（如 AAU-BBU 光纤走弱电井）
        h_horiz = haversine_m(dlat, dlng, 0, tlat, tlng, 0)
        length = h_horiz * FIBER_SLACK_FACTOR
    elif calc_method == "distance_plus_riser":
        length = h_dist + RISER_HEIGHT_M
    elif calc_method == "tower_to_ground":
        length = abs(dalt - talt) + 2.0  # 塔高 + 2m 地面预留
    elif calc_method in ("rack_to_power", "battery_to_power", "rack_ground", "short_ground"):
        length = 2.0
    elif calc_method == "dist_to_power_panel":
        length = h_dist + 2.0
    elif calc_method == "tower_top_to_bbu":
        length = h_dist  # 含水平和垂直差异
    else:
        length = h_dist  # 默认直接用 Haversine 三维距离

    return {
        "single_length_m": round(length, 2),
        "method": calc_method,
    }
