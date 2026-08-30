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
    QgsLayoutItemShape, QgsLayoutItemMapGrid,
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
            txt.setFont(QFont("SimSun", 7.5))
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
