import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="qgis")


from typing import List, Optional

from models.site import Site


def create_site_layer(sites: List[Site], layer_name: str = "设计方案站点"):
    """
    在QGIS中创建站点图层。

    Args:
        sites: 站点列表
        layer_name: 图层名称

    Returns:
        QgsVectorLayer 或 None（非QGIS环境）
    """
    try:
        from qgis.core import (
            QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
            QgsPointXY, QgsField, QgsSymbol, QgsRendererCategory,
            QgsCategorizedSymbolRenderer, QgsMarkerSymbol,
        )
        from PyQt5.QtCore import QVariant
        from PyQt5.QtGui import QColor

        # 创建内存图层
        layer = QgsVectorLayer("Point?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()

        # 添加字段
        provider.addAttributes([
            QgsField("siteId", QVariant.String),
            QgsField("name", QVariant.String),
            QgsField("siteType", QVariant.String),
            QgsField("towerType", QVariant.String),
            QgsField("towerHeight", QVariant.Double),
            QgsField("scenario", QVariant.String),
            QgsField("antennaCount", QVariant.Int),
            QgsField("longitude", QVariant.Double),
            QgsField("latitude", QVariant.Double),
        ])
        layer.updateFields()

        # 添加要素
        features = []
        for site in sites:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(
                QgsPointXY(site.longitude, site.latitude)
            ))
            feat.setAttributes([
                site.site_id,
                site.name,
                site.site_type,
                site.tower_type,
                site.tower_height,
                site.scenario,
                len(site.antennas),
                site.longitude,
                site.latitude,
            ])
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()

        # 设置样式
        _apply_site_style(layer)

        # 添加到项目
        QgsProject.instance().addMapLayer(layer)
        return layer

    except ImportError:
        print("[INFO] 非QGIS环境，跳过图层创建")
        return None


def _apply_site_style(layer):
    """应用站点样式"""
    try:
        from qgis.core import (
            QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
            QgsMarkerSymbol,
        )
        from PyQt5.QtGui import QColor

        # 宏站 - 蓝色大圆
        symbol_macro = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": "#1890ff", "size": "6",
            "outline_color": "#ffffff", "outline_width": "0.5"
        })
        # 微站 - 绿色中圆
        symbol_small = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": "#52c41a", "size": "4",
            "outline_color": "#ffffff", "outline_width": "0.5"
        })
        # 室内站 - 黄色小圆
        symbol_indoor = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": "#faad14", "size": "3",
            "outline_color": "#ffffff", "outline_width": "0.5"
        })

        categories = [
            QgsRendererCategory("MACRO", symbol_macro, "宏站"),
            QgsRendererCategory("SMALL", symbol_small, "微站"),
            QgsRendererCategory("INDOOR", symbol_indoor, "室内站"),
        ]
        renderer = QgsCategorizedSymbolRenderer("siteType", categories)
        layer.setRenderer(renderer)

    except Exception as e:
        print(f"[WARN] 样式应用失败: {e}")


def update_site_layer(layer, sites: List[Site]):
    """
    更新已有站点图层的数据。

    Args:
        layer: QgsVectorLayer
        sites: 新的站点列表
    """
    try:
        from qgis.core import QgsFeature, QgsGeometry, QgsPointXY
        from PyQt5.QtCore import QVariant

        layer.startEditing()
        layer.deleteFeatures([f.id() for f in layer.getFeatures()])

        features = []
        for site in sites:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(
                QgsPointXY(site.longitude, site.latitude)
            ))
            feat.setAttributes([
                site.site_id, site.name, site.site_type, site.tower_type,
                site.tower_height, site.scenario, len(site.antennas),
                site.longitude, site.latitude,
            ])
            features.append(feat)

        layer.addFeatures(features)
        layer.commitChanges()
        layer.updateExtents()

    except Exception as e:
        print(f"[ERROR] 图层更新失败: {e}")
        layer.rollbackChanges()
