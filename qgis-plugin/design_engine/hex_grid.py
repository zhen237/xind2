"""蜂窝拓扑站址布局生成"""
import math
from typing import List, Tuple, Optional

from models.site import Site
from models.antenna import Antenna
from .rules import BAND_CONFIGS, DEFAULT_SITE_PARAMS, BandConfig


def generate_hex_grid(
    bbox: Tuple[float, float, float, float],  # (min_lon, min_lat, max_lon, max_lat)
    isr_km: float,
    rotation_deg: float = 0.0,
) -> List[Tuple[float, float]]:
    """
    生成六边形网格中心点列表。
    采用偏移行法(offset rows)生成整齐六边形。

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        isr_km: 站间距 (km)
        rotation_deg: 网格旋转角度（度），默认0

    Returns:
        中心点坐标列表 [(lon, lat), ...]
    """
    lon_min, lat_min, lon_max, lat_max = bbox
    # 将km转为经纬度近似值（中纬度地区）
    mid_lat = (lat_min + lat_max) / 2
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(mid_lat)))
    lat_per_km = 1.0 / 111.0

    isr_lon = isr_km * lon_per_km
    isr_lat = isr_km * lat_per_km

    # 六边形列间距 = sqrt(3)*ISR, 行交替偏移 ISR/2
    col_spacing = math.sqrt(3) * isr_lon
    row_spacing = 1.5 * isr_lat

    centers = []
    row = 0
    y = lat_min - row_spacing  # 向外扩展一圈
    while y <= lat_max + row_spacing:
        x_offset = (isr_lon / 2) if row % 2 == 1 else 0
        x = lon_min - col_spacing + x_offset
        while x <= lon_max + col_spacing:
            centers.append((x, y))
            x += col_spacing
        y += row_spacing
        row += 1

    # 如果指定了旋转角度，以bbox中心为原点旋转所有网格中心点，并剔除旋转后超出bbox的点
    if rotation_deg != 0.0:
        cx = (lon_min + lon_max) / 2
        cy = (lat_min + lat_max) / 2
        theta = math.radians(rotation_deg)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        rotated = []
        for x, y in centers:
            dx = x - cx
            dy = y - cy
            rx = cx + dx * cos_t - dy * sin_t
            ry = cy + dx * sin_t + dy * cos_t
            if lon_min <= rx <= lon_max and lat_min <= ry <= lat_max:
                rotated.append((rx, ry))
        centers = rotated

    return centers


def generate_sites_from_grid(
    grid_centers: List[Tuple[float, float]],
    band_config: BandConfig,
    site_type: str = "MACRO",
    tower_height: float = 35.0,
    scenario: str = "URBAN",
    num_sectors: int = 3,
    existing_sites: Optional[List[Site]] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> List[Site]:
    """
    从网格中心点生成Site列表，自动配置天线参数。
    排除与已有站点重叠的中心点。

    Args:
        grid_centers: 网格中心点 [(lon, lat), ...]
        band_config: 频段配置
        site_type: 基站类型 MACRO/SMALL/INDOOR
        tower_height: 塔高 (m)
        scenario: 场景 URBAN/SUBURBAN/RURAL
        num_sectors: 扇区数 (0=全向)
        existing_sites: 已有站点列表（用于避让）
        bbox: 设计区域边界，用于裁剪超出范围的点

    Returns:
        生成的Site列表
    """
    existing_coords = set()
    if existing_sites:
        for es in existing_sites:
            existing_coords.add((round(es.longitude, 6), round(es.latitude, 6)))

    sites = []
    for i, (lon, lat) in enumerate(grid_centers):
        # 裁剪：超出设计区域的点跳过
        if bbox:
            lon_min, lat_min, lon_max, lat_max = bbox
            if lon < lon_min or lon > lon_max or lat < lat_min or lat > lat_max:
                continue

        # 跳过与已有站点过近的位置（< 200m）
        too_close = False
        for ex_lon, ex_lat in existing_coords:
            dist_deg = math.sqrt((lon - ex_lon)**2 + (lat - ex_lat)**2)
            dist_m = dist_deg * 111000
            if dist_m < 200:
                too_close = True
                break
        if too_close:
            continue

        site = Site(
            site_id=f"BTS-{scenario[:4].upper()}-{i+1:03d}",
            name=f"{scenario}-{i+1:03d}",
            longitude=round(lon, 7),
            latitude=round(lat, 7),
            site_type=site_type,
            tower_height=tower_height,
            scenario=scenario,
        )

        # 配置天线
        if num_sectors == 0:
            # 全向天线
            antenna = Antenna(
                antenna_type=_select_antenna_type(band_config.frequency_mhz),
                azimuth=0.0,
                height=tower_height,
                band=f"{int(band_config.frequency_mhz)}MHz",
                power=_get_default_power(band_config.frequency_mhz),
                gain=_get_default_gain(band_config.frequency_mhz),
            )
            site.antennas.append(antenna)
        else:
            # 定向天线（按扇区数均匀分布）
            for s in range(num_sectors):
                azimuth = (360.0 / num_sectors) * s
                antenna = Antenna(
                    antenna_type=_select_antenna_type(band_config.frequency_mhz),
                    azimuth=azimuth,
                    height=tower_height,
                    band=f"{int(band_config.frequency_mhz)}MHz",
                    power=_get_default_power(band_config.frequency_mhz),
                    gain=_get_default_gain(band_config.frequency_mhz),
                )
                site.antennas.append(antenna)

        sites.append(site)

    return sites


def _select_antenna_type(frequency_mhz: float) -> str:
    """根据频段选择天线型号"""
    if frequency_mhz >= 3000:
        return "AAU5313"
    elif frequency_mhz >= 2000:
        return "AAU5639"
    else:
        return "RRU5301"


def _get_default_power(frequency_mhz: float) -> float:
    """获取频段默认发射功率 (W)"""
    if frequency_mhz >= 3000:
        return 200.0
    elif frequency_mhz >= 2000:
        return 160.0
    else:
        return 120.0


def _get_default_gain(frequency_mhz: float) -> float:
    """获取频段默认天线增益 (dBi)"""
    if frequency_mhz >= 3000:
        return 24.0
    elif frequency_mhz >= 2000:
        return 22.0
    else:
        return 18.0
