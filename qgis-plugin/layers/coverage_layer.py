import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="qgis")


import math
from typing import List, Tuple, Optional


def create_coverage_layer(
    raster_data: dict,
    layer_name: str = "覆盖热力图",
):
    """
    在QGIS中创建覆盖热力图图层。

    Args:
        raster_data: generate_coverage_raster() 的返回值
        layer_name: 图层名称

    Returns:
        QgsVectorLayer 或 None（非QGIS环境）
    """
    try:
        from qgis.core import (
            QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
            QgsPointXY, QgsField, QgsSymbol, QgsSingleSymbolRenderer,
            QgsMarkerSymbol,
        )
        from PyQt5.QtCore import QVariant
        from PyQt5.QtGui import QColor

        features_data = raster_data.get("features", [])
        if not features_data:
            return None

        # 创建点图层用于热力图
        layer = QgsVectorLayer("Point?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()

        provider.addAttributes([
            QgsField("rsrp", QVariant.Double),
            QgsField("distance_km", QVariant.Double),
        ])
        layer.updateFields()

        # 添加要素
        qgs_features = []
        for feat_data in features_data:
            coords = feat_data["geometry"]["coordinates"]
            props = feat_data["properties"]

            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(coords[0], coords[1])))
            feat.setAttributes([
                props.get("rsrp", 0),
                props.get("distance_km", 0),
            ])
            qgs_features.append(feat)

        provider.addFeatures(qgs_features)
        layer.updateExtents()

        # 使用简单符号（大量点时性能更好）
        symbol = QgsMarkerSymbol.createSimple({
            "name": "circle",
            "color": "0,0,0,0",  # 透明填充
            "size": "2",
            "outline_style": "no",
        })
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))

        # 设置为热力图渲染
        _apply_heatmap_renderer(layer)

        QgsProject.instance().addMapLayer(layer)
        return layer

    except ImportError:
        print("[INFO] 非QGIS环境，跳过覆盖图层创建")
        return None


def _apply_heatmap_renderer(layer):
    """应用热力图渲染器"""
    try:
        from qgis.core import (
            QgsHeatmapRenderer, QgsColorRampShader,
            QgsGradientColorRamp, QgsSymbol,
        )
        from PyQt5.QtGui import QColor

        # 创建颜色渐变
        color_ramp = QgsGradientColorRamp(
            QColor(255, 0, 0),    # 红色（弱信号）
            QColor(0, 255, 0),    # 绿色（强信号）
            False,  # 不反转
            [
                QgsGradientColorRamp.Stop(0.25, QColor(255, 255, 0)),  # 黄色
                QgsGradientColorRamp.Stop(0.5, QColor(0, 255, 0)),     # 绿色
                QgsGradientColorRamp.Stop(0.75, QColor(0, 128, 255)),  # 蓝色
            ]
        )

        heatmap_renderer = QgsHeatmapRenderer()
        heatmap_renderer.setWeightField("rsrp")
        heatmap_renderer.setColorRamp(color_ramp)
        heatmap_renderer.setRadius(20)

        layer.setRenderer(heatmap_renderer)

    except Exception as e:
        print(f"[WARN] 热力图渲染设置失败: {e}")


def create_coverage_contour_layer(
    site_lon: float,
    site_lat: float,
    frequency_mhz: float,
    tx_power_w: float,
    antenna_gain_dbi: float,
    tower_height: float,
    radius_km: float = 2.0,
    environment: str = "URBAN",
    layer_name: str = "覆盖范围圈",
):
    """
    创建覆盖范围等值线图层（同心圆）。

    Args:
        site_lon: 站点经度
        site_lat: 站点纬度
        frequency_mhz: 频率
        tx_power_w: 发射功率
        antenna_gain_dbi: 天线增益
        tower_height: 塔高
        radius_km: 最大半径
        environment: 环境类型
        layer_name: 图层名称

    Returns:
        QgsVectorLayer 或 None
    """
    try:
        from qgis.core import (
            QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
            QgsPointXY, QgsField, QgsSymbol, QgsSingleSymbolRenderer,
            QgsLineSymbol,
        )
        from PyQt5.QtCore import QVariant
        from design_engine.coverage import okumura_hata_path_loss, calculate_rsrp, power_w_to_dbm

        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()

        provider.addAttributes([
            QgsField("rsrp_threshold", QVariant.Double),
            QgsField("radius_m", QVariant.Double),
        ])
        layer.updateFields()

        # 计算不同RSRP阈值对应的覆盖半径
        tx_dbm = power_w_to_dbm(tx_power_w)
        thresholds = [-110, -100, -90, -80]  # dBm

        lon_per_km = 1.0 / (111.0 * math.cos(math.radians(site_lat)))
        lat_per_km = 1.0 / 111.0

        for threshold in thresholds:
            # 二分法找到对应的覆盖半径
            r_min, r_max = 0.01, radius_km
            for _ in range(20):
                r_mid = (r_min + r_max) / 2
                path_loss = okumura_hata_path_loss(frequency_mhz, r_mid, tower_height, environment=environment)
                rsrp = calculate_rsrp(tx_dbm, antenna_gain_dbi, path_loss)
                if rsrp >= threshold:
                    r_min = r_mid
                else:
                    r_max = r_mid

            radius_final = (r_min + r_max) / 2
            if radius_final < 0.01:
                continue

            # 创建圆形多边形
            points = []
            for angle in range(0, 361, 5):
                rad = math.radians(angle)
                dx = radius_final * math.cos(rad) * lon_per_km
                dy = radius_final * math.sin(rad) * lat_per_km
                points.append(QgsPointXY(site_lon + dx, site_lat + dy))

            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPolygonXY([points]))
            feat.setAttributes([threshold, radius_final * 1000])
            provider.addFeatures([feat])

        layer.updateExtents()

        # 设置样式 - 不同阈值不同颜色
        _apply_contour_style(layer)

        QgsProject.instance().addMapLayer(layer)
        return layer

    except ImportError:
        print("[INFO] 非QGIS环境，跳过覆盖圈创建")
        return None


def _apply_contour_style(layer):
    """应用等值线样式"""
    try:
        from qgis.core import (
            QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
            QgsLineSymbol, QgsSimpleLineSymbolLayer,
        )
        from PyQt5.QtGui import QColor

        colors = {
            -110: QColor(255, 0, 0, 80),    # 红色 - 边缘覆盖
            -100: QColor(255, 165, 0, 80),   # 橙色
            -90: QColor(255, 255, 0, 80),     # 黄色
            -80: QColor(0, 255, 0, 80),       # 绿色 - 良好覆盖
        }

        categories = []
        for threshold, color in colors.items():
            symbol = QgsLineSymbol.createSimple({"color": color.name(), "width": "1.5"})
            symbol.setOpacity(0.5)
            categories.append(QgsRendererCategory(str(threshold), symbol, f"{threshold} dBm"))

        renderer = QgsCategorizedSymbolRenderer("rsrp_threshold", categories)
        layer.setRenderer(renderer)

    except Exception as e:
        print(f"[WARN] 等值线样式应用失败: {e}")
