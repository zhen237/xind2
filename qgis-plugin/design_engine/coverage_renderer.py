"""GDAL 栅格热力图渲染器

生成专业外观的 GeoTIFF 格式覆盖热力图，替代原来的点状分级符号渲染。
QGIS 渲染为平滑渐变热力图效果。
"""

import math
import numpy as np
from typing import List, Dict, Optional, Tuple

from ..utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)


def generate_raster_heatmap_data(
    sites: List[Dict],
    frequency_mhz: float,
    tx_power_w: float,
    antenna_gain_dbi: float,
    resolution_m: int = 50,
    radius_km: float = 3.0,
    environment: str = "URBAN",
) -> Tuple[np.ndarray, Dict]:
    """
    生成 GDAL 兼容的热力图栅格数据。

    Args:
        sites: 站点列表，每项包含 lon, lat, height, tower_height
        frequency_mhz: 频率 (MHz)
        tx_power_w: 发射功率 (W)
        antenna_gain_dbi: 天线增益 (dBi)
        resolution_m: 栅格分辨率 (米)
        radius_km: 计算半径 (km)
        environment: 环境类型 (URBAN/SUBURBAN/RURAL)

    Returns:
        (rsrp_array, transform_dict)
        - rsrp_array: numpy 2D 数组 (rows, cols)，值为 RSRP dBm
        - transform: GDAL GeoTransform 字典 [origin_x, pixel_w, 0, origin_y, 0, pixel_h]
    """
    from .coverage import okumura_hata_path_loss, power_w_to_dbm

    tx_power_dbm = power_w_to_dbm(tx_power_w)
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(35.0)))  # 近似中纬
    lat_per_km = 1.0 / 111.0

    # 计算每个站点的 bounding box
    cols_km = int(radius_km * 1000 / resolution_m)
    rows_km = cols_km

    if not sites:
        return np.array([]), {}

    # 取第一个站点的中心
    center_lon = sites[0].get('longitude', sites[0].get('lon', 110.95))
    center_lat = sites[0].get('latitude', sites[0].get('lat', 35.0))

    # 扩展 bbox 覆盖所有站点
    for s in sites[1:]:
        slon = s.get('longitude', s.get('lon', center_lon))
        slat = s.get('latitude', s.get('lat', center_lat))
        center_lon = min(center_lon, slon)
        center_lat = min(center_lat, slat)

    # 重新计算 bbox 覆盖所有站点
    min_lon = center_lon
    min_lat = center_lat
    for s in sites:
        slon = s.get('longitude', s.get('lon', center_lon))
        slat = s.get('latitude', s.get('lat', center_lat))
        min_lon = min(min_lon, slon)
        min_lat = min(min_lat, slat)

    # 扩大 radius_km
    max_lon = max(s.get('longitude', s.get('lon', 0)) for s in sites) + radius_km * lon_per_km
    max_lat = max(s.get('latitude', s.get('lat', 0)) for s in sites) + radius_km * lat_per_km
    min_lon = min(s.get('longitude', s.get('lon', 0)) for s in sites) - radius_km * lon_per_km
    min_lat = min(s.get('latitude', s.get('lat', 0)) for s in sites) - radius_km * lat_per_km

    width_km = (max_lon - min_lon) / lon_per_km
    height_km = (max_lat - min_lat) / lat_per_km
    cols = int(width_km * 1000 / resolution_m) + 1
    rows = int(height_km * 1000 / resolution_m) + 1

    # 初始化 RSRP 数组为极低值
    rsrp_grid = np.full((rows, cols), -999.0, dtype=np.float32)

    # 逐站点叠加 RSRP
    for site in sites:
        slon = site.get('longitude', site.get('lon', center_lon))
        slat = site.get('latitude', site.get('lat', center_lat))
        height = site.get('tower_height', site.get('height', 35))
        beamwidth = site.get('beamwidth_h', 65.0)
        num_sectors = site.get('num_sectors', 3)

        for sector in range(num_sectors):
            if num_sectors > 0:
                azimuth = (360.0 / num_sectors) * sector
            else:
                azimuth = 0
                beamwidth = 360.0

            for row in range(rows):
                lat = min_lat + row * resolution_m / 111000
                for col in range(cols):
                    lon = min_lon + col * resolution_m / (111000 * math.cos(math.radians(slat)))
                    d_km = math.sqrt(
                        ((lon - slon) / lon_per_km) ** 2 + ((lat - slat) / lat_per_km) ** 2
                    )

                    if d_km < 0.01 or d_km > radius_km:
                        continue

                    # 相对角度
                    dx = (lon - slon) * 111 * math.cos(math.radians(slat))
                    dy = lat - slat
                    rx_angle = math.degrees(math.atan2(dx, dy)) % 360
                    angle_diff = abs(((rx_angle - azimuth) + 180) % 360 - 180)
                    half_bw = beamwidth / 2.0

                    if angle_diff <= half_bw:
                        directivity_corr = 3.0
                    elif angle_diff <= half_bw + 15.0:
                        t = (angle_diff - half_bw) / 15.0
                        directivity_corr = 3.0 + 12.0 * t
                    else:
                        directivity_corr = 15.0

                    path_loss = okumura_hata_path_loss(
                        frequency_mhz, max(d_km, 0.01), height,
                        environment=environment
                    )
                    rsrp = tx_power_dbm + antenna_gain_dbi - path_loss - 8.0 + directivity_corr

                    idx_r, idx_c = int((lat - min_lat) * 111000 / resolution_m), \
                                   int((lon - min_lon) * 111000 * math.cos(math.radians(slat)) / resolution_m)
                    if 0 <= idx_r < rows and 0 <= idx_c < cols:
                        rsrp_grid[idx_r, idx_c] = max(rsrp_grid[idx_r, idx_c], rsrp)

    transform = {
        'origin_x': min_lon,
        'origin_y': max_lat,
        'pixel_w': (max_lon - min_lon) / cols,
        'pixel_h': -(max_lat - min_lat) / rows,
    }

    return rsrp_grid, transform


def export_heatmap_as_geotiff(
    rsrp_grid: np.ndarray,
    transform: Dict,
    output_path: str,
    crs_epsg: int = 4326,
) -> bool:
    """
    将 RSRP 栅格导出为 GeoTIFF 文件。

    Args:
        rsrp_grid: numpy 2D 数组
        transform: GeoTransform 字典
        output_path: 输出路径
        crs_epsg: CRS EPSG 码

    Returns:
        是否成功
    """
    try:
        from osgeo import gdal, osr

        driver = gdal.GetDriverByName('GTiff')
        rows, cols = rsrp_grid.shape
        dataset = driver.Create(str(output_path), cols, rows, 1, gdal.GDT_Float32)

        # 写入 GeoTransform
        dataset.SetGeoTransform([
            transform['origin_x'],
            transform['pixel_w'],
            0,
            transform['origin_y'],
            0,
            transform['pixel_h'],
        ])

        # 写入 CRS
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(crs_epsg)
        dataset.SetProjection(srs.ExportToWkt())

        # 写入数据
        dataset.GetRasterBand(1).WriteArray(rsrp_grid)
        dataset.GetRasterBand(1).SetNoDataValue(-999.0)
        dataset.GetRasterBand(1).FlushCache()

        return True
    except ImportError:
        _logger.warning("GDAL not available, skipping GeoTIFF export")
        return False
    except Exception as e:
        _logger.error("GeoTIFF export failed: %s", e, exc_info=True)
        return False
