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

import math

# ========================================================================
#  方案 B：内联矢量 SVG 生成器（逐像素还原已审核示例 v3.1 / pymupdf）
#  坐标系：viewBox="0 0 1190 842"（pt），与示例同；插件再以
#  QgsLayoutItemPicture 拉伸到 420×297mm（A3 横向）整页铺满。
#  颜色映射：pymupdf 0-1 浮点 → 十六进制（见 _C_*）。
# ========================================================================

# ---- 颜色（pymupdf 0-1 → 十六进制）----
_C_BLK = "#000000"
_C_GRY = "#e0e0e0"
_C_MID = "#8c8c8c"
_C_BLU = "#00388c"
_C_RED = "#c71414"
_C_GRN = "#007a2e"
_C_ORG = "#d16b00"
_C_LGRN = "#d1f0d6"
_C_LBLU = "#d9ebff"
_C_LYEL = "#fffad1"
_C_LRED = "#ffe0e0"

# ---- 图面常量（pt）----
_PT = 2.834645669
_A3W = 1190.0
_A3H = 842.0
_DRAW_L = 50.0
_DRAW_R = 838.0
_DRAW_T = 94.0
_DRAW_B = 792.0
_PANEL_X = 850.0
_PANEL_W = 298.0
_FX0 = 42.0
_FY0 = 42.0
_FX1 = 1148.0
_FY1 = 800.0

_SVG_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" '
             'viewBox="0 0 1190 842">'
             '<rect width="1190" height="842" fill="#ffffff"/>')


def _esc(s):
    """XML 文本转义：& < >。"""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _f(v):
    """数值格式化：整数去小数，否则保留两位小数。"""
    v = float(v)
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    return f"{v:.2f}"


def _svg_rect(x0, y0, x1, y1, w=0.8, fill="none", color=_C_BLK, dash=None):
    d = f' stroke-dasharray="{dash} {dash}"' if dash else ""
    return (f'<rect x="{_f(x0)}" y="{_f(y0)}" width="{_f(x1 - x0)}" '
            f'height="{_f(y1 - y0)}" fill="{fill}" stroke="{color}" '
            f'stroke-width="{w}"{d}/>')


def _svg_line(x0, y0, x1, y1, w=0.7, color=_C_BLK, dash=None):
    d = f' stroke-dasharray="{dash} {dash}"' if dash else ""
    return (f'<line x1="{_f(x0)}" y1="{_f(y0)}" x2="{_f(x1)}" y2="{_f(y1)}" '
            f'stroke="{color}" stroke-width="{w}"{d}/>')


def _svg_text(x, y, s, fs=9, color=_C_BLK, bold=False, family=None):
    fam = family or "'SimSun',sans-serif"
    b = ' font-weight="bold"' if bold else ""
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-size="{fs}" fill="{color}" '
            f'font-family="{fam}"{b}>{_esc(s)}</text>')


def _svg_ctext(cx, cy, s, fs=9, color=_C_BLK, bold=False, family=None):
    fam = family or "'SimHei','SimSun',sans-serif"
    b = ' font-weight="bold"' if bold else ""
    return (f'<text x="{_f(cx)}" y="{_f(cy)}" font-size="{fs}" fill="{color}" '
            f'text-anchor="middle" font-family="{fam}"{b}>{_esc(s)}</text>')


def _svg_arr_head(x, y, ang, size=5, color=_C_BLK):
    """实心三角箭头：顶点 (x,y)，方向 ang（弧度）。"""
    bx = x - size * math.cos(ang)
    by = y - size * math.sin(ang)
    px = -math.sin(ang)
    py = math.cos(ang)
    b1x, b1y = bx + px * size * 0.5, by + py * size * 0.5
    b2x, b2y = bx - px * size * 0.5, by - py * size * 0.5
    return (f'<polygon points="{_f(x)},{_f(y)} {_f(b1x)},{_f(b1y)} '
            f'{_f(b2x)},{_f(b2y)}" fill="{color}" stroke="{color}" '
            f'stroke-width="0.5"/>')


def _svg_circle(cx, cy, r, color=_C_BLK, w=1.0, fill="none"):
    return (f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="{fill}" '
            f'stroke="{color}" stroke-width="{w}"/>')


def _svg_polyline(pts, color=_C_BLK, w=1.0, dash=None, fill="none"):
    coord = " ".join(f"{_f(x)},{_f(y)}" for x, y in pts)
    d = f' stroke-dasharray="{dash} {dash}"' if dash else ""
    return (f'<polyline points="{coord}" fill="{fill}" stroke="{color}" '
            f'stroke-width="{w}"{d}/>')


def _svg_frame(fig_no, name, scale_text):
    """外框 + 内框 + 居中图名 + 右下图衔（8 文字项）。"""
    parts = []
    parts.append(_svg_rect(34, 34, _A3W - 34, _A3H - 34, 1.6, fill="none", color=_C_BLK))
    parts.append(_svg_rect(_FX0, _FY0, _FX1, _FY1, 0.6, fill="none", color=_C_BLK))
    parts.append(_svg_ctext(_A3W / 2, 62, f"图{fig_no} {name}", 16, _C_BLU, bold=True))
    tb_x0 = _FX1 - 480
    tb_y0 = _FY1 - 82
    tb_w = 480.0
    tb_h = 82.0
    parts.append(_svg_rect(tb_x0, tb_y0, tb_x0 + tb_w, tb_y0 + tb_h, 1.0,
                           fill="none", color=_C_BLK))
    for cx in (tb_x0 + 120, tb_x0 + 240, tb_x0 + 360):
        parts.append(_svg_line(cx, tb_y0, cx, tb_y0 + tb_h, 0.6, _C_MID))
    parts.append(_svg_line(tb_x0, tb_y0 + tb_h / 2, tb_x0 + tb_w, tb_y0 + tb_h / 2,
                           0.6, _C_MID))
    top = [("图名", name), ("图号", f"ENG-{fig_no:02d}"),
           ("比例", scale_text), ("设计单位", "示例通信设计院")]
    bot = [("", "设计:____  审核:____"), ("", "日期:2026-09"),
           ("", f"第{fig_no}张 共3张"), ("", "设计依据:GB 51456-2023")]
    for i, (lab, val) in enumerate(top):
        cx = tb_x0 + 120 * i
        if lab:
            parts.append(_svg_text(cx + 4, tb_y0 + 14, lab, 7, _C_BLU, bold=True))
        parts.append(_svg_text(cx + 4, tb_y0 + 30, val, 9, _C_BLK))
    for i, (lab, val) in enumerate(bot):
        cx = tb_x0 + 120 * i
        parts.append(_svg_text(cx + 4, tb_y0 + tb_h / 2 + 16, val, 8, _C_BLK))
    return "".join(parts)


def _svg_north(cx, cy):
    """指北针：圆 + 向上箭头 + N + 指北针。"""
    parts = []
    parts.append(_svg_circle(cx, cy, 24, _C_BLK, 1.0))
    tip_y = cy - 20
    parts.append(_svg_line(cx, cy + 18, cx, tip_y, 1.2, _C_BLK))
    parts.append(_svg_arr_head(cx, tip_y, -math.pi / 2, 7, _C_BLK))
    parts.append(_svg_text(cx - 5, cy - 37, "N", 11, _C_BLK))
    parts.append(_svg_text(cx - 13, cy + 32, "指北针", 7, _C_MID))
    return "".join(parts)


def _svg_scalebar(x, y, per_mm, unit_m=500, ratio_label="1:500", panel_right=_FX1):
    """4 段黑白条比例尺 + 刻度文字 + 比例尺说明。"""
    parts = []
    avail = (panel_right - x) - 8
    seg = unit_m * per_mm
    if seg <= 0:
        seg = 22.0
    if seg < 22:
        seg = 22.0
    if 4 * seg > avail:
        seg = avail / 4.0
    h = 7.0
    for i in range(4):
        sx = x + i * seg
        fill = _C_BLK if i % 2 == 0 else "#ffffff"
        parts.append(_svg_rect(sx, y, sx + seg, y + h, 0.5, fill=fill, color=_C_BLK))
    for i in range(5):
        parts.append(_svg_text(x + i * seg, y + h + 10, f"{i * unit_m}", 7, _C_MID))
    parts.append(_svg_text(x, y + h + 24, f"比例尺 {ratio_label}", 8, _C_BLK, bold=True))
    return "".join(parts)


def _svg_legend(x, y, w, h, items):
    """图例框 + 标题 + 逐项（色块 + 文字）。items: [(label, color), ...]"""
    parts = [_svg_rect(x, y, x + w, y + h, 0.8, fill="none", color=_C_BLK),
             _svg_text(x + 6, y + 15, "图  例", 9, _C_BLU, bold=True)]
    yy = y + 33
    for label, color in items:
        parts.append(_svg_rect(x + 8, yy - 7, x + 20, yy + 1, 0.5,
                               fill=color, color=_C_BLK))
        parts.append(_svg_text(x + 26, yy, label, 8, _C_BLK))
        yy += 17
    return "".join(parts)


def _svg_tech_notes(x, y, w, lines):
    """技术要求框 + 标题 + 编号列表。"""
    h = 34 + len(lines) * 15 + 8
    parts = [_svg_rect(x, y, x + w, y + h, 0.8, fill="none", color=_C_BLK),
             _svg_text(x + 7, y + 16, "技术要求", 9, _C_BLU, bold=True)]
    for i, line in enumerate(lines):
        parts.append(_svg_text(x + 9, y + 34 + i * 15, f"{i + 1}. {line}", 7.5, _C_BLK))
    return "".join(parts)


def _svg_device_table(x, y, w, rows):
    """设备表框 + 三列（名称/规格/数量）。rows: [(name, spec, qty), ...]"""
    h = 34 + (len(rows) + 1) * 17 + 6
    parts = [_svg_rect(x, y, x + w, y + h, 0.8, fill="none", color=_C_BLK),
             _svg_text(x + 6, y + 16, "设备表", 9, _C_BLU, bold=True)]
    c0, c1, c2, c3 = x, x + w * 0.30, x + w * 0.70, x + w
    parts.append(_svg_line(c0, y + 30, c3, y + 30, 0.6, _C_MID))
    parts.append(_svg_text(c0 + 4, y + 26, "名称", 8, _C_BLK, bold=True))
    parts.append(_svg_text(c1 + 4, y + 26, "规格", 8, _C_BLK, bold=True))
    parts.append(_svg_text(c2 + 4, y + 26, "数量", 8, _C_BLK, bold=True))
    for i, (nm, spec, qty) in enumerate(rows):
        ry = y + 30 + (i + 1) * 17
        parts.append(_svg_line(c0, ry, c3, ry, 0.4, _C_MID))
        parts.append(_svg_text(c0 + 4, ry - 5, nm, 7.5, _C_BLK))
        parts.append(_svg_text(c1 + 4, ry - 5, spec, 7.5, _C_BLK))
        parts.append(_svg_text(c2 + 4, ry - 5, qty, 7.5, _C_BLK))
    parts.append(_svg_line(c1, y + 30, c1, y + h, 0.4, _C_MID))
    parts.append(_svg_line(c2, y + 30, c2, y + h, 0.4, _C_MID))
    return "".join(parts)


def _svg_dim_h(x0, x1, y, label, ext=14, fs=7.5):
    """水平尺寸线 + 双箭头 + 中间文字。"""
    return "".join([
        _svg_line(x0, y, x1, y, 0.5, _C_BLK),
        _svg_line(x0, y - ext, x0, y + ext, 0.4, _C_MID),
        _svg_line(x1, y - ext, x1, y + ext, 0.4, _C_MID),
        _svg_arr_head(x0, y, 0.0, 4, _C_BLK),
        _svg_arr_head(x1, y, math.pi, 4, _C_BLK),
        _svg_ctext((x0 + x1) / 2, y - fs, label, fs, _C_BLK),
    ])


def _svg_dim_v(y0, y1, x, label, ext=14, fs=7.5):
    """垂直尺寸线 + 双箭头 + 左侧文字。"""
    return "".join([
        _svg_line(x, y0, x, y1, 0.5, _C_BLK),
        _svg_line(x - ext, y0, x + ext, y0, 0.4, _C_MID),
        _svg_line(x - ext, y1, x + ext, y1, 0.4, _C_MID),
        _svg_arr_head(x, y0, -math.pi / 2, 4, _C_BLK),
        _svg_arr_head(x, y1, math.pi / 2, 4, _C_BLK),
        _svg_ctext(x - fs, (y0 + y1) / 2, label, fs, _C_BLK),
    ])


def _draw_page1_site_plan_svg(site) -> str:
    """站址总平面定位图（1:500）整页 SVG。坐标系 viewBox 1190×842(pt)。"""
    name = getattr(site, "name", "") or "基站"
    K = _PT / 500.0
    parts = [_SVG_HEAD]

    # 征地红线（红虚线框）+ 四角十字
    sw = 130000.0 * K
    sh = 95000.0 * K
    dcx = (_DRAW_L + _DRAW_R) / 2.0
    dcy = (_DRAW_T + _DRAW_B) / 2.0
    sx = dcx - sw / 2.0
    sy = dcy - sh / 2.0
    parts.append(_svg_rect(sx, sy, sx + sw, sy + sh, 1.2, fill="none",
                           color=_C_RED, dash=6))
    for (cx, cy) in ((sx, sy), (sx + sw, sy), (sx, sy + sh), (sx + sw, sy + sh)):
        parts.append(_svg_line(cx - 6, cy, cx + 6, cy, 0.8, _C_RED))
        parts.append(_svg_line(cx, cy - 6, cx, cy + 6, 0.8, _C_RED))
    parts.append(_svg_text(sx + 4, sy - 4, "征地红线 / 院落围墙", 8, _C_RED))

    # 通信机房灰块
    bww = 12000.0 * K
    bhh = 7000.0 * K
    bx = sx + sw * 0.30
    by = sy + sh * 0.38
    parts.append(_svg_rect(bx, by, bx + bww, by + bhh, 1.0, fill=_C_GRY, color=_C_BLK))
    parts.append(_svg_ctext(bx + bww / 2, by + bhh / 2 + 3, "通信机房", 8, _C_BLK))

    # 三管塔（简化三角塔身 + 平台 + 3 面天线）
    tx = dcx
    ty_base = sy + sh * 0.62
    tower_h_pt = 90.0
    top_y = ty_base - tower_h_pt
    plat_y = top_y + 24.0
    half_b = 14.0
    half_t = 3.0
    parts.append(
        f'<polygon points="{_f(tx - half_b)},{_f(ty_base)} '
        f'{_f(tx + half_b)},{_f(ty_base)} {_f(tx + half_t)},{_f(top_y)} '
        f'{_f(tx - half_t)},{_f(top_y)}" fill="#f4f6f8" '
        f'stroke="{_C_BLK}" stroke-width="1.4"/>')
    plat_half = 16.0
    parts.append(_svg_line(tx - plat_half, plat_y, tx + plat_half, plat_y, 1.6, _C_BLK))
    for ax, ah in ((tx - 12, 26.0), (tx + 6, 26.0), (tx - 3, 22.0)):
        parts.append(_svg_rect(ax, plat_y - ah, ax + 6, plat_y, 1.0,
                               fill=_C_LBLU, color=_C_BLU))
    parts.append(_svg_text(tx + plat_half + 4, plat_y, "天线", 7.5, _C_BLU))
    parts.append(_svg_text(tx + half_b + 4, top_y + 10, "三管塔 H=35m", 8, _C_BLK, bold=True))

    # 人孔/手孔 + 通信管道（橙色）
    man_x = sx + sw * 0.12
    man_y = sy + sh * 0.75
    parts.append(_svg_rect(man_x, man_y, man_x + 10, man_y + 10, 1.0, fill=_C_GRY, color=_C_BLK))
    parts.append(_svg_rect(man_x + 20, man_y + 6, man_x + 30, man_y + 16, 1.0, fill=_C_GRY, color=_C_BLK))
    parts.append(_svg_polyline([(man_x + 10, man_y + 5), (man_x + 20, man_y + 11),
                                (tx - half_b, ty_base)], _C_ORG, 1.2))
    parts.append(_svg_text(man_x, man_y + 24, "通信管道 4孔Φ110(第7.3.2条)", 7.5, _C_ORG))

    # 市电接入点（圆）+ 红虚线外市电引入
    pw_x = sx + sw * 0.82
    pw_y = sy + sh * 0.30
    parts.append(_svg_circle(pw_x, pw_y, 8, _C_RED, 1.2))
    parts.append(_svg_polyline([(pw_x, pw_y), (tx + half_b, ty_base)], _C_RED, 1.2, dash=5))
    parts.append(_svg_text(pw_x + 12, pw_y, "外市电引入(独立回路 第6.1.1条)", 7.5, _C_RED))

    # 周边建筑 4 个（浅灰，v3.1 风格）
    _bldg_fill = "#f5f5f5"
    for nm, ex, ey, ew, eh in (
        ("办公楼", sx + 20, sy + 20, 60, 36),
        ("仓库", sx + sw - 90, sy + 24, 70, 30),
        ("居民楼", sx + 30, sy + sh - 70, 50, 46),
        ("配电房", sx + sw - 80, sy + sh - 60, 60, 40),
    ):
        parts.append(_svg_rect(ex, ey, ex + ew, ey + eh, 1.0,
                               fill=_bldg_fill, color=_C_BLK))
        parts.append(_svg_ctext(ex + ew / 2, ey + eh / 2 + 3, nm, 7.5, _C_BLK))

    # 道路 2 条（红线外上/下，v3.1 风格：灰路面 + 白虚线中心线）
    _road = "#b8b8b8"
    parts.append(_svg_line(sx - 10, sy - 38, sx + sw + 10, sy - 38, 8.0, _road))
    parts.append(_svg_line(sx - 10, sy - 38, sx + sw + 10, sy - 38, 8.0,
                           "#ffffff", dash=12))
    parts.append(_svg_text(sx - 5, sy - 46, "城市主干道", 7.5, _C_MID))
    parts.append(_svg_line(sx - 10, sy + sh + 70, min(sx + sw + 10, 658.0),
                           sy + sh + 70, 8.0, _road))
    parts.append(_svg_line(sx - 10, sy + sh + 70, min(sx + sw + 10, 658.0),
                           sy + sh + 70, 8.0, "#ffffff", dash=12))
    parts.append(_svg_text(sx - 5, sy + sh + 62, "规划道路", 7.5, _C_MID))

    # 绿地
    gx = sx + sw * 0.55
    gy = sy + sh * 0.10
    parts.append(_svg_rect(gx, gy, gx + 50, gy + 36, 1.0, fill=_C_LGRN, color=_C_GRN))
    parts.append(_svg_ctext(gx + 25, gy + 20, "绿地", 7.5, _C_GRN))

    # 坐标注记（红线框下方 8pt，v3.1 位置）
    parts.append(_svg_text(sx, sy + sh + 10,
                           "坐标注记(CGCS2000,示意): 塔位 X=4 365 210.123 "
                           "Y=398 115.456", 7.5, _C_MID))

    # 右侧面板：指北针 / 比例尺 / 图例 / 技术要求
    px = _PANEL_X + 8
    parts.append(_svg_north(px + 100, _DRAW_T + 10))
    parts.append(_svg_scalebar(px + 65, _DRAW_T + 60, K, unit_m=50, ratio_label="1:500"))
    legend_items = [
        ("征地红线(围墙)", _C_RED), ("通信机房", _C_GRY), ("三管塔天线", _C_LBLU),
        ("通信管道4孔Φ110", _C_ORG), ("外市电引入", _C_RED), ("人孔手孔", _C_GRY),
        ("周边建筑", "#f5f5f5"), ("城市道路", _C_MID), ("绿地", _C_LGRN),
    ]
    parts.append(_svg_legend(px, _DRAW_T + 105, _PANEL_W - 16, 175, legend_items))
    tech = [
        "比例1:500；",
        "塔位不设于管线区域上方(第5.3.2条)；",
        "就近预留通信管道(第5.3.4条)，室外≥4孔外径≥110mm(第7.3.2条)；",
        "埋深≥0.8m净距≥0.5m；",
        "外市电独立回路(第6.1.1条)；机房防雷接地(第4.1.12条)。",
    ]
    parts.append(_svg_tech_notes(px, _DRAW_T + 295, _PANEL_W - 16, tech))

    # 图框 + 图衔
    parts.append(_svg_frame(1, f"{name} 站址总平面定位图", "1:500"))
    parts.append("</svg>")
    return "".join(parts)


def _draw_page2_tower_elevation_svg(site) -> str:
    """铁塔立面图（1:200）整页 SVG。"""
    name = getattr(site, "name", "") or "基站"
    tower_type = str(getattr(site, "tower_type", "MONOPOLE") or "MONOPOLE")
    tower_h = float(getattr(site, "tower_height", 35.0) or 35.0)
    K = _PT / 200.0
    M = lambda m: m * K
    parts = [_SVG_HEAD]

    ground_y = 660.0
    cx = 300.0

    # 室外地面线 + 斜填土
    parts.append(_svg_line(_DRAW_L, ground_y, _DRAW_R, ground_y, 1.6, _C_BLK))
    gx = _DRAW_L + 8
    while gx < _DRAW_R:
        parts.append(_svg_line(gx, ground_y, gx - 6, ground_y + 7, 0.6, _C_MID))
        gx += 12

    # C25 基础块
    fnd_w = M(4000)
    fnd_h = M(800)
    fnd_x = cx - fnd_w / 2
    parts.append(_svg_rect(fnd_x, ground_y, fnd_x + fnd_w, ground_y + fnd_h, 1.0,
                           fill=_C_GRY, color=_C_BLK))
    parts.append(_svg_ctext(cx, ground_y + fnd_h / 2 + 3, "C25 基础", 7.5, _C_BLK))

    # 塔身腿收分 + 分段横线（8 段）
    base_half = M(2200) if tower_type == "LATTICE" else M(1900)
    top_half = M(400)
    top_y = ground_y - M(33000)
    lb, rb = cx - base_half, cx + base_half
    lt, rt = cx - top_half, cx + top_half
    parts.append(
        f'<polygon points="{_f(lb)},{_f(ground_y)} {_f(rb)},{_f(ground_y)} '
        f'{_f(rt)},{_f(top_y)} {_f(lt)},{_f(top_y)}" fill="#f4f6f8" '
        f'stroke="{_C_BLK}" stroke-width="1.4"/>')
    segs = 8
    for i in range(1, segs):
        t = i / segs
        y = ground_y + (top_y - ground_y) * t
        xl = lb + (lt - lb) * t
        xr = rb + (rt - rb) * t
        if i % 2 == 1:
            parts.append(_svg_line(xl, y, xr, y - (ground_y - top_y) / segs, 0.6, _C_MID))
        else:
            parts.append(_svg_line(xl, y, xr, y, 0.6, _C_MID))

    # 竖向刻度（每 500）
    for mm in range(0, 33000, 500):
        yk = ground_y - M(mm)
        parts.append(_svg_line(cx + top_half + 2, yk, cx + top_half + 8, yk, 0.5, _C_MID))

    # 平台 + 护栏
    plat_y2 = ground_y - M(29000)
    plat_half2 = M(1900)
    parts.append(_svg_line(cx - plat_half2, plat_y2, cx + plat_half2, plat_y2, 1.8, _C_BLK))
    parts.append(_svg_rect(cx - plat_half2, plat_y2, cx + plat_half2, plat_y2 + 4,
                           0.8, fill=_C_GRY, color=_C_BLK))

    # 3 面天线（蓝块）+ 竖向引线
    ant_y2 = ground_y - M(32000)
    parts.append(_svg_line(cx, ant_y2, cx, plat_y2, 1.0, _C_BLU))
    for ax, ah in ((cx - plat_half2 * 0.7, 30.0), (cx + plat_half2 * 0.2, 30.0),
                   (cx - plat_half2 * 0.25, 26.0)):
        parts.append(_svg_rect(ax, ant_y2 - ah, ax + 8, ant_y2, 1.0,
                               fill=_C_LBLU, color=_C_BLU))
    parts.append(_svg_text(cx + plat_half2 + 4, ant_y2 - 10, "天线(3面)", 7.5, _C_BLU))

    # 避雷针
    tip_y = top_y - M(1500)
    parts.append(_svg_line(cx, top_y, cx, tip_y, 1.2, _C_BLK))
    parts.append(_svg_arr_head(cx, tip_y, -math.pi / 2, 6, _C_BLK))
    parts.append(_svg_text(cx + 6, tip_y, "避雷针", 8, _C_BLK))

    # 左侧垂直尺寸 H
    parts.append(_svg_dim_v(ground_y, top_y, cx - base_half - 18, f"H={tower_h:.0f}m"))

    # 平台/天线挂高标注（虚线到 640）
    parts.append(_svg_line(_DRAW_L + 6, plat_y2, 640, plat_y2, 0.8, _C_BLK, dash=4))
    parts.append(_svg_text(_DRAW_L + 8, plat_y2 - 4, "平台挂高", 7.5, _C_BLK))
    parts.append(_svg_line(_DRAW_L + 6, ant_y2, 640, ant_y2, 0.8, _C_BLK, dash=4))
    parts.append(_svg_text(_DRAW_L + 8, ant_y2 - 4, "天线挂高", 7.5, _C_BLK))

    # 底部说明 + 左上标题
    parts.append(_svg_text(_DRAW_L, ground_y + 30,
                           "塔位平面定位见图1；基础配筋另详结构图(第5.1.2条)", 8, _C_BLK))
    parts.append(_svg_text(_DRAW_L, _DRAW_T + 6,
                           f"三管塔 H={tower_h:.0f}m(立面示意)", 10, _C_BLK, bold=True))

    # 右侧面板：图例 / 技术要求
    px = _PANEL_X + 8
    legend_items = [
        ("塔身", "#f4f6f8"), ("平台+护栏", _C_GRY), ("天线3面", _C_LBLU),
        ("避雷针", _C_BLK), ("爬梯", _C_MID), ("室外地面线", _C_BLK),
    ]
    parts.append(_svg_legend(px, _DRAW_T + 8, _PANEL_W - 16, 130, legend_items))
    tech = [
        "比例1:200；",
        "结构安全等级不低于二级(第3.0.5条)；支承可靠连接(第5.1.2条)；",
        "地脚螺栓预埋(第5.1.2条)；",
        "塔位不设于管线区域上方(第5.3.2条)；",
        "就近预留通信管道(第5.3.4条)；",
        "塔顶避雷针接地机房防雷(第4.1.12条)。",
    ]
    parts.append(_svg_tech_notes(px, _DRAW_T + 140, _PANEL_W - 16, tech))

    parts.append(_svg_frame(2, f"{name} 铁塔立面图", "1:200"))
    parts.append("</svg>")
    return "".join(parts)


def _draw_page3_room_layout_svg(room, site) -> str:
    """机房设备布置图（1:25）整页 SVG。room 为 None 时按通用机房。"""
    name = getattr(site, "name", "") or "基站"
    room_name = (str(getattr(room, "name", "") or f"{name}机房")
                 if room else f"{name}机房")
    K = _PT / 25.0
    M = lambda m: m * K
    parts = [_SVG_HEAD]

    rw = M(6000)
    rh = M(4000)
    wl = M(240)
    rx = (_DRAW_L + _DRAW_R) / 2.0 - rw / 2.0
    ry = (_DRAW_T + _DRAW_B) / 2.0 - rh / 2.0

    # 外墙 + 内墙（v3.1 白墙双线框，无填充）
    parts.append(_svg_rect(rx - wl, ry - wl, rx + rw + wl, ry + rh + wl, 1.6,
                           fill="none", color=_C_BLK))
    parts.append(_svg_rect(rx, ry, rx + rw, ry + rh, 1.4, fill="none", color=_C_BLK))

    # 防静电地板点阵
    dx = M(600)
    dy = M(600)
    yy = ry + dy
    while yy < ry + rh - dy / 2:
        xx = rx + dx
        while xx < rx + rw - dx / 2:
            parts.append(_svg_circle(xx, yy, 0.8, _C_MID, 0.4))
            xx += dx
        yy += dy

    # 走线架贴墙（上走线）
    tr_y = ry + M(100)
    tr_w = M(400)
    parts.append(_svg_rect(rx + M(200), tr_y, rx + rw - M(200), tr_y + M(60), 1.0,
                           fill=_C_GRY, color=_C_BLK))
    parts.append(_svg_ctext(rx + rw / 2, tr_y + M(30), "走线架(上走线,宽400)", 7.5, _C_BLK))

    def cab(xx_mm, yy_mm, w_mm, h_mm, label, fill=_C_GRY):
        ex = rx + xx_mm * K
        ey = ry + yy_mm * K
        ew = w_mm * K
        eh = h_mm * K
        parts.append(_svg_rect(ex, ey, ex + ew, ey + eh, 1.0, fill=fill, color=_C_BLK))
        parts.append(_svg_ctext(ex + ew / 2, ey + eh / 2 + 3, label, 7, _C_BLK))

    for xx in (400, 1200, 2000, 2800, 3600):
        cab(xx, 650, 600, 600, "综合机柜")
    cab(4400, 650, 1200, 500, "蓄电池组(2组)", fill=_C_LYEL)
    cab(400, 3000, 600, 600, "直流电源柜")
    cab(1300, 3000, 600, 450, "ODF")
    cab(2200, 3000, 600, 400, "空调室内机")
    cab(4400, 3000, 500, 400, "交流配电箱")
    cab(2400, 3800, 300, 150, "接地铜排", _C_LGRN)

    # 馈线洞（上墙，黑块）
    fw_x = rx + M(2400)
    fw_s = M(400)
    parts.append(_svg_rect(fw_x, ry - fw_s / 2, fw_x + fw_s, ry + fw_s / 2, 1.2,
                           fill=_C_BLK, color=_C_BLK))
    parts.append(_svg_text(fw_x, ry - fw_s / 2 - 4, "馈线洞400×400 防雨盖板(第4.2.4条)", 7.5, _C_BLK))

    # 馈线路由（橙色）：馈线洞 → spine_y 水平 → 各机柜竖直引下
    spine_y = ry + M(300)
    parts.append(_svg_line(fw_x + fw_s / 2, ry, fw_x + fw_s / 2, spine_y, 1.2, _C_ORG))
    parts.append(_svg_line(fw_x + fw_s / 2, spine_y, rx + rw - M(200), spine_y, 1.2, _C_ORG))
    for xx in (400, 1200, 2000, 2800, 3600):
        cxp = rx + xx * K + 600 * K / 2
        parts.append(_svg_line(cxp, spine_y, cxp, ry + 650 * K, 1.2, _C_ORG))

    # 电力电缆（红色虚线）
    parts.append(_svg_polyline([(rx + 4400 * K + 250 * K, ry + 3000 * K),
                                (rx + 4400 * K + 250 * K, ry + 3800 * K),
                                (rx + 2400 * K + 150 * K, ry + 3800 * K)],
                               _C_RED, 1.2, dash=5))
    parts.append(_svg_text(rx + 4400 * K, ry + 3000 * K - 4, "电力电缆(独立回路 第6.3.1条)", 7, _C_RED))

    # 接地线（绿色虚线）
    parts.append(_svg_polyline([(rx + 2400 * K + 150 * K, ry + 3800 * K),
                                (rx + 2400 * K + 150 * K, ry + 4000 * K - M(100))],
                               _C_GRN, 1.2, dash=5))
    parts.append(_svg_text(rx + 2400 * K, ry + 3800 * K + 10, "接地线", 7, _C_GRN))

    # 门（乙级防火门，下墙）+ 开启弧（蓝色，v3.1 风格）
    door_w = M(1000)
    door_x = rx + rw / 2 - door_w / 2
    parts.append(_svg_rect(door_x, ry + rh, door_x + door_w, ry + rh + wl, 1.2,
                           fill="none", color=_C_BLU))
    parts.append(
        f'<path d="M {_f(door_x)} {_f(ry + rh)} A {_f(door_w)} {_f(door_w)} '
        f'0 0 1 {_f(door_x + door_w)} {_f(ry + rh)}" fill="none" '
        f'stroke="{_C_BLU}" stroke-width="0.6"/>')
    parts.append(_svg_text(door_x + door_w / 2, ry + rh + wl + 12,
                           "乙级防火门 1000(第4.1.8条)", 7.5, _C_BLU))

    # 预留空调室外机位（下墙左下方图框内，虚线框，v3.1 位置语义）
    oaw_x = rx + M(200)
    oaw_y = ry + rh + wl + 24
    parts.append(_svg_rect(oaw_x, oaw_y, oaw_x + M(900), oaw_y + M(550), 1.0,
                           fill="none", color=_C_MID, dash=5))
    parts.append(_svg_text(oaw_x + 6, oaw_y + M(230), "预留空调室外机位", 6.8, _C_MID))
    parts.append(_svg_text(oaw_x + 6, oaw_y + M(230) + 10, "(第4.1.9条)", 6.8, _C_MID))

    # 尺寸标注 6000 / 4000
    parts.append(_svg_dim_h(rx, rx + rw, ry - wl - 14, "6000"))
    parts.append(_svg_dim_v(ry, ry + rh, rx - wl - 14, "4000"))
    parts.append(_svg_text(rx + 8, ry + rh + wl + 14, "维护通道≥800(正面)", 8, _C_BLK))
    parts.append(_svg_text(rx, ry - wl - 28, f"{room_name}（机房设备布置图）", 11, _C_BLK, bold=True))

    # 右侧面板：比例尺 / 设备表 / 技术要求
    px = _PANEL_X + 8
    parts.append(_svg_scalebar(px + 65, _DRAW_T + 8, K, unit_m=500, ratio_label="1:25"))
    device_rows = [
        ("综合机柜", "600×600×2200", "5台"),
        ("蓄电池组", "2V/500Ah×24", "2组"),
        ("直流电源柜", "-48V", "1台"),
        ("ODF配线架", "24芯", "1架"),
        ("交流配电箱", "含ATS", "1台"),
        ("柜式空调", "5kW", "1台"),
        ("接地铜排", "L40×4", "1条"),
        ("走线架", "宽400", "1批"),
        ("馈线洞", "400×400", "1个"),
    ]
    parts.append(_svg_device_table(px, _DRAW_T + 52, _PANEL_W - 16, device_rows))
    tech = [
        "机房净面积≥20m²净宽≥3m(第4.2.2条)；",
        "乙级防火门向疏散开启(第4.1.8条)；",
        "馈线洞400×400防雨盖板(第4.2.4条)；",
        "预留空调室外机位(第4.1.9条)；防雷接地(第4.1.12条)；",
        "市电≥50kW(第6.2.1条)；独立交流配电箱(第6.2.2条)；",
        "正面维护通道≥800mm设备可靠接地。",
    ]
    ty = _DRAW_T + 52 + 24 + 10 * 17 + 4 + 12
    parts.append(_svg_tech_notes(px, ty, _PANEL_W - 16, tech))

    parts.append(_svg_frame(3, f"{name} 机房设备布置图", "1:25"))
    parts.append("</svg>")
    return "".join(parts)


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

    方案 B（矢量重绘）：三页均为整页内联矢量 SVG（QgsLayoutItemPicture
    铺满页面），不使用 QGIS 地图/图例/比例尺/指北针项：
      第 1 页  站址总平面定位图（1:500 矢量示意）
      第 2 页  铁塔立面图（1:200 矢量示意）
      第 3 页  机房设备布置图（1:25，设备表与技术要求内嵌于 SVG）

    编制依据：GB 51456-2023《建筑物移动通信基础设施工程技术标准》，
    标注于每页图衔「设计依据」栏及各页技术要求。

    Args:
        project: QGIS 项目
        sites: Site 对象列表（至少含 1 个，取第 1 个生成三页内容）
        machine_rooms: MachineRoom 对象列表（可选，取第 1 个）
        pipelines: 预留参数（当前未使用）
        map_extent: 预留参数（方案 B 起第 1 页不再使用地图项，仅为
                    兼容旧调用签名保留）
        title_prefix: 图册标题前缀
        output_path: 输出 PDF 路径（None → Desktop 默认路径）
        paper_size: 纸张大小（"A3" 或 "A4"，SVG 按页面等比缩放）
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
        if num_pages < 3:
            # 三页缺一不可（缺页会导致多张整页图叠加在同一页），
            # 直接报错优于静默产出残缺图册
            raise RuntimeError(
                f"图册布局创建失败：需要 3 页，实际 {num_pages} 页"
                f"（QGIS QgsLayoutItemPage.addPage 未生效）")

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
        #  方案 B：三页全部为内联矢量 SVG（整页铺满 420×297mm 的
        #  QgsLayoutItemPicture），不调用 QGIS 地图/图例/比例尺/指北针。
        #  与已审核示例（pymupdf v3.1）逐元素 1:1 对应，详见 _draw_page*_svg。
        # ================================================================ #
        room = (machine_rooms[0] if machine_rooms else None)

        pages_spec = [
            (0, _draw_page1_site_plan_svg(site)),
            (1, _draw_page2_tower_elevation_svg(site)),
            (2, _draw_page3_room_layout_svg(room, site)),
        ]
        for p, svg_str in pages_spec:
            fd, path = tempfile.mkstemp(suffix=".svg", prefix="eng_",
                                        dir=tempfile.gettempdir())
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(svg_str)
            temp_files.append(path)

            # 整页铺满的图片项（A3 横向 420×297mm）
            pic = QgsLayoutItemPicture(layout)
            pic.setPicturePath(path)
            pic.attemptMove(QgsLayoutPoint(0, 0, QgsUnitTypes.LayoutMillimeters),
                            page=p)
            pic.attemptResize(QgsLayoutSize(PW, PH, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(pic)
            bind_page(pic, p)

        _report(60, "三页矢量图已生成，准备导出…")

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
