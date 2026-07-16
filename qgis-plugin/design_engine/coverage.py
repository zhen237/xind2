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


def path_loss_with_directivity(
    frequency_mhz: float,
    distance_km: float,
    tx_height_m: float,
    azimuth_deg: float,
    beamwidth_h_deg: float = 65.0,
    environment: str = "URBAN",
    rx_angle_deg: float = 0.0,
) -> float:
    """
    在Okumura-Hata基础上加入天线方向性增益修正。

    方向性增益模型（简化工程版）:
    - 主瓣内 (|angle| <= BW/2): 满增益
    - 过渡区 (BW/2 < |angle| <= BW/2 + 15deg): 线性衰减
    - 旁瓣/后瓣 (|angle| > BW/2 + 15deg): 固定-15dB衰减
    """
    base_loss = okumura_hata_path_loss(
        frequency_mhz, distance_km, tx_height_m, environment=environment
    )

    # 计算相对角度差
    angle_diff = abs(((rx_angle_deg - azimuth_deg) + 180) % 360 - 180)
    half_bw = beamwidth_h_deg / 2.0

    if angle_diff <= half_bw:
        # 主瓣内: 满增益，方向性增益修正 -3dB
        directivity_correction = -3.0
    elif angle_diff <= half_bw + 15.0:
        # 过渡区: 从-3dB线性衰减到-15dB
        t = (angle_diff - half_bw) / 15.0
        directivity_correction = -3.0 - 12.0 * t
    else:
        # 旁瓣/后瓣: -15dB
        directivity_correction = -15.0

    return base_loss - directivity_correction


def calculate_rsrp_sector(
    site_lon: float, site_lat: float,
    frequency_mhz: float, tx_power_w: float,
    tx_height_m: float, azimuth_deg: float,
    beamwidth_h_deg: float = 65.0,
    antenna_gain_dbi: float = 24.0,
    rx_lon: float = None, rx_lat: float = None,
    environment: str = "URBAN",
) -> float:
    """
    计算某个接收点在特定扇区下的RSRP。
    自动计算接收点相对于扇区的角度。
    """
    tx_power_dbm = power_w_to_dbm(tx_power_w)

    # 计算距离和方位角
    dx = (rx_lon - site_lon) * 111 * math.cos(math.radians(site_lat))
    dy = rx_lat - site_lat
    distance_km = math.sqrt(dx**2 + dy**2) * 111 / 1000
    rx_angle = math.degrees(math.atan2(dx, dy)) % 360

    if distance_km < 0.01:
        distance_km = 0.01

    path_loss = path_loss_with_directivity(
        frequency_mhz, distance_km, tx_height_m,
        azimuth_deg, beamwidth_h_deg, environment, rx_angle
    )

    return tx_power_dbm + antenna_gain_dbi - path_loss - 8.0  # -8dB阴影衰落


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
    # 归一化: -110dBm(深红) → -80dBm(橙) → -50dBm(品红)
    # 品红在卫星底图上最醒目，避免淡绿被背景吃掉
    if rsrp_dbm < threshold_dbm:
        return (200, 0, 50, 240)  # 深红 — 覆盖盲区

    # 映射到 0-1 范围
    normalized = (rsrp_dbm - threshold_dbm) / (-50 - threshold_dbm)
    normalized = max(0.0, min(1.0, normalized))

    if normalized < 0.5:
        # 红 → 橙（信号较差）
        r = 255
        g = int(140 * normalized * 2)
        return (r, g, 0, 225)
    else:
        # 橙 → 品红（信号良好，品红最显眼）
        ratio = (normalized - 0.5) * 2
        g = int(140 * (1 - ratio))
        b = int(200 * ratio)
        return (255, g, b, 210)


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

    内部委托给 generate_coverage_heatmap_data，再包装为 GeoJSON FeatureCollection。
    """
    from .coverage_heatmap import generate_coverage_heatmap_data

    data = generate_coverage_heatmap_data(
        site_lon=site_lon,
        site_lat=site_lat,
        tx_height_m=tx_height_m,
        frequency_mhz=frequency_mhz,
        tx_power_w=tx_power_w,
        antenna_gain_dbi=antenna_gain_dbi,
        radius_km=radius_km,
        resolution_m=resolution_m,
        rsrp_threshold_dbm=rsrp_threshold_dbm,
        environment=environment,
    )

    features = []
    for d in data:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [d["longitude"], d["latitude"]]
            },
            "properties": {
                "rsrp": d["rsrp"],
                "distance_km": d["distance_km"],
                "path_loss": d["path_loss"],
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "siteLocation": [site_lon, site_lat],
            "frequencyMHz": frequency_mhz,
            "rsrpThresholdDbm": rsrp_threshold_dbm,
            "resolutionM": resolution_m,
            "totalPoints": len(features),
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
