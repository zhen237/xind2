# -*- coding: utf-8 -*-
"""管线图层管理"""

from typing import List, Dict, Optional
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsField, QgsPointXY, QgsLineSymbol, QgsMarkerSymbol,
    QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
    QgsRendererCategory, QgsSymbolLayerUtils,
    QgsMarkerLineSymbolLayer, QgsSimpleLineSymbolLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

# 尝试相对导入，如果失败则使用绝对导入
try:
    from ..models.pipeline import Pipeline, PipelineType, PipelineConfig
except ImportError:
    from models.pipeline import Pipeline, PipelineType, PipelineConfig


def create_pipeline_layer(
    pipelines: List[Pipeline],
    layer_name: str = "通信管线"
) -> QgsVectorLayer:
    """
    创建管线图层

    Args:
        pipelines: 管线列表
        layer_name: 图层名称

    Returns:
        QgsVectorLayer
    """
    # 移除旧图层
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if layers:
        QgsProject.instance().removeMapLayer(layers[0])

    # 创建线图层
    layer = QgsVectorLayer("LineString?crs=EPSG:4326", layer_name, "memory")
    provider = layer.dataProvider()

    # 添加字段
    provider.addAttributes([
        QgsField("pipeline_id", QVariant.String),
        QgsField("start_site_id", QVariant.String),
        QgsField("end_site_id", QVariant.String),
        QgsField("pipeline_type", QVariant.String),
        QgsField("length_m", QVariant.Double),
        QgsField("depth_m", QVariant.Double),
        QgsField("diameter_mm", QVariant.Int),
        QgsField("material", QVariant.String),
        QgsField("capacity", QVariant.Int),
        QgsField("status", QVariant.String),
    ])
    layer.updateFields()

    # 添加要素
    features = []
    for pipeline in pipelines:
        if len(pipeline.coordinates) < 2:
            continue

        feat = QgsFeature(layer.fields())

        # 创建线几何
        points = [QgsPointXY(lon, lat) for lon, lat in pipeline.coordinates]
        feat.setGeometry(QgsGeometry.fromPolylineXY(points))

        # 设置属性
        feat.setAttributes([
            pipeline.pipeline_id,
            pipeline.start_site_id,
            pipeline.end_site_id,
            pipeline.pipeline_type.value,
            pipeline.length_m,
            pipeline.depth_m,
            pipeline.diameter_mm,
            pipeline.material,
            pipeline.capacity,
            pipeline.status,
        ])
        features.append(feat)

    provider.addFeatures(features)
    layer.updateExtents()

    # 设置样式
    style_pipeline_layer(layer)

    # 添加图层到项目
    QgsProject.instance().addMapLayer(layer)

    return layer


def style_pipeline_layer(layer: QgsVectorLayer) -> None:
    """
    设置管线图层样式

    Args:
        layer: 管线图层
    """
    # 创建分类渲染器
    renderer = QgsCategorizedSymbolRenderer("pipeline_type")
    renderer.setClassAttribute("pipeline_type")

    # 为每种管线类型创建样式
    for pipeline_type, config in PipelineConfig.type_configs.items():
        # 创建线符号
        symbol = QgsLineSymbol.createSimple({
            'color': config['color'],
            'width': '2.5',
            'line_style': config['line_style'],
        })

        # 设置透明度
        symbol.setOpacity(0.85)

        # 创建分类
        category = QgsRendererCategory(
            pipeline_type.value,  # 值
            symbol,               # 符号
            config['name'],       # 标签
        )
        renderer.addCategory(category)

    # 设置默认符号
    default_symbol = QgsLineSymbol.createSimple({
        'color': 'gray',
        'width': '1.5',
        'line_style': 'solid',
    })
    default_symbol.setOpacity(0.5)
    renderer.setSourceSymbol(default_symbol)

    # 应用渲染器
    layer.setRenderer(renderer)

    # 启用原生标注
    enable_pipeline_labels(layer)


def enable_pipeline_labels(layer: QgsVectorLayer) -> None:
    """
    启用管线原生标注（编号+长度+类型）

    Args:
        layer: 管线图层
    """
    from qgis.core import QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
    from qgis.utils import iface

    # 组合标注表达式: PL-0001 | 12.5m | 直埋
    label_expression = '"pipeline_id" || \' | \' || round("length_m", 1) || \'m\' || \' | \' || "pipeline_type"'

    settings = QgsPalLayerSettings()
    settings.fieldName = label_expression
    settings.enabled = True
    settings.isExpression = True  # 使用表达式

    # 文字样式
    text_format = QgsTextFormat()
    font = QFont()
    font.setPointSize(8)
    font.setBold(True)
    text_format.setFont(font)
    text_format.setColor(QColor(30, 30, 30))
    text_format.setSize(8)

    # 白色背景缓冲
    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1.5)
    buffer_settings.setColor(QColor(255, 255, 255, 200))
    text_format.setBuffer(buffer_settings)

    settings.setFormat(text_format)

    # 标注位置：沿线居中
    settings.placement = QgsPalLayerSettings.Curved
    settings.dist = 3

    # 禁用"仅显示放大到一定比例时"限制
    settings.preserveGeometry = True

    labeling = QgsVectorLayerSimpleLabeling(settings)
    layer.setLabeling(labeling)
    layer.setLabelsEnabled(True)


def create_connection_layer(
    sites: List[Dict],
    pipelines: List[Pipeline],
    layer_name: str = "基站-管线关联"
) -> QgsVectorLayer:
    """
    创建基站到管线起点的关联线图层（虚线）

    Args:
        sites: 基站列表 [{'site_id': str, 'longitude': float, 'latitude': float, ...}]
        pipelines: 管线列表
        layer_name: 图层名称

    Returns:
        QgsVectorLayer
    """
    # 移除旧图层
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if layers:
        QgsProject.instance().removeMapLayer(layers[0])

    # 创建点->点线图层
    layer = QgsVectorLayer("LineString?crs=EPSG:4326", layer_name, "memory")
    provider = layer.dataProvider()

    provider.addAttributes([
        QgsField("site_id", QVariant.String),
        QgsField("pipeline_id", QVariant.String),
    ])
    layer.updateFields()

    features = []
    # 构建 site_id -> pipeline 映射（取第一条）
    site_to_pipeline = {}
    for p in pipelines:
        if p.start_site_id not in site_to_pipeline:
            site_to_pipeline[p.start_site_id] = p

    for site in sites:
        site_id = site.get('site_id', '')
        if site_id in site_to_pipeline:
            pipeline = site_to_pipeline[site_id]
            if len(pipeline.coordinates) >= 2:
                # 关联线: 基站 -> 管线起点
                points = [
                    QgsPointXY(site['longitude'], site['latitude']),
                    QgsPointXY(pipeline.coordinates[0][0], pipeline.coordinates[0][1]),
                ]
                feat = QgsFeature(layer.fields())
                feat.setGeometry(QgsGeometry.fromPolylineXY(points))
                feat.setAttributes([site_id, pipeline.pipeline_id])
                features.append(feat)

    if features:
        provider.addFeatures(features)
        layer.updateExtents()

        # 样式：灰色虚线
        symbol = QgsLineSymbol.createSimple({
            'color': '120, 120, 120',
            'width': '1.2',
            'line_style': 'dash',
            'dash_pattern': '2 3',
        })
        symbol.setOpacity(0.5)

        # 末端箭头标记线
        arrow_sym = QgsMarkerSymbol.createSimple({
            'name': 'arrow',
            'color': '120, 120, 120',
            'size': '4',
        })
        marker_line_layer = QgsMarkerLineSymbolLayer(arrow_sym)
        marker_line_layer.setPlacement(QgsMarkerLineSymbolLayer.LastPoint)

        # 使用标记线在末端加箭头
        symbols = layer.renderer().symbols()
        if symbols:
            for sym in symbols:
                sym.setStyleLayer(marker_line_layer)

        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        QgsProject.instance().addMapLayer(layer)

    return layer


def get_pipeline_info(pipeline: Pipeline) -> str:
    """
    获取管线信息文本

    Args:
        pipeline: 管线对象

    Returns:
        信息文本
    """
    info = f"管线编号: {pipeline.pipeline_id}\n"
    info += f"类型: {pipeline.pipeline_type.value}\n"
    info += f"长度: {pipeline.length_m:.2f} m\n"
    info += f"管径: {pipeline.diameter_mm} mm\n"
    info += f"材质: {pipeline.material}\n"
    info += f"容量: {pipeline.capacity} 孔\n"
    info += f"埋深: {pipeline.depth_m:.2f} m\n"

    # 工程量
    if pipeline.engineering_volume:
        info += "\n工程量:\n"
        for key, value in pipeline.engineering_volume.items():
            info += f"  {key}: {value}\n"

    return info


def export_pipelines_to_geojson(
    pipelines: List[Pipeline],
    output_path: str
) -> bool:
    """
    导出管线为GeoJSON

    Args:
        pipelines: 管线列表
        output_path: 输出路径

    Returns:
        是否成功
    """
    import json

    features = []
    for pipeline in pipelines:
        if len(pipeline.coordinates) < 2:
            continue

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": pipeline.coordinates
            },
            "properties": pipeline.to_dict()
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"导出失败: {e}")
        return False
