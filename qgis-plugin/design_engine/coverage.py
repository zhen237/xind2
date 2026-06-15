"""覆盖范围计算 — Okumura-Hata 传播模型"""
import math
from typing import List, Tuple, Optional


def okumura_hata_path_loss(
    frequency_mhz: float,
    distance_km: float,
    tx_height_m: float,
    rx_height_m: float = 1.5,
    environment: str = "URBAN",
) -> float:
    """
    计算Okumura-Hata模型路径损耗 (dB)。

    Args:
        frequency_mhz: 载波频率 (150-2000 MHz，外推至3500)
        distance_km: 收发距离 (1-20 km)
        tx_height_m: 发射天线有效高度 (30-200 m)
        rx_height_m: 接收天线高度 (1-10 m)
        environment: URBAN/SUBURBAN/RURAL

    Returns:
        路径损耗 (dB)
    """
    # 移动台天线高度修正因子 a(hr)
    if environment == "URBAN":
        if frequency_mhz <= 200:
            a_hr = 8.29 * (math.log10(1.54 * rx_height_m))**2 - 1.1
        else:
            a_hr = 3.2 * (math.log10(11.75 * rx_height_m))**2 - 4.97
    else:
        a_hr = (1.1 * math.log10(frequency_mhz) - 0.7) * rx_height_m \
               - (1.56 * math.log10(frequency_mhz) - 0.8)

    # 城市路径损耗
    L_urban = (69.55
               + 26.16 * math.log10(frequency_mhz)
               - 13.82 * math.log10(tx_height_m)
               + (44.9 - 6.55 * math.log10(tx_height_m)) * math.log10(max(distance_km, 0.01))
               - a_hr)

    # 环境修正
    if environment == "SUBURBAN":
        L = L_urban - 2 * (math.log10(frequency_mhz / 28))**2 - 5.4
    elif environment == "RURAL":
        L = L_urban - 4.78 * (math.log10(frequency_mhz))**2 \
            + 18.33 * math.log10(frequency_mhz) - 40.94
    else:
        L = L_urban

    return L


def calculate_rsrp(
    tx_power_dbm: float,
    tx_gain_dbi: float,
    path_loss_db: float,
    rx_gain_dbi: float = 0.0,
    shadow_fade_db: float = 8.0,
) -> float:
    """
    计算 RSRP (dBm)。

    Args:
        tx_power_dbm: 发射功率 (dBm)
        tx_gain_dbi: 发射天线增益 (dBi)
        path_loss_db: 路径损耗 (dB)
        rx_gain_dbi: 接收天线增益 (dBi)
        shadow_fade_db: 阴影衰落余量 (dB)

    Returns:
        RSRP (dBm)
    """
    return tx_power_dbm + tx_gain_dbi - path_loss_db + rx_gain_dbi - shadow_fade_db


def power_w_to_dbm(power_w: float) -> float:
    """将功率从W转换为dBm"""
    if power_w <= 0:
        return -999
    return 10 * math.log10(power_w * 1000)


def rsrp_to_color(rsrp_dbm: float, threshold_dbm: float = -110) -> Tuple[int, int, int, int]:
    """
    将RSRP值映射为RGBA颜色（用于热力图渲染）。

    Args:
        rsrp_dbm: RSRP值 (dBm)
        threshold_dbm: 阈值 (dBm)，低于此值为红色

    Returns:
        (R, G, B, A) 各0-255
    """
    # 归一化: -110dBm(红) → -80dBm(绿) → -50dBm(蓝)
    if rsrp_dbm < threshold_dbm:
        return (255, 0, 0, 180)  # 红色 — 覆盖盲区

    # 映射到 0-1 范围
    normalized = (rsrp_dbm - threshold_dbm) / (-50 - threshold_dbm)
    normalized = max(0.0, min(1.0, normalized))

    if normalized < 0.5:
        # 红 → 黄
        r = 255
        g = int(255 * normalized * 2)
        return (r, g, 0, 160)
    else:
        # 黄 → 绿
        r = int(255 * (1 - (normalized - 0.5) * 2))
        g = 255
        return (r, g, 0, 120)


def generate_coverage_raster(
    site_lon: float,
    site_lat: float,
    tx_height_m: float,
    frequency_mhz: float,
    tx_power_w: float,
    antenna_gain_dbi: float,
    radius_km: float = 2.0,
    resolution_m: int = 50,
    rsrp_threshold_dbm: float = -110,
    environment: str = "URBAN",
) -> dict:
    """
    生成单个站点的覆盖栅格数据。
    返回GeoJSON格式的热力图数据。

    Args:
        site_lon: 站点经度
        site_lat: 站点纬度
        tx_height_m: 发射天线高度 (m)
        frequency_mhz: 频率 (MHz)
        tx_power_w: 发射功率 (W)
        antenna_gain_dbi: 天线增益 (dBi)
        radius_km: 计算半径 (km)
        resolution_m: 栅格分辨率 (m)
        rsrp_threshold_dbm: RSRP阈值 (dBm)
        environment: 环境类型

    Returns:
        GeoJSON FeatureCollection
    """
    tx_power_dbm = power_w_to_dbm(tx_power_w)

    # 经纬度到km的转换系数
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(site_lat)))
    lat_per_km = 1.0 / 111.0

    points = []
    steps = int(radius_km * 1000 / resolution_m)

    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            d_lon = i * resolution_m / 1000 * lon_per_km
            d_lat = j * resolution_m / 1000 * lat_per_km
            d_km = math.sqrt((i * resolution_m / 1000)**2 + (j * resolution_m / 1000)**2)

            if d_km > radius_km:
                continue

            # 计算路径损耗和RSRP
            path_loss = okumura_hata_path_loss(
                frequency_mhz, max(d_km, 0.01), tx_height_m, environment=environment
            )
            rsrp = calculate_rsrp(tx_power_dbm, antenna_gain_dbi, path_loss)

            if rsrp >= rsrp_threshold_dbm:
                points.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [site_lon + d_lon, site_lat + d_lat]
                    },
                    "properties": {
                        "rsrp": round(rsrp, 1),
                        "distance_km": round(d_km, 3),
                        "color": rsrp_to_color(rsrp, rsrp_threshold_dbm),
                    }
                })

    return {
        "type": "FeatureCollection",
        "features": points,
        "metadata": {
            "siteLocation": [site_lon, site_lat],
            "frequencyMHz": frequency_mhz,
            "rsrpThresholdDbm": rsrp_threshold_dbm,
            "resolutionM": resolution_m,
            "totalPoints": len(points),
        }
    }


def calculate_coverage_rate(
    raster_points: List[dict],
    total_area_km2: float,
    resolution_m: float = 50,
) -> float:
    """
    计算覆盖率。

    Args:
        raster_points: 覆盖栅格点列表
        total_area_km2: 总面积 (km²)
        resolution_m: 栅格分辨率 (米)，默认 50m

    Returns:
        覆盖率 (0-1)
    """
    if total_area_km2 <= 0:
        return 0.0
    point_area_km2 = (resolution_m / 1000) ** 2
    covered_area = len(raster_points) * point_area_km2
    return min(1.0, covered_area / total_area_km2)
