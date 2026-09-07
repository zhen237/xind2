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
    QgsUnitTypes, QgsMapSettings, QgsRectangle,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsLayoutItemShape, QgsLayoutItemMapGrid, QgsLayoutItemPage,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat,
)
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import QSizeF, QPointF, Qt


def _page_size_mm(layout: "QgsPrintLayout"):
    """返回页面尺寸 (宽, 高)，单位 mm。"""
    try:
        page = layout.pageCollection().pages()[0]
        sz = page.pageSize()
        return float(sz.width()), float(sz.height())
    except Exception:
        return 420.0, 297.0


def _layout_geometry(pw: float, ph: float):
    """根据页面尺寸计算地图/图例/比例尺/指北针的安全位置与尺寸，
    保证任何纸张 (A3/A4) 下元素都不超出页面而被裁切。

    图例/指北针作为地图右上角的叠加层，比例尺贴在地图左下角。
    """
    margin = 15.0
    top = 55.0          # 顶部留给标题 + 信息框
    bottom = 22.0       # 底部留给比例尺
    map_w = max(60.0, pw - 2 * margin)
    map_h = max(60.0, ph - top - bottom)
    map_pos = QPointF(margin, top)
    legend_w = min(70.0, map_w * 0.42)
    legend_h = min(120.0, map_h * 0.65)
    legend_pos = QPointF(pw - margin - legend_w, top + 6)
    north = 20.0
    north_pos = QPointF(pw - margin - north, 12.0)
    scale_pos = QPointF(margin + 2.0, ph - 18.0)
    info_w = max(140.0, pw - 2 * margin)
    info_pos = QPointF(margin, 33.0)
    return dict(
        map_pos=map_pos, map_size=QSizeF(map_w, map_h),
        legend_pos=legend_pos, legend_size=QSizeF(legend_w, legend_h),
        north_pos=north_pos, north_size=QSizeF(north, north),
        scale_pos=scale_pos, info_pos=info_pos, info_w=info_w,
    )


def _ensure_rendered(map_item, layout, total_ms: int = 1200):
    """多级刷新 + 事件循环等待，确保 Print Layout 地图项真正渲染完成
    （避免导出白图）。兼容从按钮点击（主线程嵌套事件循环）调用。"""
    from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QTimer
    try:
        from qgis.utils import iface as _iface
    except Exception:
        _iface = None
    if _iface is not None:
        try:
            _iface.mapCanvas().refresh()
            QCoreApplication.processEvents()
        except Exception:
            pass
    for ms in (200, 300, 400, total_ms):
        try:
            map_item.refresh()
            if layout is not None:
                layout.refresh()
        except Exception:
            pass
        QCoreApplication.processEvents()
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()


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
    layers: Optional[List] = None,
    extent_crs: Optional[QgsCoordinateReferenceSystem] = None,
    add_buffer: bool = True,
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

    # ── 先关联图层（必须在设置范围之前，zoomToExtent 依赖它） ──
    layer_crs = None
    if layers is not None:
        valid = [lyr for lyr in (layers.values() if isinstance(layers, dict) else layers) if lyr is not None and lyr.isValid()]
        if valid:
            map_item.setLayers(valid)
            # 取第一个有效图层的 CRS 作为地图项坐标系
            c = valid[0].crs()
            if c is not None and c.isValid() and c.authid():
                layer_crs = c
            total_feats = sum(lyr.featureCount() for lyr in valid)
            crs_auth = layer_crs.authid() if layer_crs else "?"
            print(f"[FTTH PDF] 地图项已关联 {len(valid)} 个图层, CRS={crs_auth}, "
                  f"要素总数={total_feats}")
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
                c = visible_layers[0].crs()
                if c is not None and c.isValid() and c.authid():
                    layer_crs = c

    # ── 确定地图项 CRS ──
    # 优先级：调用方明确给出的 extent_crs（与 extent 配套）> 第一个有效图层 CRS > 工程 CRS
    project_crs = layout.project().crs() if layout.project() else None
    target_crs = None
    if extent_crs is not None and extent_crs.isValid():
        target_crs = extent_crs
    elif layer_crs is not None and layer_crs.isValid():
        target_crs = layer_crs
    elif project_crs is not None and project_crs.isValid():
        target_crs = project_crs

    # ── 智能检测：PRJ 可能撒谎（仅对从图层猜出的 CRS 做校验）──
    # 常见坑：.prj 声称 EPSG:4326 但坐标值是投影网格（如 Lambert93）。
    if target_crs is not None and target_crs == layer_crs:
        authid = target_crs.authid() or ""
        if '4326' in authid or 'wgs84' in authid.lower():
            xmin, ymin = map_extent.xMinimum(), map_extent.yMinimum()
            xmax, ymax = map_extent.xMaximum(), map_extent.yMaximum()
            if (xmin < -360 or xmax > 360 or ymin < -90 or ymax > 90):
                print(f"[layout_export] CRS={authid} 与坐标范围不符: "
                      f"({xmin:.1f},{ymin:.1f})-({xmax:.1f},{ymax:.1f})，"
                      f"使用工程 CRS 兜底")
                target_crs = project_crs if (project_crs and project_crs.isValid()) else None

    if target_crs is not None:
        map_item.setCrs(target_crs)
    map_item.setMapRotation(0)

    # ── 构造最终范围，必要时做坐标转换 ──
    final_extent = QgsRectangle(map_extent)
    if not final_extent.isEmpty() and target_crs is not None \
       and extent_crs is not None and extent_crs.isValid() \
       and extent_crs != target_crs:
        try:
            transform = QgsCoordinateTransform(extent_crs, target_crs, QgsProject.instance())
            final_extent = transform.transformBoundingBox(final_extent)
            print(f"[layout_export] 范围已从 {extent_crs.authid()} 转换到 {target_crs.authid()}: "
                  f"({final_extent.xMinimum():.4f}, {final_extent.yMinimum():.4f}) - "
                  f"({final_extent.xMaximum():.4f}, {final_extent.yMaximum():.4f})")
        except Exception as e:
            print(f"[layout_export] 范围坐标转换失败，保留原范围: {e}")

    # 仅在非严格裁剪模式下加 2% 边距；严格模式（如框选导出）保持原范围
    if not final_extent.isEmpty() and add_buffer:
        final_extent = final_extent.buffered(final_extent.width() * 0.02)

    # 范围设置状态
    extent_set = False

    # ── 设置范围：优先用调用方指定的 extent，否则让地图项自动缩放到图层 ──
    if not final_extent.isEmpty():
        map_item.setExtent(final_extent)
        actual_after_set = map_item.extent()
        if actual_after_set.width() > 0 and actual_after_set.height() > 0:
            extent_set = True
            crs_label = target_crs.authid() if target_crs else "图层原生"
            print(f"[layout_export] 手动设定范围: ({final_extent.xMinimum():.4f}, {final_extent.yMinimum():.4f}) - "
                  f"({final_extent.xMaximum():.4f}, {final_extent.yMaximum():.4f}), CRS={crs_label}")
        else:
            print(f"[layout_export] WARNING: setExtent 后范围为空 (w={actual_after_set.width()}, h={actual_after_set.height()}), 将使用 zoomToExtent 兜底")

    if not extent_set:
        map_item.zoomToExtent()
        ext = map_item.extent()
        print(f"[layout_export] zoomToExtent 范围: ({ext.xMinimum():.4f}, {ext.yMinimum():.4f}) - "
              f"({ext.xMaximum():.4f}, {ext.yMaximum():.4f})")

    map_item.setBackgroundColor(QColor(255, 255, 255))

    # 若用户指定了比例尺，按其设置（位置=范围中心，比例由用户决定）
    if scale and scale > 0:
        try:
            map_item.setScale(scale)
        except Exception:
            pass

    # 先加入布局场景，再刷新（refresh 在 addLayoutItem 之前无效）
    layout.addLayoutItem(map_item)

    # 加入布局后立即刷新，触发渲染管线
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
        # 贴合内容，裁掉四周白边（PNG 不再留整页白底）
        # 注意：QGIS 3.34 LTR 自带的 PyQt 未暴露 QMarginsF，
        # 故不设置 cropMargins（默认 0 边距），cropToContents 已足够去白边。
        settings.cropToContents = True

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
    scale: Optional[float] = None,
    extent_crs: Optional[QgsCoordinateReferenceSystem] = None,
    map_frame_extent: Optional[QgsRectangle] = None,
    layers: Optional[List] = None,
) -> Optional[str]:
    """
    创建标准设计图纸

    Args:
        project: QGIS项目
        sites: 站点列表
        map_extent: 地图范围（应与 extent_crs 配套，未提供时默认与工程/画布 CRS 一致）
        title: 图纸标题
        output_path: 输出路径
        paper_size: 纸张大小
        export_format: 导出格式 (PDF/PNG)
        scale: 固定比例尺（None=跟随范围）
        extent_crs: map_extent 的坐标系；不填则按工程 CRS 处理
        map_frame_extent: 若提供，将在地图项上叠加一个红色矩形框，
                          表示用户框选的导出边界；同时地图范围严格对齐该框。
        layers: 指定地图项要渲染的图层列表；None 则使用项目可见图层。

    Returns:
        输出文件路径，失败返回None
    """
    try:
        # 创建布局
        layout = create_design_layout(project, title, paper_size)
        pw, ph = _page_size_mm(layout)
        geo = _layout_geometry(pw, ph)

        # 添加标题
        add_title_to_layout(layout, title)

        # 添加信息框（显示真实 CRS，不再硬编码 EPSG:4326）
        crs_label = extent_crs.authid() if (extent_crs and extent_crs.isValid()) else (project.crs().authid() if project else "未知")
        info_text = f"Total Sites: {len(sites)} | Paper: {paper_size} | CRS: {crs_label}"
        add_info_box_to_layout(layout, info_text,
                               position=geo['info_pos'],
                               size=QSizeF(geo['info_w'], 18))

        # 添加地图（尺寸/位置自适应页面，避免 A4 下被裁切）
        # 若用户指定了框选范围（map_frame_extent），地图严格按该范围显示，不加缓冲
        map_item = add_map_to_layout(
            layout, map_extent,
            map_position=geo['map_pos'],
            map_size=geo['map_size'],
            scale=scale, extent_crs=extent_crs,
            add_buffer=(map_frame_extent is None),
            layers=layers)

        # 若提供了框选范围，在地图项上叠加红色矩形框（与 CAD 图框视觉一致）
        if map_frame_extent is not None:
            try:
                frame = QgsLayoutItemShape(layout)
                frame.setShapeType(QgsLayoutItemShape.Rectangle)
                frame.attemptMove(QgsLayoutPoint(
                    geo['map_pos'].x(), geo['map_pos'].y(), QgsUnitTypes.LayoutMillimeters))
                frame.attemptResize(QgsLayoutSize(
                    geo['map_size'].width(), geo['map_size'].height(), QgsUnitTypes.LayoutMillimeters))
                frame.setStrokeColor(QColor(255, 0, 0))
                frame.setStrokeWidth(0.8)
                frame.setFillColor(QColor(255, 255, 255, 0))  # 透明填充
                layout.addLayoutItem(frame)
            except Exception as e:
                print(f"[layout_export] 地图红框添加失败（已忽略）: {e}")

        # 图例/比例尺/指北针作为地图角上的叠加层，任何纸张都不溢出
        add_legend_to_layout(layout, map_item,
                             position=geo['legend_pos'], size=geo['legend_size'])
        add_scale_bar_to_layout(layout, map_item, position=geo['scale_pos'])
        add_north_arrow_to_layout(layout, position=geo['north_pos'], size=geo['north_size'])

        # ── 强制渲染：多级刷新 + 事件循环等待，避免白图 ──
        _ensure_rendered(map_item, layout)

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


# ----------------------------------------------------------------------------
# 国标标准竣工图辅助函数（图框 / 图签 / 坐标网格 / 标注）
# ----------------------------------------------------------------------------

# FTTH 图层 -> 国标规范中文图例名（YD/T 5015 通信工程制图）
_FTTH_LEGEND_NAMES = {
    "ZNRO": "ZNRO 机房覆盖范围（面）",
    "ZPM": "ZPM 配线区范围（面）",
    "INFRASTRUCTURE": "INFRA 管道/杆路（线）",
    "CABLE": "CABLE 光缆（线）",
    "PTECH": "PTECH 杆路/人井（点）",
    "SITE": "SITE 站点/机房（点）",
    "BOITE": "BOITE 光交箱（点）",
    "IMB": "IMB 楼栋住户（点）",
}

# 需要打文字标注的图层及其字段（标识：站点号/箱体号/覆盖区号）
_LABEL_FIELD = {
    "SITE": "CODE", "BOITE": "CODE", "IMB": "CODE",
    "ZNRO": "CODE", "ZPM": "CODE",
}


def _nice_interval(raw: float) -> float:
    """把原始间隔取整到 1/2/5 × 10ⁿ 的『漂亮』刻度数。"""
    if raw is None or raw <= 0:
        return 1.0
    import math
    mag = 10 ** math.floor(math.log10(raw))
    norm = raw / mag
    step = 1.0 if norm <= 1 else 2.0 if norm <= 2 else 5.0 if norm <= 5 else 10.0
    return step * mag


def _add_drawing_frame(layout: "QgsPrintLayout", pw: float, ph: float,
                        margin: float = 10.0):
    """在页面四周画标准图框（黑色细线矩形）。"""
    try:
        frame = QgsLayoutItemShape(layout)
        frame.setShapeType(QgsLayoutItemShape.Rectangle)
        frame.attemptMove(QgsLayoutPoint(margin, margin, QgsUnitTypes.LayoutMillimeters))
        frame.attemptResize(QgsLayoutSize(
            pw - 2 * margin, ph - 2 * margin, QgsUnitTypes.LayoutMillimeters))
        frame.setStrokeColor(QColor(0, 0, 0))
        frame.setStrokeWidth(0.6)
        frame.setFillColor(QColor(255, 255, 255, 0))  # 透明填充
        layout.addLayoutItem(frame)
        print("[layout_export] 已添加图框")
    except Exception as e:
        print(f"[layout_export] 图框添加失败: {e}")


def _add_title_block(layout: "QgsPrintLayout", pw: float, ph: float,
                     margin: float, fields: dict):
    """在右下角画国标图签（标题栏表格）：工程名称/图名/比例/坐标系/日期图号/设计审核。"""
    try:
        # 图签尺寸（mm）：宽 88，高 36，置于右下页边距内
        w, h = 88.0, 36.0
        x = pw - margin - w
        y = ph - margin - h
        # 外边框
        box = QgsLayoutItemShape(layout)
        box.setShapeType(QgsLayoutItemShape.Rectangle)
        box.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
        box.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
        box.setStrokeColor(QColor(0, 0, 0))
        box.setStrokeWidth(0.5)
        box.setFillColor(QColor(255, 255, 255))
        layout.addLayoutItem(box)

        # 内部横向分隔线（3 行：基础信息 / 比例坐标系 / 日期审核）
        rows = 3
        for i in range(1, rows):
            ly = y + h * i / rows
            line = QgsLayoutItemShape(layout)
            line.setShapeType(QgsLayoutItemShape.Rectangle)
            line.attemptMove(QgsLayoutPoint(x, ly, QgsUnitTypes.LayoutMillimeters))
            line.attemptResize(QgsLayoutSize(w, 0.01, QgsUnitTypes.LayoutMillimeters))
            line.setStrokeColor(QColor(0, 0, 0))
            line.setStrokeWidth(0.3)
            line.setFillColor(QColor(0, 0, 0))
            layout.addLayoutItem(line)

        # 文本块（左列字段名 + 右列值）
        labels = [
            ("工程名称", fields.get("工程名称", "")),
            ("图纸名称", fields.get("图纸名称", "")),
            ("比例 / 坐标系", f"{fields.get('比例','')}  {fields.get('坐标系','')}"),
            ("日期 / 图号", f"{fields.get('日期','')}  {fields.get('图号','')}"),
            ("设计 / 审核", fields.get("设计审核", "")),
        ]
        # 5 行文本均分图签高度
        n = len(labels)
        for i, (k, v) in enumerate(labels):
            txt = QgsLayoutItemLabel(layout)
            txt.setText(f"{k}：{v}")
            # PyQt5 的 QFont(family, pointSize) 只收 int；7.5 这类小数字号
            # 须用 setPointSizeF(qreal)，否则真机报 overloaded call 错误
            txt_font = QFont("SimSun")
            txt_font.setPointSizeF(7.5)
            txt.setFont(txt_font)
            txt.setMargin(1.5)
            txt.attemptMove(QgsLayoutPoint(
                x + 2, y + h * i / n + 1, QgsUnitTypes.LayoutMillimeters))
            txt.attemptResize(QgsLayoutSize(
                w - 4, h / n - 1, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(txt)
        print("[layout_export] 已添加图签")
    except Exception as e:
        print(f"[layout_export] 图签添加失败: {e}")


def _add_map_coordinate_grid(map_item: "QgsLayoutItemMap", crs):
    """给地图项加坐标网格（经纬网/方里网），带注记。"""
    try:
        ext = map_item.extent()
        if ext.isEmpty():
            return
        is_geo = (crs is not None and crs.isValid()
                  and ('4326' in (crs.authid() or '')
                       or 'wgs84' in (crs.authid() or '').lower()))
        interval = _nice_interval(ext.width() / 5.0)
        grid = QgsLayoutItemMapGrid("坐标网格", map_item)
        grid.setEnabled(True)
        grid.setStyle(QgsLayoutItemMapGrid.Solid)
        grid.setAnnotationEnabled(True)
        grid.setAnnotationDisplay(QgsLayoutItemMapGrid.Outward)
        grid.setAnnotationFormat(QgsLayoutItemMapGrid.Decimal)
        grid.setAnnotationPrecision(5 if is_geo else 0)
        grid.setIntervalX(interval)
        grid.setIntervalY(interval)
        grid.setPenWidth(0.15)
        grid.setAnnotationFont(QFont("Arial", 6))
        if crs is not None and crs.isValid():
            grid.setCrs(crs)
        map_item.grids().addGrid(grid)
        print(f"[layout_export] 已添加坐标网格: interval={interval:.4f} "
              f"({'经纬网' if is_geo else '方里网'})")
    except Exception as e:
        print(f"[layout_export] 坐标网格添加失败: {e}")


def _apply_ftth_labels(ftth_layers: dict):
    """为关键 FTTH 图层临时开启 CODE 文字标注，返回旧状态列表以便还原。"""
    saved = []
    try:
        for name, layer in (ftth_layers or {}).items():
            if layer is None or not layer.isValid():
                continue
            field = _LABEL_FIELD.get(name)
            if not field:
                continue
            if field not in [f.name() for f in layer.fields()]:
                continue
            saved.append((layer, layer.labelsEnabled(), layer.labeling()))
            fmt = QgsTextFormat()
            fmt.setSize(7.0)
            fmt.setSizeUnit(QgsUnitTypes.RenderPoints)
            fmt.setColor(QColor(15, 23, 42))
            pal = QgsPalLayerSettings()
            pal.fieldName = field
            pal.setFormat(fmt)
            pal.placement = QgsPalLayerSettings.OverPoint
            layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
            layer.setLabelsEnabled(True)
            layer.triggerRepaint()
        print(f"[layout_export] 已为 {len(saved)} 个图层开启标注")
    except Exception as e:
        print(f"[layout_export] 标注启用失败: {e}")
    return saved


def _restore_ftth_labels(saved):
    """还原图层标注状态（避免永久改变画布）。"""
    for layer, was_enabled, old_labeling in saved:
        try:
            layer.setLabelsEnabled(was_enabled)
            layer.setLabeling(old_labeling)
            layer.triggerRepaint()
        except Exception:
            pass


def _rename_legend_entries(legend_item, ftth_layers: dict):
    """把图例条目改名成国标中文规范名。"""
    try:
        root = legend_item.model().rootGroup()
        for name, layer in (ftth_layers or {}).items():
            if layer is None or not layer.isValid():
                continue
            lg = root.findLayer(layer.id())
            if lg is not None:
                lg.setCustomLabel(_FTTH_LEGEND_NAMES.get(name, name))
        legend_item.refresh()
        print("[layout_export] 图例已改为中文规范名")
    except Exception as e:
        print(f"[layout_export] 图例改名失败: {e}")


def create_ftth_drawing(
    project: QgsProject,
    ftth_layers: dict,
    map_extent: QgsRectangle,
    title: str = "FTTH Plan de Reculement",
    output_path: str = None,
    paper_size: str = "A3",
    export_format: str = "PDF",
    dpi: int = 300,
    scale: Optional[float] = None,
    with_title_block: bool = True,
    with_grid: bool = True,
    with_labels: bool = True,
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
    from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QTimer

    saved_labels = []
    try:
        # ── 前置：强制刷新画布渲染，确保图层已就绪 ──
        iface_ref = None
        try:
            from qgis.utils import iface as _iface
            iface_ref = _iface
        except Exception:
            pass
        if iface_ref is not None:
            canvas = iface_ref.mapCanvas()
            canvas.refresh()
            # 等 500ms 让渲染管线完成（Print Layout 读的是渲染缓存）
            loop = QEventLoop()
            QTimer.singleShot(500, loop.quit)
            loop.exec()

        # 创建布局
        layout = create_design_layout(project, title, paper_size)
        pw, ph = _page_size_mm(layout)
        margin = 10.0

        # 标准图框（国标竣工图外边框）
        if with_title_block:
            _add_drawing_frame(layout, pw, ph, margin)

        # 添加标题
        add_title_to_layout(layout, title)

        # 信息框：各图层要素计数 + 实际 CRS
        order = ["ZNRO", "ZPM", "INFRASTRUCTURE", "CABLE", "PTECH",
                 "SITE", "BOITE", "IMB"]
        parts = []
        actual_crs = "?"
        for name in order:
            if name in ftth_layers:
                parts.append(f"{name}={ftth_layers[name].featureCount()}")
                if actual_crs == "?":
                    c = ftth_layers[name].crs()
                    actual_crs = c.authid() if (c and c.isValid() and c.authid()) else "未知"
        info_text = " | ".join(parts) + f" | CRS: {actual_crs}"
        add_info_box_to_layout(layout, info_text)

        # 添加地图(只渲染 FTTH 标准图层)
        valid_layers = [lyr for lyr in ftth_layers.values()
                       if lyr is not None and lyr.isValid()]
        if not valid_layers:
            print("[FTTH PDF] 无有效图层，跳过地图项")
            return None

        # 明确告诉 add_map_to_layout：extent 的坐标系就是第一个有效图层的 CRS，
        # 避免它按其他图层 CRS 解释数值导致范围被压扁。
        extent_crs = valid_layers[0].crs()
        geo = _layout_geometry(*_page_size_mm(layout))
        map_item = add_map_to_layout(
            layout, map_extent,
            map_position=geo['map_pos'],
            map_size=geo['map_size'],
            scale=scale,
            layers=valid_layers,
            extent_crs=extent_crs,
        )

        # 坐标网格（国标竣工图需有坐标网/方里网注记）
        if with_grid:
            _add_map_coordinate_grid(map_item, extent_crs)

        # 临时开启关键图层 CODE 文字标注（图上有标识，导出后还原）
        saved_labels = _apply_ftth_labels(ftth_layers) if with_labels else []

        # 图例 / 比例尺 / 指北针作为地图角上的叠加层，位置自适应页面（A3/A4 都不溢出）
        legend_item = add_legend_to_layout(layout, map_item,
                             position=geo['legend_pos'], size=geo['legend_size'])
        add_scale_bar_to_layout(layout, map_item, position=geo['scale_pos'])
        add_north_arrow_to_layout(layout, position=geo['north_pos'], size=geo['north_size'])
        # 图例改为国标中文规范名
        _rename_legend_entries(legend_item, ftth_layers)

        # ── 多级渲染等待，确保地图项真正渲染完成（避免白图）──
        _ensure_rendered(map_item, layout)

        # 导出前最终诊断：记录地图项实际状态
        # 注意：QgsLayoutItemMap 没有 itemPosition() 方法（会抛 AttributeError 并
        # 导致整个导出失败 → 白图）。正确取"地图项在页面上的位置"用 pagePos()，
        # 旧版本可能用 positionOnPage() 或 pos()，做三级兼容。
        try:
            pre_ext = map_item.pagePos()
        except AttributeError:
            try:
                pre_ext = map_item.positionOnPage()
            except AttributeError:
                pre_ext = map_item.pos()
        map_ext = map_item.extent()
        print(f"[FTTH PDF] 导出前诊断: map_item pos=({pre_ext.x():.1f},{pre_ext.y():.1f}), "
              f"extent=({map_ext.xMinimum():.4f},{map_ext.yMinimum():.4f})-({map_ext.xMaximum():.4f},{map_ext.yMaximum():.4f}), "
              f"layers={len(map_item.layers()) if hasattr(map_item, 'layers') else '?'}")
        map_ext = map_item.extent()

        # 最终再刷一轮，确保图例/比例尺已基于渲染后的地图项就位
        layout.refresh()
        QCoreApplication.processEvents()
        final_wait = QEventLoop()
        QTimer.singleShot(400, final_wait.quit)
        final_wait.exec()

        # ── 图签（国标竣工图标题栏）──
        if with_title_block:
            try:
                sc = map_item.scale()
                scale_txt = f"1:{int(round(sc))}" if sc and sc > 0 else "随图自适应"
            except Exception:
                scale_txt = "随图自适应"
            import datetime as _dt
            fields = {
                "工程名称": "通信基建数智化全流程平台",
                "图纸名称": "FTTH 竣工图 (Plan de Reculement)",
                "比例": scale_txt,
                "坐标系": actual_crs if actual_crs != "?" else "未知",
                "日期": _dt.date.today().isoformat(),
                "图号": "FTTH-001",
                "设计审核": "设计：__________  审核：__________",
            }
            _add_title_block(layout, pw, ph, margin, fields)

        # 导出
        if output_path is None:
            output_path = os.path.join(
                os.path.expanduser('~'), 'Desktop', f'{title}.{export_format.lower()}')

        if export_format.upper() == "PDF":
            ok, err = export_layout_to_pdf(layout, output_path, dpi=dpi)
            if not ok:
                print(f"FTTH PDF export failed: {err}")
                _restore_ftth_labels(saved_labels)
                return None
            _restore_ftth_labels(saved_labels)
            return output_path
        else:
            ok = export_layout_to_png(layout, output_path, dpi=dpi)
            _restore_ftth_labels(saved_labels)
            return output_path if ok else None

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed to create FTTH drawing: {e}")
        _restore_ftth_labels(saved_labels)
        return None


# ======================================================================== #
#  标准工程图册辅助函数（图框 / 图衔 / BOM 表 / 技术要求）
#  （自 stash eead1cc0 恢复；编制依据标注：GB 51456-2023）
# ======================================================================== #

# 技术要求默认条款：第一条为编制依据（GB 51456-2023《建筑物移动通信基础
# 设施工程技术标准》，住建部 2023-05-23 发布、2023-09-01 施行），其余沿用
# 原版通用条款。
DEFAULT_TECH_REQUIREMENTS = [
    "1. 本图集依据 GB 51456-2023《建筑物移动通信基础设施工程技术标准》编制。",
    "2. 本图尺寸单位：标高为米(m)，其余为毫米(mm)；坐标系统采用 CGCS2000。",
    "3. 铁塔基础按《移动通信工程钢塔桅结构设计规范》(YD/T 5131) 执行。",
    "4. 接地电阻≤10Ω；接地网采用热镀锌扁钢，埋深≥0.7m。",
    "5. 设备安装应符合 YD/T 5230 及相关行业标准要求。",
    "6. 未尽事宜按现行国家及行业有关标准、规范执行。",
]


def draw_frame(layout: QgsPrintLayout, page_index: int = 0,
               page_width: float = 420.0, page_height: float = 297.0,
               margin: float = 10.0):
    """在指定页面绘制标准工程图框（外粗线 + 内细线）。

    坐标一律使用页内相对坐标，并通过 attemptMove 的 page 参数绑定页码
    （不手工 y += PH*page_index——那会忽略页间间隙 spaceBetweenPages()，
    导致跨页元素被裁出页外或错位）。

    Args:
        layout: 打印布局
        page_index: 页码（0-based）
        page_width, page_height: 页面尺寸 (mm)
        margin: 图框距页边距离 (mm)
    """
    # 外框（粗线）
    outer = QgsLayoutItemShape(layout)
    outer.setShapeType(QgsLayoutItemShape.Rectangle)
    outer.attemptMove(QgsLayoutPoint(margin, margin,
                                     QgsUnitTypes.LayoutMillimeters),
                      page=page_index)
    outer.attemptResize(QgsLayoutSize(page_width - 2 * margin,
                                      page_height - 2 * margin,
                                      QgsUnitTypes.LayoutMillimeters))
    # 通过 symbol 设置描边（QGIS 3.x+ 方式）
    try:
        from qgis.core import QgsFillSymbol, QgsSimpleLineSymbolLayer
        sl = QgsSimpleLineSymbolLayer.create({'width': '1.2', 'color': '#1f2933'})
        sym = QgsFillSymbol([sl])
        sym.setOpacity(0)  # 填充透明，只留边框
        outer.setSymbol(sym)
    except Exception:
        pass  # 旧版 QGIS 兜底：默认样式也可接受
    layout.addLayoutItem(outer)

    # 内框（细线，距外框 5mm）
    inner_margin = margin + 5.0
    inner = QgsLayoutItemShape(layout)
    inner.setShapeType(QgsLayoutItemShape.Rectangle)
    inner.attemptMove(QgsLayoutPoint(inner_margin, inner_margin,
                                     QgsUnitTypes.LayoutMillimeters),
                      page=page_index)
    inner.attemptResize(QgsLayoutSize(page_width - 2 * inner_margin,
                                      page_height - 2 * inner_margin,
                                      QgsUnitTypes.LayoutMillimeters))
    try:
        from qgis.core import QgsFillSymbol, QgsSimpleLineSymbolLayer
        sl2 = QgsSimpleLineSymbolLayer.create(
            {'width': '0.4', 'color': '#5b6770'})
        sym2 = QgsFillSymbol([sl2])
        sym2.setOpacity(0)
        inner.setSymbol(sym2)
    except Exception:
        pass
    layout.addLayoutItem(inner)


def add_title_block(layout: QgsPrintLayout, page_index: int = 0,
                    sheet_name: str = "通信基站设计图",
                    scale_text: str = "1:100",
                    drawing_no: str = "0001",
                    designer: str = "",
                    reviewer: str = "",
                    org_name: str = "通信基建数智化平台"):
    """添加国标风格图衔（标题栏）到页面底部。

    采用横向条带式布局（A3 横向适配），含：
      图名 | 图号 | 比例 | 设计 | 审核 | 单位 | 日期 | 设计依据

    与 stash 原版的差异：
      1) 末尾新增「设计依据：GB 51456-2023」列（用户要求的国标标注）；
      2) 各列宽度按页面实际宽度等比缩放——原版列宽合计 545mm，A3 横向
         (420mm) 下会溢出页面，这里保证整条图衔始终落在页边距内。

    Args:
        layout: 打印布局
        page_index: 页码
        sheet_name: 图纸名称
        scale_text: 比例尺文字
        drawing_no: 图号
        designer: 设计人
        reviewer: 审核人
        org_name: 设计单位
    """
    from datetime import date as _date
    # 从布局实际页面尺寸取宽高，避免 A4 等比例下错位
    try:
        _pages = layout.pageCollection().pages()
        _pw = (_pages[page_index].pageSize().width()
               if 0 <= page_index < len(_pages) else 420.0)
        _ph = (_pages[page_index].pageSize().height()
               if 0 <= page_index < len(_pages) else 297.0)
    except Exception:
        _pw, _ph = 420.0, 297.0
    # tb_y 为页内相对坐标（距该页底边 7mm）；绑页交给 attemptMove 的
    # page 参数，不手工加 _ph*page_index 偏移（会忽略页间间隙导致跨页错位）
    tb_y = _ph - 29.0   # 条带顶部 y（距底边 7mm，条带高 22mm）
    tb_h = 22.0                     # 条带高度
    cols = [
        ["图名", sheet_name, 170.0],
        ["图号", drawing_no, 50.0],
        ["比例", scale_text, 45.0],
        ["设计", designer or "AI 辅助", 55.0],
        ["审核", reviewer or "", 45.0],
        ["单位", org_name, 80.0],
        # 日期 + 设计依据（用户要求在图衔标注所用国标）
        ["日期", _date.today().strftime("%Y-%m-%d"), 42.0],
        ["设计依据", "GB 51456-2023", 52.0],
    ]

    # 等比缩放列宽，使整条图衔（含分隔余量）不超出页面可用宽度
    x_start = 15.0
    natural = sum(c[2] for c in cols) + 2.0 * (len(cols) - 1)  # 列间 2mm 分隔线
    avail = max(_pw - 2 * x_start, 120.0)
    if natural > avail:
        ratio = avail / natural
        for c in cols:
            c[2] = c[2] * ratio

    font_title = QFont('SimHei', 9, QFont.Bold)
    font_val = QFont('SimSun', 8)

    cx = x_start
    for label, value, w in cols:
        # 列分隔竖线
        if cx > x_start:
            sep = QgsLayoutItemShape(layout)
            sep.setShapeType(QgsLayoutItemShape.Rectangle)
            sep.attemptMove(QgsLayoutPoint(cx, tb_y,
                                           QgsUnitTypes.LayoutMillimeters),
                            page=page_index)
            sep.attemptResize(QgsLayoutSize(0.4, tb_h, QgsUnitTypes.LayoutMillimeters))
            try:
                from qgis.core import QgsFillSymbol, QgsSimpleLineSymbolLayer
                s = QgsFillSymbol([
                    QgsSimpleLineSymbolLayer.create(
                        {'width': '0.4', 'color': '#5b6770'})])
                s.setOpacity(0)
                sep.setSymbol(s)
            except Exception:
                pass
            layout.addLayoutItem(sep)
            cx += 2.0

        # 标签行（上半格）
        lbl = QgsLayoutItemLabel(layout)
        lbl.setText(label)
        lbl.setFont(font_title)
        lbl.attemptMove(QgsLayoutPoint(cx + 2, tb_y + 1,
                                       QgsUnitTypes.LayoutMillimeters),
                        page=page_index)
        lbl.attemptResize(QgsLayoutSize(w - 4, 9,
                                         QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(lbl)

        # 值行（下半格）
        val = QgsLayoutItemLabel(layout)
        val.setText(value)
        val.setFont(font_val)
        val.attemptMove(QgsLayoutPoint(cx + 2, tb_y + 11,
                                        QgsUnitTypes.LayoutMillimeters),
                        page=page_index)
        val.attemptResize(QgsLayoutSize(w - 4, 9,
                                         QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(val)

        cx += w

    # 外边框
    frame = QgsLayoutItemShape(layout)
    frame.setShapeType(QgsLayoutItemShape.Rectangle)
    frame.attemptMove(QgsLayoutPoint(x_start, tb_y,
                                     QgsUnitTypes.LayoutMillimeters),
                      page=page_index)
    total_w = cx - x_start
    frame.attemptResize(QgsLayoutSize(total_w, tb_h,
                                      QgsUnitTypes.LayoutMillimeters))
    try:
        from qgis.core import QgsFillSymbol, QgsSimpleLineSymbolLayer
        sf = QgsFillSymbol([
            QgsSimpleLineSymbolLayer.create(
                {'width': '1.0', 'color': '#1f2933'})])
        sf.setOpacity(0)
        frame.setSymbol(sf)
    except Exception:
        pass
    layout.addLayoutItem(frame)


def _bom_table_svg(site) -> str:
    """从 Site.bill_of_materials() 生成 BOM 表 SVG 字符串。

    纯 Python，无 QGIS 依赖。返回的 SVG 可通过 QgsLayoutItemPicture 嵌入。
    """
    bom = site.bill_of_materials() if hasattr(site, 'bill_of_materials') else None
    items = []
    summary = ""
    if bom and isinstance(bom, dict):
        items = bom.get("items", [])
        summary = bom.get("summary", "")

    FONTS = "'Microsoft YaHei','SimHei',sans-serif"
    STROKE = "#1f2933"
    THIN = "#5b6770"

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    W, H = 420.0, max(len(items) * 20 + 60, 90)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {W:.0f} {H:.0f}" '
             f'font-family="{FONTS}">']

    # 表头背景
    parts.append(f'<rect x="0" y="0" width="{W}" height="28" '
                 f'fill="#eef1f4" stroke="{STROKE}" stroke-width="0.8"/>')
    headers = ["序号", "名称", "规格/型号", "数量", "单位"]
    col_w = [40, 140, 150, 50, 40]
    hx = 0
    for h, cw in zip(headers, col_w):
        parts.append(f'<text x="{hx+cw/2}" y="18" font-size="9" '
                     f'fill="{STROKE}" text-anchor="middle" '
                     f'font-weight="bold">{esc(h)}</text>')
        hx += cw

    # 数据行
    for r_idx, item in enumerate(items):
        ry = 28 + r_idx * 20
        bg = "#ffffff" if r_idx % 2 == 0 else "#fafbfc"
        parts.append(f'<rect x="0" y="{ry}" width="{W}" height="20" '
                     f'fill="{bg}" stroke="{THIN}" stroke-width="0.4"/>')
        vals = [
            str(r_idx + 1),
            item.get("name", ""),
            item.get("spec", ""),
            str(item.get("qty", "")),
            item.get("unit", ""),
        ]
        vx = 0
        for v, cw in zip(vals, col_w):
            parts.append(f'<text x="{vx+4}" y="{ry+14}" font-size="8.5" '
                         f'fill="{STROKE}">{esc(v)}</text>')
            vx += cw

    # 汇总行
    sy = H - 24
    parts.append(f'<line x1="0" y1="{sy-2}" x2="{W}" y2="{sy-2}" '
                 f'stroke="{STROKE}" stroke-width="0.8"/>')
    parts.append(f'<text x="4" y="{sy+12}" font-size="9" fill="{STROKE}" '
                 f'font-weight="bold">汇总：{esc(summary)}</text>')

    parts.append('</svg>')
    return "".join(parts)


def add_bom_table_from_site(layout: QgsPrintLayout, site,
                            position: QPointF = QPointF(15, 155),
                            size: QSizeF = QSizeF(390, 110),
                            temp_registry: list = None):
    """将 Site 的 BOM 表以 SVG 图片形式嵌入布局。

    Args:
        layout: 打印布局
        site: models.site.Site 对象（需有 bill_of_materials 方法）
        position: 左上角位置 (mm)
        size: 显示尺寸 (mm)
        temp_registry: 可选列表；临时 SVG 路径会 append 进去，
                       由调用方在导出后统一清理（避免 %TEMP% 泄漏）
    Returns:
        QgsLayoutItemPicture 或 None
    """
    import tempfile, os
    svg_str = _bom_table_svg(site)
    if not svg_str.strip():
        return None

    fd, path = tempfile.mkstemp(suffix=".bom.svg", prefix="eng_",
                                dir=tempfile.gettempdir())
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(svg_str)
    if temp_registry is not None:
        temp_registry.append(path)

    pic = QgsLayoutItemPicture(layout)
    pic.setPicturePath(path)
    pic.attemptMove(QgsLayoutPoint(position.x(), position.y(),
                                    QgsUnitTypes.LayoutMillimeters))
    pic.attemptResize(QgsLayoutSize(size.width(), size.height(),
                                     QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(pic)
    return pic


def add_tech_requirements(layout: QgsPrintLayout,
                          lines: List[str] = None,
                          position: QPointF = QPointF(15, 275),
                          size: QSizeF = QSizeF(390, 16)):
    """添加技术要求文本块（多行编号列表）。

    Args:
        layout: 打印布局
        lines: 技术要求行列表（默认 DEFAULT_TECH_REQUIREMENTS，
               第一条为编制依据 GB 51456-2023）
        position: 位置 (mm)
        size: 尺寸 (mm)
    Returns:
        QgsLayoutItemLabel（便于调用方用 attemptMove(page=...) 绑定页码）
    """
    if lines is None:
        lines = list(DEFAULT_TECH_REQUIREMENTS)
    text = "\n".join(lines)
    label = QgsLayoutItemLabel(layout)
    label.setText(text)
    # PyQt5 的 QFont(family, pointSize) 只收 int；7.5 这类小数字号
    # 须用 setPointSizeF(qreal)，否则真机报 overloaded call 错误
    tech_font = QFont('SimSun')
    tech_font.setPointSizeF(7.5)
    label.setFont(tech_font)
    label.attemptMove(QgsLayoutPoint(position.x(), position.y(),
                                     QgsUnitTypes.LayoutMillimeters))
    label.attemptResize(QgsLayoutSize(size.width(), size.height(),
                                      QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(label)
    return label


# ======================================================================== #
#  图册 SVG 视图生成（纯 Python，无 QGIS 依赖）
#  说明：stash 原版引用了 design_engine.sheet_svg 模块，但该文件从未入库
#  （stash 树中也不存在）。此处按主函数引用的 viewBox 比例（铁塔 320x470、
#  机房 520x380）内联重写实现，避免悬空 import。
# ======================================================================== #

def _draw_tower_elevation_svg(site) -> str:
    """生成铁塔立面示意图 SVG（viewBox 320x470）。

    依据 site.tower_type 绘制单管塔 / 角钢塔轮廓，标注塔高与天线挂高。
    """
    FONTS = "'Microsoft YaHei','SimHei',sans-serif"
    STROKE = "#1f2933"
    THIN = "#5b6770"

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    tower_type = str(getattr(site, "tower_type", "MONOPOLE") or "MONOPOLE")
    tower_h = float(getattr(site, "tower_height", 35.0) or 35.0)
    type_label = {"MONOPOLE": "单管塔", "LATTICE": "角钢塔"}.get(
        tower_type, "通信塔")

    W, H = 320.0, 470.0
    ground_y = 430.0
    top_y = 80.0
    cx = 185.0

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONTS}">']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" '
                 f'fill="#ffffff"/>')

    # 地面线 + 填土斜线
    parts.append(f'<line x1="20" y1="{ground_y}" x2="{W-20}" y2="{ground_y}" '
                 f'stroke="{STROKE}" stroke-width="1.6"/>')
    gx = 28.0
    while gx < W - 24:
        parts.append(f'<line x1="{gx}" y1="{ground_y}" x2="{gx-7}" '
                     f'y2="{ground_y+8}" stroke="{THIN}" stroke-width="0.7"/>')
        gx += 14.0

    if tower_type == "LATTICE":
        # 角钢塔：双腿收分 + 交叉腹杆
        base_half, top_half = 44.0, 14.0
        lb, rb = cx - base_half, cx + base_half
        lt, rt = cx - top_half, cx + top_half
        parts.append(f'<line x1="{lb}" y1="{ground_y}" x2="{lt}" y2="{top_y}" '
                     f'stroke="{STROKE}" stroke-width="2"/>')
        parts.append(f'<line x1="{rb}" y1="{ground_y}" x2="{rt}" y2="{top_y}" '
                     f'stroke="{STROKE}" stroke-width="2"/>')
        segs = 9
        for i in range(1, segs):
            t = i / segs
            y = ground_y + (top_y - ground_y) * t
            xl = lb + (lt - lb) * t
            xr = rb + (rt - rb) * t
            if i % 2 == 1:
                parts.append(f'<line x1="{xl:.1f}" y1="{y:.1f}" '
                             f'x2="{xr:.1f}" y2="{y - (ground_y-top_y)/segs:.1f}" '
                             f'stroke="{THIN}" stroke-width="0.9"/>')
            else:
                parts.append(f'<line x1="{xl:.1f}" y1="{y:.1f}" '
                             f'x2="{xr:.1f}" y2="{y:.1f}" '
                             f'stroke="{THIN}" stroke-width="0.9"/>')
    else:
        # 单管塔：锥形钢管 + 法兰
        pole_w_top, pole_w_bot = 10.0, 26.0
        parts.append(f'<polygon points="{cx-pole_w_bot/2},{ground_y} '
                     f'{cx+pole_w_bot/2},{ground_y} '
                     f'{cx+pole_w_top/2},{top_y} '
                     f'{cx-pole_w_top/2},{top_y}" fill="#f4f6f8" '
                     f'stroke="{STROKE}" stroke-width="1.6"/>')
        fy = ground_y
        for _ in range(3):
            parts.append(f'<line x1="{cx-pole_w_bot/2-4}" y1="{fy}" '
                         f'x2="{cx+pole_w_bot/2+4}" y2="{fy}" '
                         f'stroke="{THIN}" stroke-width="1.0"/>')
            fy -= (ground_y - top_y) / 3.0

    # 天线平台 + 天线板（3 面）
    parts.append(f'<line x1="{cx-34}" y1="{top_y+6}" x2="{cx+34}" '
                 f'y2="{top_y+6}" stroke="{STROKE}" stroke-width="2.2"/>')
    for ax, ah in ((cx - 28, 34.0), (cx + 22, 34.0), (cx - 3, 30.0)):
        parts.append(f'<rect x="{ax}" y="{top_y+6-ah}" width="7" '
                     f'height="{ah}" rx="3" fill="#dfe6ec" '
                     f'stroke="{STROKE}" stroke-width="1.0"/>')

    # 塔高尺寸标注（左侧）
    dx = 78.0
    parts.append(f'<line x1="{dx}" y1="{top_y+6}" x2="{dx}" '
                 f'y2="{ground_y}" stroke="{STROKE}" stroke-width="0.8"/>')
    for yy in (top_y + 6, ground_y):
        parts.append(f'<line x1="{dx-5}" y1="{yy}" x2="{dx+5}" y2="{yy}" '
                     f'stroke="{STROKE}" stroke-width="0.8"/>')
    parts.append(f'<text x="{dx-8}" y="{(top_y+ground_y)/2}" font-size="12" '
                 f'fill="{STROKE}" text-anchor="end">'
                 f'H={tower_h:.0f}m</text>')

    # 图名
    parts.append(f'<text x="{W/2}" y="{H-16}" font-size="13" '
                 f'fill="{STROKE}" text-anchor="middle" '
                 f'font-weight="bold">{esc(getattr(site, "name", "") or "基站")}'
                 f' — 铁塔立面示意图（{esc(type_label)}）</text>')
    parts.append('</svg>')
    return "".join(parts)


def _draw_room_layout_svg(room, site) -> str:
    """生成机房设备布置示意图 SVG（viewBox 520x380）。

    room 为 None 时按通用汇聚机房绘制示意布置。
    """
    FONTS = "'Microsoft YaHei','SimHei',sans-serif"
    STROKE = "#1f2933"
    THIN = "#5b6770"

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    room_name = str(getattr(room, "name", "") or
                    (getattr(site, "name", "") or "基站") + "机房")
    room_type = str(getattr(room, "room_type", "") or "汇聚机房")
    power = str(getattr(room, "power_supply", "") or "AC220V")
    cap = getattr(room, "capacity", None)
    cap_text = f"{float(cap):.0f}kVA" if cap else "—"

    W, H = 520.0, 380.0
    rx, ry, rw, rh = 40.0, 66.0, 440.0, 250.0

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONTS}">']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" '
                 f'fill="#ffffff"/>')

    # 房间墙体（双线）+ 门洞（右下）+ 窗（上墙）
    parts.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" '
                 f'fill="#fbfcfd" stroke="{STROKE}" stroke-width="2.2"/>')
    parts.append(f'<rect x="{rx+3}" y="{ry+3}" width="{rw-6}" '
                 f'height="{rh-6}" fill="none" stroke="{THIN}" '
                 f'stroke-width="0.8"/>')
    parts.append(f'<rect x="{rx+rw-70}" y="{ry+rh-3}" width="54" '
                 f'height="6" fill="#ffffff" stroke="{STROKE}" '
                 f'stroke-width="1.2"/>')
    parts.append(f'<text x="{rx+rw-44}" y="{ry+rh+16}" font-size="10" '
                 f'fill="{STROKE}" text-anchor="middle">门 1000</text>')
    parts.append(f'<rect x="{rx+120}" y="{ry-3}" width="90" height="6" '
                 f'fill="#ffffff" stroke="{STROKE}" stroke-width="1.2"/>')
    parts.append(f'<text x="{rx+165}" y="{ry-8}" font-size="10" '
                 f'fill="{STROKE}" text-anchor="middle">窗 1500</text>')

    # 设备布置：综合机柜 / 蓄电池组 / 直流电源柜 / 空调
    devices = [
        (rx + 30, ry + 40, 90, 50, "综合机柜"),
        (rx + 30, ry + 120, 90, 50, "直流电源柜"),
        (rx + 160, ry + 40, 110, 42, "蓄电池组 2组"),
        (rx + 160, ry + 120, 70, 46, "空调室内机"),
        (rx + 300, ry + 40, 100, 46, "ODF 配线架"),
    ]
    for ex, ey, ew, eh, name in devices:
        parts.append(f'<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" '
                     f'fill="#e8edf2" stroke="{STROKE}" stroke-width="1.2"/>')
        parts.append(f'<text x="{ex+ew/2}" y="{ey+eh/2+4}" font-size="10" '
                     f'fill="{STROKE}" text-anchor="middle">'
                     f'{esc(name)}</text>')

    # 房间信息标注
    parts.append(f'<text x="{rx}" y="{ry-18}" font-size="12" '
                 f'fill="{STROKE}" font-weight="bold">'
                 f'{esc(room_name)}（{esc(room_type)}）</text>')
    parts.append(f'<text x="{rx}" y="{ry+rh+30}" font-size="10" '
                 f'fill="{THIN}">供电：{esc(power)}｜容量：{esc(cap_text)}'
                 f'｜设备间距≥0.8m，维护通道≥1.0m</text>')

    # 图名
    parts.append(f'<text x="{W/2}" y="{H-14}" font-size="13" '
                 f'fill="{STROKE}" text-anchor="middle" '
                 f'font-weight="bold">机房设备布置示意图</text>')
    parts.append('</svg>')
    return "".join(parts)


# ======================================================================== #
#  标准工程图册（多页 A3）：站址总平面 / 铁塔立面 / 机房布置+BOM+技术要求
# ======================================================================== #

def create_standard_engineering_sheet(
    project: QgsProject,
    sites: List,
    machine_rooms: List = None,
    pipelines: List = None,
    map_extent: QgsRectangle = None,
    title_prefix: str = "通信基站工程图册",
    output_path: str = None,
    paper_size: str = "A3",
    dpi: int = 300,
    progress_callback: Optional[callable] = None,
) -> Optional[str]:
    """生成标准多视图工程图册 PDF（三页：总平面 / 立面 / 机房布置）。

    模仿真实通信基站 CAD 三视图结构，从当前 QGIS 设计数据自动生成：
      第 1 页  站址总平面图（QGIS 地图项 + 图框 + 图衔 + 比例尺/指北针）
      第 2 页  铁塔立面图（SVG 矢量示意 + 图框 + 图衔 + 尺寸标注）
      第 3 页  机房设备布置图（SVG + 设备材料表 BOM + 技术要求 + 图衔）

    编制依据：GB 51456-2023《建筑物移动通信基础设施工程技术标准》，
    标注于每页图衔「设计依据」栏及第 3 页技术要求第一条。

    Args:
        project: QGIS 项目
        sites: Site 对象列表（至少含 1 个，取第 1 个生成立面/机房）
        machine_rooms: MachineRoom 对象列表（可选）
        pipelines: Pipeline 对象列表（预留）
        map_extent: 地图范围（第 1 页用；None 则从站点坐标估算）
        title_prefix: 图册标题前缀
        output_path: 输出 PDF 路径（None → Desktop 默认路径）
        paper_size: 纸张大小 ("A3" 或 "A4")
        dpi: 导出分辨率
        progress_callback: 进度回调 fn(pct: int, msg: str|None)

    Returns:
        输出 PDF 路径；失败返回 None。
    """
    import tempfile, os
    from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QTimer

    # ---- 参数校验 ----
    if not sites:
        print("[Engineering Sheet] 无站点数据，无法生成")
        return None
    site = sites[0]  # 取第一个站点作为主站

    temp_files = []  # 临时 SVG 文件，导出后清理
    try:

        # 进度回调（如有）：在阶段节点上报百分比与文字，便于 UI 显示"正在导出"
        def _report(pct, msg=None):
            if progress_callback is not None:
                try:
                    progress_callback(int(pct), msg)
                except Exception:
                    pass
        _report(3, "初始化图册布局…")

        # ---- 布局初始化（A3 横向） ----
        PW, PH = 420.0, 297.0  # A3 mm
        if paper_size.upper() == "A4":
            PW, PH = 297.0, 210.0

        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        try:
            size = QgsLayoutSize(PW, PH, QgsUnitTypes.LayoutMillimeters)
            layout.pageCollection().pages()[0].setPageSize(size)
        except Exception:
            pass

        # 追加第 2、3 页：QgsLayoutPageCollection 公开 API 为 addPage(QgsLayoutItemPage)
        # （不存在 appendPage(QgsLayoutSize)）。若 QGIS 不支持多页应直接抛错，
        # 不做静默降级——残缺的单页图册比报错更误导。
        for _ in range(2):
            page = QgsLayoutItemPage(layout)
            page.setPageSize(QgsLayoutSize(PW, PH, QgsUnitTypes.LayoutMillimeters))
            layout.pageCollection().addPage(page)

        num_pages = len(layout.pageCollection().pages())
        print(f"[Engineering Sheet] 创建 {num_pages} 页布局 ({PW:.0f}x{PH:.0f}mm)")

        # ---- 辅助：将 item 绑定到指定页 ----
        def bind_page(item, p):
            """用 attemptMove 的 page 参数把 item 绑定到第 p 页（p 从 0 起）。

            QgsLayoutItem 只有 page()/pagePos()，没有 setPage()；attemptMove
            带 page=p 时 QgsLayoutPoint 按页内坐标解释，且由 QGIS 自动处理
            页间间隙 spaceBetweenPages()（不能手工 y+=PH*p，会忽略间隙导致
            跨页内容错位）。调用约定：item 此前均以第 0 页坐标系完成初始
            attemptMove，故 positionWithUnits() 读回的即页内坐标。
            """
            pwu = item.positionWithUnits()
            item.attemptMove(
                QgsLayoutPoint(pwu.x(), pwu.y(), QgsUnitTypes.LayoutMillimeters),
                page=p)
            return True

        # ================================================================ #
        #  第 1 页：站址总平面图（QGIS 地图）
        # ================================================================ #
        if map_extent is None or map_extent.isEmpty():
            # 从站点坐标估算范围
            lons = [getattr(s, 'longitude', 111.0) for s in sites]
            lats = [getattr(s, 'latitude', 35.0) for s in sites]
            pad = max((max(lons) - min(lons)) * 0.15, 0.005)
            map_extent = QgsRectangle(min(lons) - pad, min(lats) - pad,
                                      max(lons) + pad, max(lats) + pad)

        # 标题
        title1 = f"{title_prefix} - 站址总平面图"
        t1 = add_title_to_layout(layout, title1,
                                 position=QPointF(20, 12), font_size=14)
        bind_page(t1, 0)

        # 地图
        m1 = add_map_to_layout(layout, map_extent,
                               map_position=QPointF(18, 50),
                               map_size=QSizeF(320, 200))
        bind_page(m1, 0)

        # 渲染等待
        try:
            from qgis.utils import iface
            if iface:
                iface.mapCanvas().refresh()
                QCoreApplication.processEvents()
                loop = QEventLoop(); QTimer.singleShot(400, loop.quit); loop.exec()
            m1.refresh()
            QCoreApplication.processEvents()
            loop2 = QEventLoop(); QTimer.singleShot(300, loop2.quit); loop2.exec()
        except Exception as e:
            print(f"[Sheet P1] render wait: {e}")

        # 图例 / 比例尺 / 指北针
        leg1 = add_legend_to_layout(layout, m1,
                                    position=QPointF(360, 55),
                                    size=QSizeF(45, 120))
        bind_page(leg1, 0)

        sb1 = add_scale_bar_to_layout(layout, m1,
                                      position=QPointF(18, 258))
        bind_page(sb1, 0)

        na1 = add_north_arrow_to_layout(layout,
                                        position=QPointF(380, 14),
                                        size=QSizeF(22, 22))
        bind_page(na1, 0)

        # 图框 + 图衔
        draw_frame(layout, page_index=0, page_width=PW, page_height=PH)
        add_title_block(layout, page_index=0, sheet_name=title1,
                        scale_text="1:100", drawing_no="0001")

        _report(25, "站址总平面图已完成，绘制铁塔立面…")

        # ================================================================ #
        #  第 2 页：铁塔立面图（SVG 矢量嵌入）
        # ================================================================ #
        if num_pages >= 2:
            tower_svg = _draw_tower_elevation_svg(site)
            fd2, svg2_path = tempfile.mkstemp(suffix="_tower.svg",
                                              prefix="eng_",
                                              dir=tempfile.gettempdir())
            with os.fdopen(fd2, "w", encoding="utf-8") as f:
                f.write(tower_svg)
            temp_files.append(svg2_path)

            title2 = f"{title_prefix} - 铁塔立面图"
            t2 = add_title_to_layout(layout, title2,
                                     position=QPointF(20, 12), font_size=14)
            bind_page(t2, 1)

            # SVG 图片项（居中放置，留出标题和图衔空间）
            pic2 = QgsLayoutItemPicture(layout)
            pic2.setPicturePath(svg2_path)
            pic2_w = min(PW - 40, 280.0)
            pic2_h = pic2_w * (470.0 / 320.0)  # 保持 tower viewBox 比例
            pic2_x = (PW - pic2_w) / 2.0
            pic2_y = 30.0
            if pic2_y + pic2_h > PH - 40:
                pic2_h = PH - 40 - pic2_y
                pic2_w = pic2_h * (320.0 / 470.0)
                pic2_x = (PW - pic2_w) / 2.0
            pic2.attemptMove(QgsLayoutPoint(pic2_x, pic2_y,
                                            QgsUnitTypes.LayoutMillimeters))
            pic2.attemptResize(QgsLayoutSize(pic2_w, pic2_h,
                                             QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(pic2)
            bind_page(pic2, 1)

            draw_frame(layout, page_index=1, page_width=PW, page_height=PH)
            add_title_block(layout, page_index=1, sheet_name=title2,
                            scale_text="1:100", drawing_no="0002")

        _report(45, "铁塔立面图已完成，绘制机房布置…")

        # ================================================================ #
        #  第 3 页：机房设备布置 + BOM 表 + 技术要求
        # ================================================================ #
        if num_pages >= 3:
            room = (machine_rooms[0] if machine_rooms else None)
            room_svg = _draw_room_layout_svg(room, site)

            fd3, svg3_path = tempfile.mkstemp(suffix="_room.svg",
                                              prefix="eng_",
                                              dir=tempfile.gettempdir())
            with os.fdopen(fd3, "w", encoding="utf-8") as f:
                f.write(room_svg)
            temp_files.append(svg3_path)

            title3 = f"{title_prefix} - 机房设备布置"
            t3 = add_title_to_layout(layout, title3,
                                     position=QPointF(20, 12), font_size=14)
            bind_page(t3, 2)

            # 房间布置 SVG（左上区域）
            pic3 = QgsLayoutItemPicture(layout)
            pic3.setPicturePath(svg3_path)
            pic3_w = min(PW * 0.58, 240.0)
            pic3_h = pic3_w * (380.0 / 520.0)  # room viewBox 比例
            pic3.attemptMove(QgsLayoutPoint(18, 46,
                                            QgsUnitTypes.LayoutMillimeters))
            pic3.attemptResize(QgsLayoutSize(pic3_w, pic3_h,
                                             QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(pic3)
            bind_page(pic3, 2)

            # BOM 表（右侧或下方）：绑到第 3 页（page=2）
            bom_pos = (QPointF(270, 46) if pic3_w < 260
                       else QPointF(18, 46 + pic3_h + 6))
            bom_sz = QSizeF(PW - bom_pos.x() - 18, 110)
            bom_pic = add_bom_table_from_site(layout, site, position=bom_pos,
                                              size=bom_sz,
                                              temp_registry=temp_files)
            if bom_pic is not None:
                bind_page(bom_pic, 2)

            # 技术要求（底部）：第一条为编制依据 GB 51456-2023。
            # 位置须避开底部图衔条带（tb_y = PH-29，高 22mm）：
            # y = PH-62 + 高 28mm → 底边距 PH-34，与图衔顶部留 ~5mm 间隙。
            # 同样绑到第 3 页（page=2）。
            tech_lbl = add_tech_requirements(
                layout, lines=list(DEFAULT_TECH_REQUIREMENTS),
                position=QPointF(18, PH - 62),
                size=QSizeF(PW - 36, 28))
            bind_page(tech_lbl, 2)

            draw_frame(layout, page_index=2, page_width=PW, page_height=PH)
            add_title_block(layout, page_index=2, sheet_name=title3,
                            scale_text="1:100", drawing_no="0003")

        _report(65, "机房布置/BOM/技术要求已完成，准备导出…")

        # ================================================================ #
        #  导出 PDF
        # ================================================================ #
        # 最终渲染等待
        layout.refresh()
        QCoreApplication.processEvents()
        final_wait = QEventLoop()
        QTimer.singleShot(600, final_wait.quit)
        final_wait.exec()

        _report(80, "图框/图衔已套用，正在导出 PDF…")

        if output_path is None:
            desktop = os.path.expanduser("~")
            safe_name = (getattr(site, "name", "") or "基站").replace("/", "-")
            output_path = os.path.join(desktop, f"{title_prefix}_{safe_name}.pdf")

        _report(95, "正在写入 PDF 文件…")
        ok, err = export_layout_to_pdf(layout, output_path, dpi=dpi)

        if ok:
            print(f"[Engineering Sheet] 导出成功: {output_path}")
            _report(100, "导出完成")
            return output_path
        else:
            print(f"[Engineering Sheet] 导出失败: {err}")
            return None
    finally:
        # 无论成功或异常均清理临时 SVG，避免 %TEMP% 泄漏
        for _p in temp_files:
            try:
                os.remove(_p)
            except OSError:
                pass
