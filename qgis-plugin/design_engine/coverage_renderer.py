"""专业级覆盖渲染器 — 基于GDAL栅格的连续热力图

替代原始的逐点画圆方案，使用栅格聚合+伪彩色渲染，
达到 Atoll/Planet 等专业电信软件级别的视觉效果。
"""
import math
import numpy as np
from typing import List, Dict, Tuple

# RSRP标准分级颜色表（符合3GPP/ITU-R建议）
# 从左到右：RSRP阈值(dBm) → RGB颜色
RSRP_COLOR_STOPS = [
    (-50, (0, 0, 255)),     # 深蓝: 极强
    (-65, (0, 191, 255)),   # 浅蓝: 极好
    (-80, (0, 255, 0)),     # 绿: 良好
    (-90, (255, 255, 0)),   # 黄: 一般
    (-100, (255, 165, 0)),  # 橙: 较差
    (-110, (255, 0, 0)),    # 红: 弱覆盖
    (-120, (128, 0, 128)),  # 紫: 盲区
]


def generate_coverage_grid(
    all_data: List[Dict],
    bbox: Tuple[float, float, float, float],
    resolution_m: int = 30,
) -> Tuple[np.ndarray, Tuple[float, float, float, float, float, float]]:
    """
    将离散覆盖点聚合为规则栅格，每个单元格取最强RSRP值。

    Args:
        all_data: 覆盖点列表 [{'longitude': float, 'latitude': float, 'rsrp': float}, ...]
        bbox: (lon_min, lat_min, lon_max, lat_max)
        resolution_m: 栅格分辨率（米），越小越精细

    Returns:
        (raster_array, geotransform)
        - raster_array: shape=(rows, cols), dtype=float32, 值=RSRP(dBm)，无覆盖区域=-200.0
        - geotransform: GDAL-compatible GeoTransform tuple
    """
    lon_min, lat_min, lon_max, lat_max = bbox

    # 经纬度到米的转换系数（中纬度近似）
    mid_lat = (lat_min + lat_max) / 2
    lon_per_deg = 111.0 * math.cos(math.radians(mid_lat))
    lat_per_deg = 111.0

    # 计算栅格行列数
    width_m = (lon_max - lon_min) * lon_per_deg
    height_m = (lat_max - lat_min) * lat_per_deg
    width_px = max(10, int(width_m / resolution_m))
    height_px = max(10, int(height_m / resolution_m))

    # 初始化为极小值（表示无覆盖）
    grid = np.full((height_px, width_px), -200.0, dtype=np.float32)

    dx = (lon_max - lon_min) / width_px
    dy = (lat_max - lat_min) / height_px

    # 将每个覆盖点映射到栅格单元格，取最强信号
    for pt in all_data:
        col = int((pt['longitude'] - lon_min) / dx)
        row = int((lat_max - pt['latitude']) / dy)
        col = max(0, min(width_px - 1, col))
        row = max(0, min(height_px - 1, row))
        if pt['rsrp'] > grid[row, col]:
            grid[row, col] = pt['rsrp']

    geotransform = (lon_min, dx, 0, lat_max, 0, -dy)
    return grid, geotransform


def rsrp_to_rgba(rsrp: float) -> Tuple[int, int, int, int]:
    """双线性插值RSRP到RGBA颜色"""
    if rsrp >= RSRP_COLOR_STOPS[0][0]:
        return RSRP_COLOR_STOPS[0][1]
    if rsrp <= RSRP_COLOR_STOPS[-1][0]:
        return RSRP_COLOR_STOPS[-1][1]

    for i in range(len(RSRP_COLOR_STOPS) - 1):
        lo_val, lo_rgb = RSRP_COLOR_STOPS[i]
        hi_val, hi_rgb = RSRP_COLOR_STOPS[i + 1]
        if lo_val >= rsrp > hi_val:
            t = (rsrp - hi_val) / (lo_val - hi_val)
            r = int(lo_rgb[0] * t + hi_rgb[0] * (1 - t))
            g = int(lo_rgb[1] * t + hi_rgb[1] * (1 - t))
            b = int(lo_rgb[2] * t + hi_rgb[2] * (1 - t))
            a = int(140 + 80 * t)
            return (r, g, b, a)
    return (255, 0, 0, 120)


def rsrp_to_qgis_color(rsrp: float) -> str:
    """将RSRP值转为QGIS颜色字符串 'R,G,B,A'"""
    r, g, b, a = rsrp_to_rgba(rsrp)
    return f"{r},{g},{b},{a}"
