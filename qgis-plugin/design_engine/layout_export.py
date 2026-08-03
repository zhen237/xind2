"""
标准图纸导出模块
用于生成标准设计图纸并导出为PDF/PNG/SVG格式
"""

import os
from typing import List, Dict, Optional
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap,
    QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutExporter, QgsLayoutSize, QgsLayoutPoint,
    QgsUnitTypes, QgsMapSettings, QgsRectangle
)
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import QSizeF, QPointF, Qt


def create_design_layout(
    project: QgsProject,
    layout_name: str = "Base Station Design",
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
    map_position: QPointF = QPointF(15, 55),
    map_size: QSizeF = QSizeF(320, 210),
    scale: Optional[float] = None,
    layers: Optional[List] = None
) -> QgsLayoutItemMap:
    """
    添加地图到布局

    Args:
        layout: 打印布局
        map_extent: 地图范围
        map_position: 地图位置 (mm)
        map_size: 地图大小 (mm)

    Returns:
        地图项
    """
    from qgis.core import QgsCoordinateReferenceSystem

    # 创建地图项
    map_item = QgsLayoutItemMap(layout)
    map_item.setRect(0, 0, map_size.width(), map_size.height())
    map_item.attemptMove(QgsLayoutPoint(map_position.x(), map_position.y(), QgsUnitTypes.LayoutMillimeters))
    map_item.attemptResize(QgsLayoutSize(map_size.width(), map_size.height(), QgsUnitTypes.LayoutMillimeters))

    # 明确指定 CRS 与范围一致，避免项目 CRS 不一致导致灰底或错位
    map_item.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
    map_item.setMapRotation(0)

    # 图层来源:
    #  - 调用方显式指定 layers(如 FTTH 只渲染 8 个标准图层) -> 直接用
    #  - 否则关联当前项目的可见图层，确保基站/管线/热力图等设计图层正常渲染
    if layers is not None:
        valid = [lyr for lyr in layers if lyr is not None and lyr.isValid()]
        if valid:
            map_item.setLayers(valid)
    else:
        project = layout.project()
        visible_layers = []
        if project:
            root = project.layerTreeRoot()
            for layer in project.mapLayers().values():
                if not layer.isValid():
                    continue
                node = root.findLayer(layer.id())
                if node is None or node.isVisible() == Qt.Checked:
                    visible_layers.append(layer)
            if visible_layers:
                map_item.setLayers(visible_layers)

    # 直接使用调用方指定的导出范围（用户已自行在地图/框选中确定位置与比例），
    # 仅加 2% 边距避免元素贴边。不再强制使用所有图层的联合范围，
    # 否则包含整幅底图时设计内容会被缩成一团。
    final_extent = QgsRectangle(map_extent)
    if not final_extent.isEmpty():
        final_extent = final_extent.buffered(final_extent.width() * 0.02)
    map_item.setExtent(final_extent)
    map_item.setBackgroundColor(QColor(255, 255, 255))

    # 若用户指定了比例尺，按其设置（位置=范围中心，比例由用户决定）
    if scale and scale > 0:
        try:
            map_item.setScale(scale)
        except Exception:
            pass

    # 刷新地图项，确保布局导出前渲染管线已就绪
    map_item.refresh()

    # 添加到布局
    layout.addLayoutItem(map_item)

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
        print(f"Export failed: {e}")
        return False


def create_standard_design_drawing(
    project: QgsProject,
    sites: List[Dict],
    map_extent: QgsRectangle,
    title: str = "Base Station Design Drawing",
    output_path: str = None,
    paper_size: str = "A3",
    export_format: str = "PDF",
    scale: Optional[float] = None
) -> Optional[str]:
    """
    创建标准设计图纸

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
        # 创建布局
        layout = create_design_layout(project, title, paper_size)

        # 添加标题
        add_title_to_layout(layout, title)

        # 添加信息框
        info_text = f"Total Sites: {len(sites)} | Paper Size: {paper_size} | CRS: EPSG:4326"
        add_info_box_to_layout(layout, info_text)

        # 添加地图
        map_item = add_map_to_layout(layout, map_extent, scale=scale)

        # 添加图例
        add_legend_to_layout(layout, map_item)

        # 添加比例尺
        add_scale_bar_to_layout(layout, map_item)

        # 添加指北针
        add_north_arrow_to_layout(layout)

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
        print(f"Failed to create design drawing: {e}")
        return None


def create_ftth_drawing(
    project: QgsProject,
    ftth_layers: dict,
    map_extent: QgsRectangle,
    title: str = "FTTH Plan de Reculement",
    output_path: str = None,
    paper_size: str = "A3",
    export_format: str = "PDF",
    dpi: int = 300,
    scale: Optional[float] = None
) -> Optional[str]:
    """
    创建 FTTH 标准竣工图纸(仅渲染 8 个 FTTH 标准图层)。

    Args:
        project: QGIS 项目
        ftth_layers: {图层名: QgsVectorLayer} (由 qgis_style.load_ftth_layers 产出)
        map_extent: 地图范围(QgsRectangle)
        title: 图纸标题
        output_path: 输出路径
        paper_size: 纸张大小 (A3/A4)
        export_format: 导出格式 (PDF/PNG)
        dpi: 分辨率
        scale: 比例尺(可选，None=跟随范围)

    Returns:
        输出文件路径，失败返回 None
    """
    try:
        # 创建布局
        layout = create_design_layout(project, title, paper_size)

        # 添加标题
        add_title_to_layout(layout, title)

        # 信息框：各图层要素计数
        order = ["ZNRO", "ZPM", "INFRASTRUCTURE", "CABLE", "PTECH",
                 "SITE", "BOITE", "IMB"]
        parts = []
        for name in order:
            if name in ftth_layers:
                parts.append(f"{name}={ftth_layers[name].featureCount()}")
        info_text = " | ".join(parts) + " | CRS: EPSG:4326"
        add_info_box_to_layout(layout, info_text)

        # 添加地图(只渲染 FTTH 标准图层)
        map_item = add_map_to_layout(
            layout, map_extent,
            map_position=QPointF(15, 55),
            map_size=QSizeF(320, 210),
            scale=scale,
            layers=list(ftth_layers.values()),
        )

        # 添加图例 / 比例尺 / 指北针
        add_legend_to_layout(layout, map_item)
        add_scale_bar_to_layout(layout, map_item)
        add_north_arrow_to_layout(layout)

        # 导出
        if output_path is None:
            output_path = os.path.join(
                os.path.expanduser('~'), 'Desktop', f'{title}.{export_format.lower()}')

        if export_format.upper() == "PDF":
            ok, err = export_layout_to_pdf(layout, output_path, dpi=dpi)
            if not ok:
                print(f"FTTH PDF export failed: {err}")
                return None
            return output_path
        else:
            ok = export_layout_to_png(layout, output_path, dpi=dpi)
            return output_path if ok else None

    except Exception as e:
        print(f"Failed to create FTTH drawing: {e}")
        return None
