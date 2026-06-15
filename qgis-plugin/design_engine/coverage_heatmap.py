"""
覆盖热力图生成模块

分为两层：
- 纯计算层：generate_coverage_heatmap_data / calculate_coverage_statistics（无qgis依赖，可测试）
- QGIS渲染层：create_coverage_heatmap_layer / style_coverage_heatmap（需要qgis环境）
"""

import math
from typing import List, Tuple, Dict


def generate_coverage_heatmap_data(
    site_lon: float,
    site_lat: float,
    tx_height_m: float,
    frequency_mhz: float,
    tx_power_w: float,
    antenna_gain_dbi: float,
    radius_km: float = 2.0,
    resolution_m: int = 100,
    rsrp_threshold_dbm: float = -110,
    environment: str = "URBAN"
) -> List[Dict]:
    """
    生成覆盖热力图数据

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
        热力图数据列表
    """
    from .coverage import okumura_hata_path_loss, calculate_rsrp, power_w_to_dbm

    tx_power_dbm = power_w_to_dbm(tx_power_w)

    # 经纬度到km的转换系数
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(site_lat)))
    lat_per_km = 1.0 / 111.0

    heatmap_data = []
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
                heatmap_data.append({
                    'longitude': site_lon + d_lon,
                    'latitude': site_lat + d_lat,
                    'rsrp': round(rsrp, 1),
                    'distance_km': round(d_km, 3),
                    'path_loss': round(path_loss, 2)
                })

    return heatmap_data


def create_coverage_heatmap_layer(
    heatmap_data: List[Dict],
    layer_name: str = "Coverage Heatmap"
):
    """
    创建覆盖热力图图层（需要qgis环境）

    Args:
        heatmap_data: 热力图数据
        layer_name: 图层名称

    Returns:
        QgsVectorLayer
    """
    from qgis.core import (
        QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
        QgsField,
    )
    from qgis.PyQt.QtCore import QVariant

    # 创建内存图层
    layer = QgsVectorLayer('Point?crs=EPSG:4326', layer_name, 'memory')
    provider = layer.dataProvider()

    # 添加字段
    provider.addAttributes([
        QgsField('longitude', QVariant.Double),
        QgsField('latitude', QVariant.Double),
        QgsField('rsrp', QVariant.Double),
        QgsField('distance_km', QVariant.Double),
        QgsField('path_loss', QVariant.Double)
    ])
    layer.updateFields()

    # 添加要素
    features = []
    for data in heatmap_data:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(
            QgsPointXY(data['longitude'], data['latitude'])
        ))
        feature.setAttributes([
            data['longitude'],
            data['latitude'],
            data['rsrp'],
            data['distance_km'],
            data['path_loss']
        ])
        features.append(feature)

    provider.addFeatures(features)
    layer.updateExtents()

    return layer


def style_coverage_heatmap(layer) -> None:
    """
    为覆盖热力图图层设置5级颜色渲染（需要qgis环境）

    Args:
        layer: QgsVectorLayer
    """
    from qgis.core import (
        QgsMarkerSymbol, QgsRendererRange, QgsGraduatedSymbolRenderer
    )

    # 定义RSRP等级和颜色
    ranges = [
        # 极好 (-50 to -65 dBm) - 深绿色
        QgsRendererRange(-50, -65, QgsMarkerSymbol.createSimple({
            'name': 'circle', 'color': '#006400', 'size': '2'
        }), 'Excellent (-50 to -65 dBm)'),

        # 好 (-65 to -80 dBm) - 绿色
        QgsRendererRange(-65, -80, QgsMarkerSymbol.createSimple({
            'name': 'circle', 'color': '#228B22', 'size': '2'
        }), 'Good (-65 to -80 dBm)'),

        # 一般 (-80 to -90 dBm) - 黄色
        QgsRendererRange(-80, -90, QgsMarkerSymbol.createSimple({
            'name': 'circle', 'color': '#FFD700', 'size': '2'
        }), 'Fair (-80 to -90 dBm)'),

        # 差 (-90 to -100 dBm) - 橙色
        QgsRendererRange(-90, -100, QgsMarkerSymbol.createSimple({
            'name': 'circle', 'color': '#FF8C00', 'size': '2'
        }), 'Poor (-90 to -100 dBm)'),

        # 很差 (-100 to -110 dBm) - 红色
        QgsRendererRange(-100, -110, QgsMarkerSymbol.createSimple({
            'name': 'circle', 'color': '#DC143C', 'size': '2'
        }), 'Very Poor (-100 to -110 dBm)'),
    ]

    # 创建分级符号渲染器
    renderer = QgsGraduatedSymbolRenderer()
    renderer.setClassAttribute('rsrp')
    for r in ranges:
        renderer.addClassRange(r)

    # 应用渲染器
    layer.setRenderer(renderer)
    layer.triggerRepaint()


def generate_multi_site_coverage(
    sites: List[Dict],
    frequency_mhz: float,
    tx_power_w: float,
    antenna_gain_dbi: float,
    radius_km: float = 2.0,
    resolution_m: int = 100,
    environment: str = "URBAN"
):
    """
    生成多站点覆盖热力图

    Args:
        sites: 站点列表 [{'lon': float, 'lat': float, 'height': float}, ...]
        frequency_mhz: 频率 (MHz)
        tx_power_w: 发射功率 (W)
        antenna_gain_dbi: 天线增益 (dBi)
        radius_km: 计算半径 (km)
        resolution_m: 栅格分辨率 (m)
        environment: 环境类型

    Returns:
        合并后的热力图图层
    """
    all_heatmap_data = []

    for site in sites:
        heatmap_data = generate_coverage_heatmap_data(
            site_lon=site['lon'],
            site_lat=site['lat'],
            tx_height_m=site.get('height', 45),
            frequency_mhz=frequency_mhz,
            tx_power_w=tx_power_w,
            antenna_gain_dbi=antenna_gain_dbi,
            radius_km=radius_km,
            resolution_m=resolution_m,
            environment=environment
        )
        all_heatmap_data.extend(heatmap_data)

    # 创建图层
    layer = create_coverage_heatmap_layer(all_heatmap_data, "Multi-Site Coverage")

    # 设置样式
    style_coverage_heatmap(layer)

    return layer


def calculate_coverage_statistics(heatmap_data: List[Dict]) -> Dict:
    """
    计算覆盖统计信息

    Args:
        heatmap_data: 热力图数据

    Returns:
        统计信息字典
    """
    if not heatmap_data:
        return {
            'total_points': 0,
            'avg_rsrp': 0,
            'min_rsrp': 0,
            'max_rsrp': 0,
            'coverage_rate': 0
        }

    rsrp_values = [data['rsrp'] for data in heatmap_data]

    return {
        'total_points': len(heatmap_data),
        'avg_rsrp': round(sum(rsrp_values) / len(rsrp_values), 1),
        'min_rsrp': min(rsrp_values),
        'max_rsrp': max(rsrp_values),
        'coverage_rate': round(len([r for r in rsrp_values if r >= -110]) / len(rsrp_values) * 100, 1)
    }
