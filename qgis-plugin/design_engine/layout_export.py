"""
标准图纸导出模块
用于生成标准设计图纸并导出为PDF/PNG格式
"""

import os
from typing import List, Dict, Optional
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap,
    QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutExporter, QgsLayoutSize, QgsLayoutPoint,
    QgsUnitTypes, QgsMapSettings, QgsRectangle, QgsLayerTreeLayer,
    QgsVectorLayer, QgsFillSymbol, QgsGeometry
)
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import QSizeF, QPointF

from ..utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)


def create_design_layout(
    project: QgsProject,
    layout_name: str = "通信基站设计方案",
    paper_size: str = "A3"
) -> QgsPrintLayout:
    """
    创建标准设计图纸布局

    Args:
        project: QGIS项目
        layout_name: 布局名称
        paper_size: 纸张大小 (A3/A4)

    Returns:
        打印布局对象
    """
    # 创建打印布局
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()

    # 设置纸张大小
    if paper_size == "A3":
        width = 420  # mm
        height = 297  # mm
    else:  # A4
        width = 297  # mm
        height = 210  # mm

    # 通过 pageCollection().pages()[0] 设置纸张大小
    try:
        size = QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters)
        layout.pageCollection().pages()[0].setPageSize(size)
    except (IndexError, AttributeError):
        layout.setPaperSize(width, height, QgsUnitTypes.LayoutMillimeters)

    return layout


def add_map_to_layout(
    layout: QgsPrintLayout,
    map_extent: QgsRectangle,
    map_position: QPointF = QPointF(20, 60),
    map_size: QSizeF = QSizeF(350, 200)
) -> QgsLayoutItemMap:
    """
    添加地图到布局 — BUG6修复: 确保只包含可见图层并正确设置范围

    Args:
        layout: 打印布局
        map_extent: 地图范围
        map_position: 地图位置 (mm)
        map_size: 地图大小 (mm)

    Returns:
        地图项
    """
    # 创建地图项
    map_item = QgsLayoutItemMap(layout)
    map_item.setRect(0, 0, map_size.width(), map_size.height())
    map_item.attemptMove(QgsLayoutPoint(map_position.x(), map_position.y(), QgsUnitTypes.LayoutMillimeters))
    map_item.attemptResize(QgsLayoutSize(map_size.width(), map_size.height(), QgsUnitTypes.LayoutMillimeters))

    # BUG6修复: 设置地图范围
    map_item.setExtent(map_extent)

    # BUG6修复: 关联当前项目的可见图层（仅可见 + 有效的图层）
    project = layout.project()
    if project:
        # 关键修复: 获取所有可见且有效的图层
        visible_layers = [
            layer for layer in project.mapLayers().values()
            if layer.isValid() and layer.isSpatial()
        ]
        if visible_layers:
            map_item.setLayers(visible_layers)

    # BUG6修复: 保持图层锁定，强制地图项预渲染
    map_item.setKeepLayerSet(True)

    # 添加到布局
    layout.addLayoutItem(map_item)

    # BUG6修复: 关键 — 在添加后立即刷新地图项，确保渲染缓存完成
    map_item.refresh()

    return map_item


def add_title_to_layout(
    layout: QgsPrintLayout,
    title: str,
    position: QPointF = QPointF(20, 10),
    font_size: int = 18
) -> QgsLayoutItemLabel:
    """
    添加标题到布局

    Args:
        layout: 打印布局
        title: 标题文本
        position: 位置 (mm)
        font_size: 字体大小

    Returns:
        标题项
    """
    # 创建标题项
    title_item = QgsLayoutItemLabel(layout)
    title_item.setText(title)
    title_item.setFont(QFont('Arial', font_size, QFont.Bold))
    title_item.attemptMove(QgsLayoutPoint(position.x(), position.y(), QgsUnitTypes.LayoutMillimeters))

    # 添加到布局
    layout.addLayoutItem(title_item)

    return title_item


def add_info_box_to_layout(
    layout: QgsPrintLayout,
    info_text: str,
    position: QPointF = QPointF(20, 30),
    size: QSizeF = QSizeF(350, 25)
) -> QgsLayoutItemLabel:
    """
    添加信息框到布局

    Args:
        layout: 打印布局
        info_text: 信息文本
        position: 位置 (mm)
        size: 大小 (mm)

    Returns:
        信息框项
    """
    # 创建信息框项
    info_item = QgsLayoutItemLabel(layout)
    info_item.setText(info_text)
    info_item.setFont(QFont('Arial', 10))
    info_item.attemptMove(QgsLayoutPoint(position.x(), position.y(), QgsUnitTypes.LayoutMillimeters))
    info_item.attemptResize(QgsLayoutSize(size.width(), size.height(), QgsUnitTypes.LayoutMillimeters))

    # 添加到布局
    layout.addLayoutItem(info_item)

    return info_item


def add_legend_to_layout(
    layout: QgsPrintLayout,
    map_item: QgsLayoutItemMap,
    position: QPointF = QPointF(380, 60),
    size: QSizeF = QSizeF(30, 100)
) -> QgsLayoutItemLegend:
    """
    添加图例到布局

    Args:
        layout: 打印布局
        map_item: 关联的地图项
        position: 位置 (mm)
        size: 大小 (mm)

    Returns:
        图例项
    """
    # 创建图例项
    legend_item = QgsLayoutItemLegend(layout)
    legend_item.setLinkedMap(map_item)
    legend_item.attemptMove(QgsLayoutPoint(position.x(), position.y(), QgsUnitTypes.LayoutMillimeters))
    legend_item.attemptResize(QgsLayoutSize(size.width(), size.height(), QgsUnitTypes.LayoutMillimeters))

    # 添加到布局
    layout.addLayoutItem(legend_item)

    return legend_item


def add_scale_bar_to_layout(
    layout: QgsPrintLayout,
    map_item: QgsLayoutItemMap,
    position: QPointF = QPointF(20, 270)
) -> QgsLayoutItemScaleBar:
    """
    添加比例尺到布局

    Args:
        layout: 打印布局
        map_item: 关联的地图项
        position: 位置 (mm)

    Returns:
        比例尺项
    """
    # 创建比例尺项
    scalebar_item = QgsLayoutItemScaleBar(layout)
    scalebar_item.setLinkedMap(map_item)
    scalebar_item.applyDefaultSize()
    scalebar_item.attemptMove(QgsLayoutPoint(position.x(), position.y(), QgsUnitTypes.LayoutMillimeters))

    # 添加到布局
    layout.addLayoutItem(scalebar_item)

    return scalebar_item


def add_north_arrow_to_layout(
    layout: QgsPrintLayout,
    position: QPointF = QPointF(380, 20),
    size: QSizeF = QSizeF(20, 20)
) -> QgsLayoutItemPicture:
    """
    添加指北针到布局

    Args:
        layout: 打印布局
        position: 位置 (mm)
        size: 大小 (mm)

    Returns:
        指北针项
    """
    # 创建指北针项
    north_item = QgsLayoutItemPicture(layout)
    north_item.setPicturePath(":/images/north_arrows/default.svg")
    north_item.attemptMove(QgsLayoutPoint(position.x(), position.y(), QgsUnitTypes.LayoutMillimeters))
    north_item.attemptResize(QgsLayoutSize(size.width(), size.height(), QgsUnitTypes.LayoutMillimeters))

    # 添加到布局
    layout.addLayoutItem(north_item)

    return north_item


def export_layout_to_pdf(
    layout: QgsPrintLayout,
    output_path: str,
    dpi: int = 300
) -> tuple:
    """
    导出布局为PDF

    Args:
        layout: 打印布局
        output_path: 输出路径
        dpi: 分辨率

    Returns:
        (是否成功, 错误信息)
    """
    try:
        # 确保输出路径是绝对路径
        output_path = os.path.abspath(output_path)

        # 检查输出目录是否存在
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            return False, f"输出目录不存在: {output_dir}"

        exporter = QgsLayoutExporter(layout)

        # 创建PDF导出设置
        settings = QgsLayoutExporter.PdfExportSettings()
        settings.dpi = dpi

        # 导出PDF
        result = exporter.exportToPdf(output_path, settings)

        if result == QgsLayoutExporter.Success:
            return True, ""
        else:
            return False, f"导出失败，错误代码: {result}\n输出路径: {output_path}"

    except Exception as e:
        return False, str(e)


def export_layout_to_png(
    layout: QgsPrintLayout,
    output_path: str,
    dpi: int = 300
) -> bool:
    """
    导出布局为PNG

    Args:
        layout: 打印布局
        output_path: 输出路径
        dpi: 分辨率

    Returns:
        是否成功
    """
    try:
        exporter = QgsLayoutExporter(layout)
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.dpi = dpi

        result = exporter.exportToImage(output_path, settings)

        if result == QgsLayoutExporter.Success:
            return True
        else:
            return False

    except Exception as e:
        _logger.error("Export failed: %s", e, exc_info=True)
        return False


def create_standard_design_drawing(
    project: QgsProject,
    sites: List[Dict],
    map_extent: QgsRectangle,
    title: str = "通信基站设计方案",
    output_path: str = None,
    paper_size: str = "A3",
    export_format: str = "PDF",
    scheme_params: Optional[Dict] = None
) -> Optional[str]:
    """
    创建标准设计图纸 — BUG6修复: 确保导出前所有地图元素正确渲染

    Args:
        project: QGIS项目
        sites: 站点列表
        map_extent: 地图范围
        title: 图纸标题
        output_path: 输出路径
        paper_size: 纸张大小
        export_format: 导出格式 (PDF/PNG)

    Returns:
        输出文件路径，失败返回None
    """
    try:
        # BUG6修复: 导出前强制所有目标图层可见
        target_layer_names = ["基站设计", "通信管线-直连", "通信管线-曼哈顿",
                              "基站-管线关联-直连", "基站-管线关联-曼哈顿",
                              "覆盖热力图"]
        for name in target_layer_names:
            for layer in QgsProject.instance().mapLayersByName(name):
                layer.setVisible(True)

        # 创建布局
        layout = create_design_layout(project, title, paper_size)

        # 添加标题
        add_title_to_layout(layout, title)

        # 添加信息框 — 中文本地化
        params_str = ""
        if scheme_params:
            freq = scheme_params.get('frequency_band', '3.5GHz')
            scenario = scheme_params.get('scenario', 'URBAN')
            tower_h = scheme_params.get('tower_height', 35)
            band = scheme_params.get('band', '700MHz')
            params_str = f" | 频段: {band} | 场景: {scenario} | 塔高: {tower_h}m"
        
        info_text = f"站点数: {len(sites)} | 纸张: {paper_size} | 坐标系: EPSG:4326{params_str}"
        add_info_box_to_layout(layout, info_text)

        # 添加地图
        map_item = add_map_to_layout(layout, map_extent)

        # 添加图例
        add_legend_to_layout(layout, map_item)

        # 添加比例尺
        add_scale_bar_to_layout(layout, map_item)

        # 添加指北针
        add_north_arrow_to_layout(layout)

        # BUG6修复: 关键 — 导出前强制布局刷新，确保地图项完成渲染
        layout.refresh()

        # 导出
        if output_path is None:
            output_path = os.path.join(os.path.expanduser('~'), 'Desktop', f'{title}.{export_format.lower()}')

        if export_format.upper() == "PDF":
            ok, err = export_layout_to_pdf(layout, output_path)
            success = ok
        else:  # PNG
            success = export_layout_to_png(layout, output_path)

        if success:
            return output_path
        else:
            return None

    except Exception as e:
        _logger.error("Failed to create design drawing: %s", e, exc_info=True)
        return None
