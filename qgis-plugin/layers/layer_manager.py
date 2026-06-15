"""统一图层管理器 — 管理所有基站设计图层"""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="qgis")

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsField, QgsRendererCategory,
    QgsCategorizedSymbolRenderer, QgsMarkerSymbol,
)
from qgis.PyQt.QtCore import QVariant


LAYER_NAME = "基站设计"

FIELDS = [
    QgsField("siteId", QVariant.String),
    QgsField("name", QVariant.String),
    QgsField("siteType", QVariant.String),
    QgsField("towerHeight", QVariant.Double),
    QgsField("scenario", QVariant.String),
    QgsField("antennaCount", QVariant.Int),
]


class LayerManager:

    def __init__(self):
        self._layer = None

    def get_or_create_layer(self):
        if self._layer and self._layer.isValid():
            return self._layer

        for layer in QgsProject.instance().mapLayersByName(LAYER_NAME):
            self._layer = layer
            return layer

        self._layer = QgsVectorLayer("Point?crs=EPSG:4326", LAYER_NAME, "memory")
        self._layer.dataProvider().addAttributes(FIELDS)
        self._layer.updateFields()
        self._apply_style(self._layer)
        QgsProject.instance().addMapLayer(self._layer)
        return self._layer

    def add_sites(self, sites):
        layer = self.get_or_create_layer()
        layer.startEditing()
        for site in sites:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(site.longitude, site.latitude)))
            feat.setAttributes([
                site.site_id, site.name, site.site_type,
                site.tower_height, site.scenario, len(site.antennas),
            ])
            layer.addFeature(feat)
        layer.commitChanges()
        layer.updateExtents()
        layer.triggerRepaint()

    def replace_sites(self, sites):
        layer = self.get_or_create_layer()
        layer.startEditing()
        layer.deleteFeatures(layer.allFeatureIds())
        feats = []
        for site in sites:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(site.longitude, site.latitude)))
            feat.setAttributes([
                site.site_id, site.name, site.site_type,
                site.tower_height, site.scenario, len(site.antennas),
            ])
            feats.append(feat)
        layer.addFeatures(feats)
        layer.commitChanges()
        layer.updateExtents()
        layer.triggerRepaint()

    def clear(self):
        layer = self.get_or_create_layer()
        layer.startEditing()
        layer.deleteFeatures(layer.allFeatureIds())
        layer.commitChanges()
        layer.triggerRepaint()

    def _apply_style(self, layer):
        # 宏站 - 大红色圆点，带白色边框
        symbol_macro = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": "#ff0000", "size": "8",
            "outline_color": "white", "outline_width": "1"
        })
        # 微站 - 绿色圆点
        symbol_small = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": "#00ff00", "size": "6",
            "outline_color": "white", "outline_width": "0.5"
        })
        # 室内站 - 黄色圆点
        symbol_indoor = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": "#ffff00", "size": "5",
            "outline_color": "white", "outline_width": "0.5"
        })
        # 默认/手动添加 - 红色星形，更大
        symbol_manual = QgsMarkerSymbol.createSimple({
            "name": "star", "color": "#ff0000", "size": "10",
            "outline_color": "white", "outline_width": "1"
        })

        categories = [
            QgsRendererCategory("MACRO", symbol_macro, "宏站"),
            QgsRendererCategory("SMALL", symbol_small, "微站"),
            QgsRendererCategory("INDOOR", symbol_indoor, "室内站"),
        ]
        renderer = QgsCategorizedSymbolRenderer("siteType", categories)
        renderer.setSourceSymbolManual(symbol_manual)  # 默认符号
        layer.setRenderer(renderer)
