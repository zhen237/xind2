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

    # ── 先构造最终范围（供 CRS 坐标校验与后续 setExtent 复用） ──
    final_extent = QgsRectangle(map_extent)
    extent_set = False
    if not final_extent.isEmpty():
        final_extent = final_extent.buffered(final_extent.width() * 0.02)

    # ── 设置地图项 CRS（智能检测：PRJ 可能撒谎） ──
    # 常见坑：.prj 声称 EPSG:4326 但坐标值是投影网格（如 Lambert93 的 -950000/3920000）。
    # 若 CRS 声称 4326 但坐标超出经纬度合法范围，则不强制设 CRS，
    # 让 QGIS 按图层原生坐标系渲染（或使用工程 CRS）。
    target_crs = None
    if layer_crs and layer_crs.isValid() and layer_crs.authid():
        authid = layer_crs.authid()
        coord_ok = True
        if '4326' in authid or 'wgs84' in authid.lower():
            # 验证坐标是否真的在 WGS84 合法范围内（仅在范围有效时校验）
            if not final_extent.isEmpty():
                xmin, ymin = final_extent.xMinimum(), final_extent.yMinimum()
                xmax, ymax = final_extent.xMaximum(), final_extent.yMaximum()
                if (xmin < -360 or xmax > 360 or ymin < -90 or ymax > 90):
                    coord_ok = False
                    print(f"[FTTH PDF] CRS={authid} 与坐标范围不符: "
                          f"({xmin:.1f},{ymin:.1f})-({xmax:.1f},{ymax:.1f})，"
                          f"跳过强制 CRS，使用图层原生坐标渲染")
        if coord_ok:
            target_crs = layer_crs

    if target_crs:
        map_item.setCrs(target_crs)
    else:
        # 不设 CRS：让地图项跟随工程/图层的实际坐标系（处理 PRJ 错标场景）
        print("[FTTH PDF] 未强制设置地图项 CRS，将按图层原生坐标系渲染")
    map_item.setMapRotation(0)

    # ── 设置范围：优先用调用方指定的 extent，否则让地图项自动缩放到图层 ──
    if not final_extent.isEmpty():
        map_item.setExtent(final_extent)
        # 立刻验证：取回的范围是否与设定的一致（QGIS 有时会静默忽略）
        actual_after_set = map_item.extent()
        if actual_after_set.width() > 0 and actual_after_set.height() > 0:
            extent_set = True
            crs_label = target_crs.authid() if target_crs else "图层原生"
            print(f"[FTTH PDF] 手动设定范围: ({final_extent.xMinimum():.4f}, {final_extent.yMinimum():.4f}) - "
                  f"({final_extent.xMaximum():.4f}, {final_extent.yMaximum():.4f}), CRS={crs_label}")
        else:
            print(f"[FTTH PDF] WARNING: setExtent 后范围为空 (w={actual_after_set.width()}, h={actual_after_set.height()}), 将使用 zoomToExtent 兜底")

    if not extent_set:
        # 兜底：让 QGIS 根据已关联的图层自动计算最佳范围
        map_item.zoomToExtent()
        ext = map_item.extent()
        print(f"[FTTH PDF] zoomToExtent 范围: ({ext.xMinimum():.4f}, {ext.yMinimum():.4f}) - "
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

        # ── 强制渲染刷新（QGIS Print Layout 地图项需要主线程事件循环配合）──
        try:
            from qgis.core import QgsProject
            from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QTimer

            # 1) 先刷新主画布，让所有图层渲染缓存就绪
            from qgis.utils import iface
            if iface:
                canvas = iface.mapCanvas()
                canvas.refresh()
                QCoreApplication.processEvents()
                loop = QEventLoop()
                QTimer.singleShot(500, loop.quit)
                loop.exec()

            # 2) 再刷新布局内地图项
            map_item.refresh()
            QCoreApplication.processEvents()
            loop2 = QEventLoop()
            QTimer.singleShot(300, loop2.quit)
            loop2.exec()
        except Exception as render_err:
            print(f"[layout_export] 渲染等待异常（仍继续导出）: {render_err}")

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
    from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QTimer

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

        map_item = add_map_to_layout(
            layout, map_extent,
            map_position=QPointF(15, 55),
            map_size=QSizeF(320, 210),
            scale=scale,
            layers=valid_layers,
        )

        # ── 渲染等待管线：多次 refresh + 足够的延迟 ──
        # QGIS Print Layout 的地图项渲染是异步的（尤其多图层 + 投影变换时），
        # 单次 300ms 可能不够，导致导出时画布仍为空白。
        for wait_ms in (200, 300, 500):
            map_item.refresh()
            QCoreApplication.processEvents()
            loop = QEventLoop()
            QTimer.singleShot(wait_ms, loop.quit)
            loop.exec()

        # 导出前强制布局重算（确保图例/比例尺也基于已渲染的地图项）
        layout.refresh()
        QCoreApplication.processEvents()

        # 添加图例 / 比例尺 / 指北针
        add_legend_to_layout(layout, map_item)
        add_scale_bar_to_layout(layout, map_item)
        add_north_arrow_to_layout(layout)

        # ── 最终渲染保障：图例/比例尺加入后，再等一轮确保全部就绪 ──
        layout.refresh()
        map_item.refresh()
        # 强制 Qt 场景重绘（解决某些 QGIS 版本地图项渲染缓存不更新的问题）
        try:
            map_item.update()
        except Exception:
            pass
        QCoreApplication.processEvents()

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

        final_wait = QEventLoop()
        QTimer.singleShot(800, final_wait.quit)
        final_wait.exec()

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
        import traceback
        traceback.print_exc()
        print(f"Failed to create FTTH drawing: {e}")
        return None
