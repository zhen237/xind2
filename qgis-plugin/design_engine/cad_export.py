"""CAD 图纸导出模块 (cad_export.py)

把 QGIS 中的通信设计图层导出为 CAD 可用格式：
  - DXF：通过 QGIS 原生 QgsDxfExport 生成（AutoCAD R2000 矢量，可在 CAD 中编辑）。
         使用 QgsDxfExport.DxfLayer 列表一次写出，自动保留点/线/面多种几何类型。
  - DWG：DXF 的 Autodesk 私有封装，QGIS 原生不支持，需借助外部转换器
         （ODA File Converter，免费）把 DXF -> DWG。本模块自动检测本机是否安装，
         装了就一键转，没装就只出 DXF 并提示下载地址。

设计图层 -> CAD 图层映射（layer name 尽量用英文，CAD 兼容性最好）：
  - 基站/站点 (点)        -> SITE   (基站、机房、NRO、ZNRO 等)
  - FTTH 楼栋/用户 (点)   -> BUILD  (IMB 楼栋)
  - 管线/光路由 (线)      -> PIPE   (管线、CABLE 光缆)
  - 覆盖/建议区 (面)      -> AREA   (覆盖缺口、建议站点缓冲区)
  - 标注/文字             -> TEXT   (站点编号、参数标注)
"""

from __future__ import annotations

import os
import shutil
import subprocess

# QGIS 环境内才导入，离线单元测试时不依赖
try:
    from qgis.core import (
        QgsProject,
        QgsRectangle,
        QgsCoordinateReferenceSystem,
        QgsDxfExport,
        QgsMapSettings,
        Qgis,
        QgsVectorLayer,
        QgsFeature,
        QgsGeometry,
        QgsField,
        QgsPointXY,
        QgsWkbTypes,
        QgsSingleSymbolRenderer,
    )
    from qgis.PyQt.QtCore import QFile, QIODevice, QVariant
    HAS_QGIS = True
except Exception:  # pragma: no cover - 非 QGIS 环境（离线测试）
    HAS_QGIS = False

import math


# CAD 图层名常量
LAYER_SITE = "SITE"      # 站点/设备点
LAYER_BUILD = "BUILD"    # 楼栋/用户点
LAYER_PIPE = "PIPE"      # 管线/光路由线
LAYER_AREA = "AREA"      # 覆盖/缓冲区面
LAYER_TEXT = "TEXT"      # 标注文字

# 常见 ODA File Converter 安装位置（Windows）
ODA_CANDIDATES = [
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"D:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
]


def find_oda_converter() -> str | None:
    """查找本机是否安装了 ODA File Converter，返回可执行路径或 None。"""
    env_path = os.environ.get("ODA_FILE_CONVERTER")
    if env_path and os.path.isfile(env_path):
        return env_path
    for cand in ODA_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    found = shutil.which("ODAFileConverter")
    if found:
        return found
    return None


def _safe_layer_name(name: str) -> str:
    """把 QGIS 图层名转成 CAD 友好的英文名（去掉中文/空格/特殊字符）。"""
    table = {
        "基站": LAYER_SITE,
        "站点": LAYER_SITE,
        "机房": LAYER_SITE,
        "NRO": LAYER_SITE,
        "ZNRO": LAYER_SITE,
        "楼栋": LAYER_BUILD,
        "IMB": LAYER_BUILD,
        "用户": LAYER_BUILD,
        "管线": LAYER_PIPE,
        "光缆": LAYER_PIPE,
        "CABLE": LAYER_PIPE,
        "路由": LAYER_PIPE,
        "覆盖": LAYER_AREA,
        "缺口": LAYER_AREA,
        "建议": LAYER_AREA,
        "标注": LAYER_TEXT,
    }
    for k, v in table.items():
        if k in name:
            return v
    ascii_name = "".join(c if ord(c) < 128 else "_" for c in name)[:16]
    return ascii_name or LAYER_PIPE


# 装饰图层 CAD 层名常量
LAYER_FRAME = "FRAME"      # 图框
LAYER_SCALE = "SCALE"      # 比例尺
LAYER_NORTH = "NORTH"      # 指北针
LAYER_TITLE = "TITLE"      # 图签/标题文字
LAYER_LABEL = "LABEL"      # 要素编号标注

# 用于自动打要素编号的字段（按优先级取第一个存在的）
_LABEL_FIELDS = ["CODE", "CODE_PTC", "NAME", "REF_PLAQUE", "REF_NRO"]


def _nice_interval(raw: float) -> float:
    """把原始间隔取整到 1/2/5 × 10ⁿ 的『漂亮』刻度数。"""
    if raw is None or raw <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(raw))
    norm = raw / mag
    step = 1.0 if norm <= 1 else 2.0 if norm <= 2 else 5.0 if norm <= 5 else 10.0
    return step * mag


# ── DXF 颜色/线宽/文字高度统一规范 ───────────────────────────────────────
# AutoCAD 深色背景下默认黑色细线/默认字号几乎不可见，这里按「CAD 索引色(ACI)」
# 给装饰层与数据层统一设置高对比颜色、线宽、文字高度。
# ACI 常用值：1=红 2=黄 3=绿 4=青 5=蓝 6=品红 7=白/黑(随背景) 30~250=灰度
DXF_ACI = {
    "FRAME": 1,    # 图框：红（醒目边界）
    "SCALE": 2,    # 比例尺：黄（易读）
    "NORTH": 1,    # 指北针：红
    "TITLE": 4,    # 图签文字：青（与白底/黑底都对比强）
    "LABEL": 6,    # 要素编号：品红（区分于图签）
    "SITE":  5,    # 站点：蓝
    "BUILD": 30,   # 楼栋：深灰（比纯黑浅，深色背景可见）
    "PIPE":  3,    # 管线：绿
    "AREA":  4,    # 覆盖区：青
    "TEXT":  7,    # 通用文字：白（随背景反色）
}
# 线宽（mm），DXF 写入时映射为最接近的标准线宽
DXF_WIDTH_MM = {
    "FRAME": 0.30,   # 图框加粗
    "SCALE": 0.15,
    "NORTH": 0.20,
    "TITLE": 0.0,    # 文字层无线宽
    "LABEL": 0.0,
    "SITE":  0.20,
    "BUILD": 0.10,
    "PIPE":  0.20,
    "AREA":  0.10,
    "TEXT":  0.0,
}
# 文字高度（mm），CAD 中 TEXT 实体高度
DXF_TEXT_HEIGHT_MM = {
    "SCALE": 2.0,   # 比例尺标注
    "NORTH": 3.0,   # N 字
    "TITLE": 2.5,   # 图签
    "LABEL": 2.0,   # 要素编号
    "TEXT":  2.0,
}


def _aci_color(idx: int):
    """构造 QColor，按 ACI 索引。ACI 1~255 为 AutoCAD 索引色。"""
    from qgis.PyQt.QtGui import QColor
    # 用标准 ACI RGB 近似（保证深色背景可见；ACI 7 白色用纯白）
    aci_rgb = {
        1: (255, 0, 0), 2: (255, 255, 0), 3: (0, 255, 0),
        4: (0, 255, 255), 5: (0, 0, 255), 6: (255, 0, 255),
        7: (255, 255, 255), 30: (128, 128, 128), 250: (255, 255, 255),
    }
    r, g, b = aci_rgb.get(idx, (255, 255, 255))
    return QColor(r, g, b)


def _apply_symbol_style(vl, aci: int, width_mm: float = 0.0):
    """给内存层设置渲染符号的颜色与线宽（DXF 导出时即写入 ACI 颜色/线宽）。"""
    from qgis.core import (
        QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer,
        QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol,
    )
    gt = vl.geometryType()
    color = _aci_color(aci)
    if gt == QgsWkbTypes.PointGeometry:
        sym = QgsMarkerSymbol.createSimple({
            "color": f"{color.red()},{color.green()},{color.blue()}",
            "size": "3", "size_unit": "MM",
            "outline_color": "0,0,0", "outline_width": "0.2",
        })
    elif gt == QgsWkbTypes.LineGeometry:
        sym = QgsLineSymbol.createSimple({
            "color": f"{color.red()},{color.green()},{color.blue()}",
            "width": f"{width_mm if width_mm > 0 else 0.15}",
            "width_unit": "MM",
        })
    else:  # Polygon
        sym = QgsFillSymbol.createSimple({
            "color": "0,0,0,0",  # 透明填充，仅描边
            "outline_color": f"{color.red()},{color.green()},{color.blue()}",
            "outline_width": f"{width_mm if width_mm > 0 else 0.15}",
            "outline_width_unit": "MM",
        })
    vl.setRenderer(_single_renderer(gt, sym))


def _single_renderer(gt, sym):
    from qgis.core import QgsSingleSymbolRenderer
    return QgsSingleSymbolRenderer(sym)


def _apply_text_style(vl, aci: int, height_mm: float):
    """给文字内存层设置标注（label）的文字高度与颜色，DXF 写出时映射为 TEXT 高度。"""
    try:
        from qgis.core import QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling
        from qgis.PyQt.QtGui import QColor
        fs = QgsPalLayerSettings()
        fs.fieldName = "TEXT"
        fmt = QgsTextFormat()
        fmt.setSize(height_mm)
        fmt.setSizeUnit(2)  # 2 = MM
        c = _aci_color(aci)
        fmt.setColor(c)
        fs.setFormat(fmt)
        vl.setLabelsEnabled(True)
        vl.setLabeling(QgsVectorLayerSimpleLabeling(fs))
        vl.triggerRepaint()
    except Exception as e:
        print(f"[cad_export] 文字样式设置失败（已忽略）: {e}")


def _make_mem_layer(geom_type: str, crs_auth: str, name: str,
                    with_text: bool = False, aci: int | None = None,
                    width_mm: float = 0.0, text_height_mm: float = 0.0):
    """创建一个内存矢量图层（用于生成 DXF 装饰/标注），并应用 DXF 颜色/线宽/字号。"""
    uri = f"{geom_type}?crs={crs_auth}"
    vl = QgsVectorLayer(uri, name, "memory")
    pr = vl.dataProvider()
    if with_text:
        pr.addAttributes([QgsField("TEXT", QVariant.String)])
        vl.updateFields()
    # 应用 CAD 样式
    _aci = aci if aci is not None else DXF_ACI.get(name, 7)
    _w = width_mm if width_mm else DXF_WIDTH_MM.get(name, 0.0)
    _apply_symbol_style(vl, _aci, _w)
    if with_text:
        _h = text_height_mm if text_height_mm else DXF_TEXT_HEIGHT_MM.get(name, 2.0)
        _apply_text_style(vl, _aci, _h)
    return vl


def _build_decorations(extent, dst_crs, base_layers=None,
                       title_info: dict | None = None):
    """构造标准图装饰图层（图框/比例尺/指北针/图签/要素编号），返回 DxfLayer 列表。

    这些图层以『模型坐标』与真实数据同框绘制；图框包住导出范围，
    比例尺按真实世界长度画一段并标注米数，指北针画在右上角，图签写工程信息，
    要素编号取各图层的 CODE 等字段在要素位置写字。
    """
    out = []
    mem_layers = []
    if extent is None or extent.isNull():
        return out, mem_layers
    try:
        crs_auth = dst_crs.authid() if (dst_crs and dst_crs.isValid()) \
            else "EPSG:4326"
        is_geo = ('4326' in crs_auth) or ('wgs84' in crs_auth.lower())
        mid_lat = (extent.yMinimum() + extent.yMaximum()) / 2.0

        def _to_meters(width_crs_units: float) -> float:
            if is_geo:
                coslat = max(0.01, abs(math.cos(math.radians(mid_lat))))
                return width_crs_units * 111320.0 * coslat
            return width_crs_units

        def _to_crs_units(meters: float) -> float:
            if is_geo:
                coslat = max(0.01, abs(math.cos(math.radians(mid_lat))))
                return meters / (111320.0 * coslat)
            return meters

        # 边距与图框范围（模型单位）
        pad = max(extent.width(), extent.height()) * 0.03 or 1.0
        fx0, fy0 = extent.xMinimum() - pad, extent.yMinimum() - pad
        fx1, fy1 = extent.xMaximum() + pad, extent.yMaximum() + pad

        def _ring(x0, y0, x1, y1):
            return QgsGeometry.fromPolygonXY([[
                QgsPointXY(x0, y0), QgsPointXY(x1, y0),
                QgsPointXY(x1, y1), QgsPointXY(x0, y1),
                QgsPointXY(x0, y0),
            ]])

        # ── 图框 FRAME ──
        try:
            frame = _make_mem_layer("Polygon", crs_auth, LAYER_FRAME)
            mem_layers.append(frame)
            f = QgsFeature(); f.setGeometry(_ring(fx0, fy0, fx1, fy1))
            frame.dataProvider().addFeature(f); frame.updateExtents()
            frame.setTitle(LAYER_FRAME)
            out.append(QgsDxfExport.DxfLayer(frame))
        except Exception as e:
            print(f"[cad_export] 图框生成失败: {e}")

        # ── 比例尺 SCALE（真实世界长度 + 文字标注）──
        try:
            width_m = _to_meters(extent.width())
            scale_len_m = _nice_interval(width_m / 8.0) if width_m > 0 else 100.0
            scale_len = _to_crs_units(scale_len_m)
            sx0, sy0 = fx0 + pad * 0.6, fy0 + pad * 0.6
            scale = _make_mem_layer("LineString", crs_auth, LAYER_SCALE)
            mem_layers.append(scale)
            sf = QgsFeature()
            sf.setGeometry(QgsGeometry.fromPolylineXY([
                QgsPointXY(sx0, sy0), QgsPointXY(sx0 + scale_len, sy0)]))
            scale.dataProvider().addFeature(sf); scale.updateExtents()
            scale.setTitle(LAYER_SCALE)
            out.append(QgsDxfExport.DxfLayer(scale))
            # 比例尺文字：0 / 长度
            stxt = _make_mem_layer("Point", crs_auth, LAYER_SCALE, with_text=True)
            mem_layers.append(stxt)
            for px, txt in ((sx0, "0"), (sx0 + scale_len, f"{scale_len_m:g} m")):
                t = QgsFeature(); t.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(px, sy0)))
                t.setFields(stxt.fields())
                t.setAttributes([txt]); stxt.dataProvider().addFeature(t)
            stxt.updateExtents(); stxt.setTitle(LAYER_SCALE)
            out.append(QgsDxfExport.DxfLayer(
                stxt, stxt.fields().indexOf("TEXT")))
        except Exception as e:
            print(f"[cad_export] 比例尺生成失败: {e}")

        # ── 指北针 NORTH（右上角箭头 + N 字）──
        try:
            nx0, ny0 = fx1 - pad * 1.2, fy1 - pad * 0.6
            arrow_len = pad * 1.0
            north = _make_mem_layer("LineString", crs_auth, LAYER_NORTH)
            mem_layers.append(north)
            # 杆
            nf = QgsFeature()
            nf.setGeometry(QgsGeometry.fromPolylineXY([
                QgsPointXY(nx0, ny0), QgsPointXY(nx0, ny0 + arrow_len)]))
            north.dataProvider().addFeature(nf)
            # 箭头（两条斜线）
            head = QgsFeature()
            head.setGeometry(QgsGeometry.fromPolylineXY([
                QgsPointXY(nx0 - arrow_len * 0.25, ny0 + arrow_len * 0.6),
                QgsPointXY(nx0, ny0 + arrow_len),
                QgsPointXY(nx0 + arrow_len * 0.25, ny0 + arrow_len * 0.6)]))
            north.dataProvider().addFeature(head)
            north.updateExtents(); north.setTitle(LAYER_NORTH)
            out.append(QgsDxfExport.DxfLayer(north))
            ntxt = _make_mem_layer("Point", crs_auth, LAYER_NORTH, with_text=True)
            mem_layers.append(ntxt)
            t = QgsFeature()
            t.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(nx0, ny0 + arrow_len + pad * 0.15)))
            t.setFields(ntxt.fields())
            t.setAttributes(["N"]); ntxt.dataProvider().addFeature(t)
            ntxt.updateExtents(); ntxt.setTitle(LAYER_NORTH)
            out.append(QgsDxfExport.DxfLayer(
                ntxt, ntxt.fields().indexOf("TEXT")))
        except Exception as e:
            print(f"[cad_export] 指北针生成失败: {e}")

        # ── 图签 TITLE（右下角信息文字）──
        try:
            info = title_info or {}
            lines = [
                f"工程: {info.get('工程名称', '通信基建数智化平台')}",
                f"图名: {info.get('图纸名称', '通信设计方案')}",
                f"坐标系: {info.get('坐标系', crs_auth)}",
                f"日期: {info.get('日期', '')}",
            ]
            title = _make_mem_layer("Point", crs_auth, LAYER_TITLE, with_text=True)
            mem_layers.append(title)
            ty = fy0 + pad * (0.6 + (len(lines) - 1) * 1.4)
            for i, txt in enumerate(lines):
                t = QgsFeature()
                t.setGeometry(QgsGeometry.fromPointXY(
                    QgsPointXY(fx1 - pad * 0.6, ty - i * pad * 1.4)))
                t.setFields(title.fields())
                t.setAttributes([txt]); title.dataProvider().addFeature(t)
            title.updateExtents(); title.setTitle(LAYER_TITLE)
            out.append(QgsDxfExport.DxfLayer(
                title, title.fields().indexOf("TEXT")))
        except Exception as e:
            print(f"[cad_export] 图签生成失败: {e}")

        # ── 要素编号 LABEL（取各图层 CODE 等字段在要素位置写字）──
        try:
            for layer in (base_layers or []):
                if layer is None or not getattr(layer, "isValid", lambda: False)():
                    continue
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    continue  # 线（管线）要素多，跳过避免拥挤
                fld = None
                for cand in _LABEL_FIELDS:
                    if layer.fields().indexOf(cand) >= 0:
                        fld = cand
                        break
                if fld is None:
                    continue
                lab = _make_mem_layer("Point", crs_auth, LAYER_LABEL, with_text=True)
                mem_layers.append(lab)
                idx = layer.fields().indexOf(fld)
                for feat in layer.getFeatures():
                    g = feat.geometry()
                    if g is None or g.isEmpty():
                        continue
                    pt = g.centroid().asPoint() if g.type() == QgsWkbTypes.PolygonGeometry \
                        else g.asPoint()
                    val = feat[idx]
                    if val is None or str(val).strip() == "":
                        continue
                    t = QgsFeature()
                    t.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                    t.setFields(lab.fields())
                    t.setAttributes([str(val)]); lab.dataProvider().addFeature(t)
                if lab.featureCount() > 0:
                    lab.updateExtents(); lab.setTitle(LAYER_LABEL)
                    out.append(QgsDxfExport.DxfLayer(
                        lab, lab.fields().indexOf("TEXT")))
        except Exception as e:
            print(f"[cad_export] 要素编号生成失败: {e}")

        print(f"[cad_export] 已生成 {len(out)} 个装饰/标注 DXF 图层")
    except Exception as e:
        print(f"[cad_export] 装饰图层生成失败: {e}")
    return out, mem_layers


def export_dxf(
    project=None,
    output_path: str = "",
    extent: "QgsRectangle | None" = None,
    extent_crs: "QgsCoordinateReferenceSystem | None" = None,
    layer_filter: list[str] | None = None,
    title_info: dict | None = None,
    with_decorations: bool = True,
) -> str:
    """导出 DXF。

    Args:
        project: QgsProject 实例（默认 QgsProject.instance()）。
        output_path: 输出 DXF 路径；为空则落到桌面。
        extent: 导出范围（QgsRectangle）。
        extent_crs: 范围坐标系。
        layer_filter: 仅导出这些 QGIS 图层名（含子串匹配）；为空导出全部矢量图层。

    Returns:
        生成的 DXF 文件路径；失败抛异常。
    """
    if not HAS_QGIS:
        raise RuntimeError("QgsDxfExport 仅在 QGIS 运行环境内可用（请在 QGIS 中调用）。")

    project = project or QgsProject.instance()

    # 收集要导出的矢量图层
    layers = []
    for layer in project.mapLayers().values():
        if not hasattr(layer, "wkbType"):
            continue
        lname = layer.name()
        if layer_filter and not any(f in lname for f in layer_filter):
            continue
        layers.append(layer)

    if not layers:
        raise RuntimeError("没有可导出的矢量图层，请先生成设计方案。")

    # 输出路径兜底
    if not output_path:
        output_path = os.path.join(
            os.path.expanduser("~"), "Desktop", "通信设计方案.dxf")
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # 目标 CRS：默认项目 CRS；若指定 extent_crs 则用 extent_crs
    dst_crs = extent_crs if extent_crs is not None else project.crs()
    if dst_crs is None or not dst_crs.isValid():
        dst_crs = QgsCoordinateReferenceSystem("EPSG:4326")

    # 构造 QgsDxfExport.DxfLayer 列表：每个 QGIS 图层 -> DXF 中的一个 CAD 图层
    # 注意：本机 QGIS 3.44 的 DxfLayer 构造函数是
    #   DxfLayer(QgsVectorLayer* layer, int layerOutputAttributeIndex=-1, ...)
    # 不支持自定义 layerName 参数，因此只传图层引用。
    # CAD 层名通过 setLayerTitleAsName(True) + 图层 title 控制：
    #   把图层 title 设为英文简称（不改动 layer.setName，保留用户的中文显示名）。
    dxf_layers = []
    _deco_keepalive = []
    _data_renderer_backup = []  # 导出后恢复原图层渲染样式，避免改动地图显示
    for layer in layers:
        safe = _safe_layer_name(layer.name())
        if hasattr(layer, "setTitle"):
            try:
                layer.setTitle(safe)
            except Exception:
                pass
        # DXF 样式增强：临时覆盖数据层颜色/线宽，保证 AutoCAD 深色背景下清晰可见
        # 导出完成后在 finally 中恢复原 renderer（不改动 QGIS 地图显示）
        try:
            _data_renderer_backup.append((layer, layer.renderer()))
            _apply_symbol_style(layer, DXF_ACI.get(safe, 7),
                                DXF_WIDTH_MM.get(safe, 0.0))
        except Exception as e:
            print(f"[cad_export] 数据层 {safe} 样式覆盖跳过: {e}")
        dxf_layers.append(QgsDxfExport.DxfLayer(layer))

    # 构造装饰图层（图框/比例尺/指北针/图签/要素编号），与真实数据同框写出。
    # 装饰层以「模型坐标」绘制，并以 setLayerTitleAsName(True) 映射到 FRAME/SCALE/
    # NORTH/TITLE/LABEL 五个 CAD 图层，导入 CAD 后仍为可编辑矢量，不依赖外部库。
    if with_decorations:
        deco_extent = extent
        if deco_extent is None or deco_extent.isNull():
            # 未指定范围时，用所有导出图层的并集范围，确保装饰包住全部数据
            deco_extent = QgsRectangle()
            for l in layers:
                le = l.extent()
                if le is not None and not le.isNull():
                    deco_extent.combineExtentWith(le)
        if deco_extent is not None and not deco_extent.isNull():
            try:
                deco_layers, deco_mem = _build_decorations(
                    deco_extent, dst_crs, base_layers=layers,
                    title_info=title_info)
                if deco_layers:
                    dxf_layers.extend(deco_layers)
                # 防 GC 回收内存层导致 QgsDxfExport 持悬空指针 -> QGIS 原生崩溃(闪退)
                # 装饰层未加入工程，必须保活到 writeToFile 完成
                _deco_keepalive.extend(deco_mem)
            except Exception as e:
                print(f"[cad_export] 装饰层并入失败（已跳过）: {e}")

    try:
        def _make_configured_dxf():
            """构造并配置好 CRS/范围/图层名选项的 QgsDxfExport 实例。"""
            d = QgsDxfExport()
            if hasattr(d, "setDestinationCrs"):
                d.setDestinationCrs(dst_crs)
            if extent is not None and not extent.isNull() and hasattr(d, "setExtent"):
                d.setExtent(extent)
            if hasattr(d, "setLayerTitleAsName"):
                d.setLayerTitleAsName(True)
            return d

        # 写出 DXF：兼容不同 QGIS 版本的 API
        # QGIS 3.44 实测：
        #   - 无 setLayers 方法
        #   - addLayers(dxfLayers) 可用
        #   - writeToFile 只接受 QIODevice，不再接受文件路径字符串
        # 旧版/其他版本可能有 setLayers 或 writeToFile(path, enc) / writeToFile(path, enc, layers)
        # 这里把三种「设图层」方式与三种「写文件」签名交叉尝试。

        def _success_value():
            dxf_res = getattr(Qgis, "DxfExportResult", None)
            if dxf_res is not None and hasattr(dxf_res, "Success"):
                return dxf_res.Success
            return 0

        def _is_ok(res):
            return res is not None and res == _success_value()

        def _try_write(dxf, layers_for_third_arg=None):
            """优先用 QIODevice 写出；失败再回退字符串路径签名。"""
            errs = []

            # a) QIODevice（QGIS 3.44 等新版）
            file = QFile(output_path)
            if file.open(QIODevice.WriteOnly):
                try:
                    r = dxf.writeToFile(file, "CP1252")
                    if _is_ok(r):
                        return r, []
                    errs.append(f"writeToFile(QFile): {r}")
                except TypeError as e:
                    errs.append(f"writeToFile(QFile): {e}")
                finally:
                    file.close()
            else:
                errs.append(f"无法打开文件写入: {output_path}")

            # b) 字符串路径 + 编码
            try:
                r = dxf.writeToFile(output_path, "CP1252")
                if _is_ok(r):
                    return r, []
                errs.append(f"writeToFile(str,enc): {r}")
            except Exception as e:
                errs.append(f"writeToFile(str,enc): {e}")

            # c) 字符串路径 + 编码 + layers（旧版三参数）
            if layers_for_third_arg is not None:
                try:
                    r = dxf.writeToFile(output_path, "CP1252", layers_for_third_arg)
                    if _is_ok(r):
                        return r, []
                    errs.append(f"writeToFile(str,enc,layers): {r}")
                except Exception as e:
                    errs.append(f"writeToFile(str,enc,layers): {e}")
            return None, errs

        errors = []

        # 1) setLayers + writeToFile（部分 3.x 旧版）
        if hasattr(QgsDxfExport, "setLayers"):
            try:
                dxf = _make_configured_dxf()
                dxf.setLayers(dxf_layers)
                res, errs = _try_write(dxf)
                if _is_ok(res):
                    return output_path
                errors.append(f"setLayers: {'; '.join(errs)}")
            except Exception as e:
                errors.append(f"setLayers: {e}")

        # 2) addLayers + writeToFile（QGIS 3.44 实测可用）
        try:
            dxf = _make_configured_dxf()
            dxf.addLayers(dxf_layers)
            res, errs = _try_write(dxf)
            if _is_ok(res):
                return output_path
            errors.append(f"addLayers: {'; '.join(errs)}")
        except Exception as e:
            errors.append(f"addLayers: {e}")

        # 3) 直接 writeToFile(路径, 编码, layers)
        try:
            dxf = _make_configured_dxf()
            res, errs = _try_write(dxf, dxf_layers)
            if _is_ok(res):
                return output_path
            errors.append(f"writeToFile(3 args): {'; '.join(errs)}")
        except Exception as e:
            errors.append(f"writeToFile(3 args): {e}")

        raise RuntimeError(
            "当前 QGIS 版本的 QgsDxfExport 无法完成 DXF 导出。\n"
            f"已尝试接口: {'; '.join(errors)}\n"
            f"最终返回码: {res if 'res' in locals() else 'N/A'}\n"
            "建议：确认项目中有可导出的矢量图层；QGIS 3.44 请确保 writeToFile 使用 QFile。"
        )
    finally:
        # 恢复数据层原始渲染样式，避免 DXF 临时样式残留到 QGIS 地图显示
        for lyr, rnd in _data_renderer_backup:
            try:
                if rnd is not None:
                    lyr.setRenderer(rnd)
                    lyr.triggerRepaint()
            except Exception:
                pass

    return output_path


def export_dwg(dxf_path: str, convert_exe: str | None = None) -> tuple[bool, str]:
    """把 DXF 转换为 DWG（需要 ODA File Converter）。"""
    exe = convert_exe or find_oda_converter()
    if not exe or not os.path.isfile(exe):
        return False, (
            "未检测到 ODA File Converter，无法生成 DWG。\n"
            "可免费下载：https://www.opendesign.com/guestfiles/oda_file_converter\n"
            "DXF 仍可在 AutoCAD / 中望 / CAD 快速看图 等直接打开。")

    in_dir = os.path.dirname(dxf_path)
    out_dir = in_dir
    cmd = [
        exe,
        in_dir,
        out_dir,
        "ACAD2000",
        "ACAD2018",
        "DWG",
        "0",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:  # pragma: no cover
        return False, f"调用 ODAFileConverter 失败: {e}"

    dwg_path = os.path.splitext(dxf_path)[0] + ".dwg"
    if os.path.isfile(dwg_path):
        return True, dwg_path
    base = os.path.splitext(os.path.basename(dxf_path))[0]
    for f in os.listdir(out_dir):
        if f.lower().endswith(".dwg") and base in f:
            return True, os.path.join(out_dir, f)
    return False, f"ODA 转换未生成 DWG（返回码 {proc.returncode}）: {proc.stderr[:300]}"


def export_cad(
    output_path: str = "",
    to_dwg: bool = True,
    extent=None,
    extent_crs=None,
    layer_filter: list[str] | None = None,
    title_info: dict | None = None,
    with_decorations: bool = True,
) -> dict:
    """一键导出 CAD：先 DXF，可选转 DWG。"""
    result = {"dxf": None, "dwg": None, "dwg_auto": False, "msg": ""}

    if output_path:
        dxf_path = os.path.splitext(output_path)[0] + ".dxf"
    else:
        dxf_path = ""

    dxf_path = export_dxf(
        output_path=dxf_path,
        extent=extent,
        extent_crs=extent_crs,
        layer_filter=layer_filter,
        title_info=title_info,
        with_decorations=with_decorations,
    )
    result["dxf"] = dxf_path

    if to_dwg:
        oda = find_oda_converter()
        if oda:
            result["dwg_auto"] = True
            ok, info = export_dwg(dxf_path, oda)
            if ok:
                result["dwg"] = info
                result["msg"] = (
                    f"已生成 DXF 与 DWG：\n{result['dxf']}\n{result['dwg']}")
            else:
                result["msg"] = (
                    f"DXF 已生成：{result['dxf']}\n（DWG 转换失败：{info}）")
        else:
            result["msg"] = (
                f"DXF 已生成：{result['dxf']}\n"
                "（本机未安装 ODA File Converter，未生成 DWG；"
                "DXF 可被 AutoCAD/中望/CAD 快速看图 等直接打开）")
    else:
        result["msg"] = f"DXF 已生成：{result['dxf']}"

    return result
