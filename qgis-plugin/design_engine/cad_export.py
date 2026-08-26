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
        QgsCoordinateTransform,
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

# ezdxf 用于 DXF 写出后的颜色后处理（强制写入 ACI 颜色，保证 AutoCAD 深色背景可见）。
# QGIS 自带的 Python 通常没有该包；未安装时跳过上色但不阻断导出（向后兼容）。
try:
    import ezdxf
    HAS_EZDXF = True
except Exception:
    HAS_EZDXF = False


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
LAYER_SCALE_BG = "SCALE_BG"  # 比例尺背景（提高深色背景对比度）
LAYER_NORTH = "NORTH"      # 指北针
LAYER_TITLE = "TITLE"      # 图签/标题文字
LAYER_LABEL = "LABEL"      # 要素编号标注

# 用于自动打要素编号的字段（按优先级取第一个存在的）
_LABEL_FIELDS = ["CODE", "siteId", "CODE_PTC", "name", "NAME",
                 "REF_PLAQUE", "REF_NRO"]


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
    "FRAME": 1,           # 图框：红（醒目边界）
    "SCALE": 2,           # 比例尺：黄（易读）
    "SCALE_BG": 7,        # 比例尺背景：白/黑（随背景反色）
    "NORTH": 1,           # 指北针：红
    "TITLE": 4,           # 图签文字：青（与白底/黑底都对比强）
    "LABEL": 6,           # 要素编号：品红（区分于图签）
    "SITE":  5,           # 站点：蓝
    "BUILD": 30,          # 楼栋：深灰（比纯黑浅，深色背景可见）
    "PIPE":  3,           # 管线：绿
    "AREA":  4,           # 覆盖区：青
    "TEXT":  7,           # 通用文字：白（随背景反色）
    # FTTH / 通信设计中的常见数据层（QGIS 原始图层名保留法语/英文缩写）
    "BOITE":           5,  # 分光箱/光交箱：蓝
    "INFRASTRUCTURE":  7,  # 基础设施：白
    "PTECH":           6,  # 技术点：品红
    "ZPM":             5,  # 配线点：蓝
    "N":               1,  # 指北针相关：红
    "0":               7,  # 默认层：白
}
# 线宽（mm），DXF 写入时映射为最接近的标准线宽
DXF_WIDTH_MM = {
    "FRAME": 0.30,   # 图框加粗
    "SCALE": 0.30,   # 比例尺主横线/刻度加粗，深色背景更清晰
    "SCALE_BG": 0.0, # 比例尺背景无线宽
    "NORTH": 0.20,
    "TITLE": 0.0,    # 文字层无线宽
    "LABEL": 0.0,
    "SITE":  0.25,
    "BUILD": 0.15,
    "PIPE":  0.35,
    "AREA":  0.15,
    "TEXT":  0.0,
    "BOITE": 0.20,
    "INFRASTRUCTURE": 0.15,
    "PTECH": 0.15,
    "ZPM":   0.20,
    "N":     0.0,
    "0":     0.0,
}
# 文字高度（mm），CAD 中 TEXT 实体高度
DXF_TEXT_HEIGHT_MM = {
    "SCALE": 2.0,   # 比例尺标注
    "NORTH": 3.0,   # N 字
    "TITLE": 2.5,   # 图签
    "LABEL": 2.0,   # 要素编号
    "TEXT":  2.0,
}


def _ascii_layer_name(name: str) -> str:
    r"""把任意图层名清理成 AutoCAD 安全 ASCII 名（非法字符转下划线）。

    AutoCAD 图层名不能包含 ? * : ; | " ' ` ~ < > \ / 等字符，且 CP1252 编码下
    中文字符会变成乱码。这里只保留字母、数字、空格、下划线、连字符、点，
    其余全部替换为下划线并合并。
    """
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.")
    safe = "".join(c if c in allowed else "_" for c in name)
    # 合并连续下划线
    while "__" in safe:
        safe = safe.replace("__", "_")
    safe = safe.strip("_ ")
    # 若清理后为空，兜底为 LAYER
    if not safe:
        safe = "LAYER"
    return safe[:31]  # DXF 图层名最大 31 字符


def _sanitize_dxf_layer_names(doc) -> dict[str, str]:
    """用 ezdxf 把 DXF 中所有非 ASCII / 乱码图层名重命名为安全 ASCII 名。

    AutoCAD 对 CP1252 编码写出的中文图层名会报"无效图层名"并放弃加载。
    此函数在颜色后处理前执行：遍历 LAYER 表，把含非 ASCII 的图层名改成安全名，
    同时更新模型空间里引用这些图层的实体。

    返回：{旧图层名: 新图层名} 映射表。
    """
    name_map: dict[str, str] = {}
    for layer in list(doc.layers):
        old_name = layer.dxf.name
        new_name = _ascii_layer_name(old_name)
        if new_name != old_name:
            # ezdxf 重命名图层
            layer.dxf.name = new_name
            name_map[old_name] = new_name

    if name_map:
        for entity in doc.modelspace():
            try:
                lname = entity.dxf.layer
                if lname in name_map:
                    entity.dxf.layer = name_map[lname]
            except Exception:
                pass
    return name_map


def _postprocess_dxf_colors(dxf_path: str,
                            text_annotations: list[dict] | None = None) -> None:
    """DXF 写出后，用 ezdxf 强制写入 ACI 颜色/线宽，并清理乱码图层名。

    QGIS 的 QgsDxfExport 不按我们给内存层/数据层临时设置的 renderer 颜色写出
    ACI 颜色（默认写 ByLayer 或忽略），且用 CP1252 编码时中文图层名会变成乱码。
    部分 QGIS 版本（如 3.44）还写不出内存文字层的 TEXT 实体。因此在所有写出
    路径成功后，重新打开 DXF：
      1. 把所有非 ASCII 图层名重命名为安全 ASCII 名；
      2. 按 CAD 图层名把该图层下所有实体颜色强制改为 DXF_ACI 规定的索引色；
      3. 清除实体的真彩色（420 组码），避免其覆盖 ACI；
      4. 设置线宽；
      5. 用 ezdxf 补充写入装饰/标注文字（比例尺、指北针、图签、要素编号）。
    这样不依赖 QGIS renderer，AutoCAD 深色背景下一定可见。

    仅修改颜色/线宽/图层名/文字属性，不改变坐标/几何。

    Args:
        dxf_path: 已写出的 DXF 文件路径（R2000）。
        text_annotations: 装饰文字标注列表，每项含 layer/text/x/y/height/aci。
    """
    if not HAS_EZDXF:
        print("[cad_export] 未安装 ezdxf，跳过 DXF 颜色后处理（DXF 仍可正常打开，"
              "只是保持默认颜色）。如需上色请运行: pip install ezdxf")
        return
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        # 0) 先清理乱码图层名，防止 AutoCAD 拒绝加载
        name_map = _sanitize_dxf_layer_names(doc)
        if name_map:
            print(f"[cad_export] DXF 图层名清理: {name_map}")

        # 1) 设置每个图层的颜色（ACI）
        for layer in doc.layers:
            lname = layer.dxf.name
            aci = DXF_ACI.get(lname)
            if aci is None:
                # 不在规范表中的图层：默认白（ACI 7 随背景反色），跳过不报错
                continue
            try:
                layer.dxf.color = aci
            except Exception as e:
                print(f"[cad_export] 图层 {lname} 颜色设置失败（已忽略）: {e}")

        # 2) 遍历模型空间所有实体，把颜色也设为对应图层的 ACI，
        #    并清除真彩色（420 组码），防止真彩色黑色覆盖 ACI。
        for entity in msp:
            try:
                lname = entity.dxf.layer
            except Exception:
                continue
            aci = DXF_ACI.get(lname)
            if aci is None:
                continue
            try:
                entity.dxf.color = aci
                if hasattr(entity.dxf, "true_color"):
                    entity.dxf.true_color = None
            except Exception:
                pass
            # 线实体顺带设线宽（可选；0 表示默认，跳过）
            w = DXF_WIDTH_MM.get(lname, 0.0)
            if w and w > 0:
                try:
                    # ezdxf 使用 1/100 mm 为单位的线宽整数常量
                    lw_mm = int(round(w * 100))
                    entity.dxf.lineweight = lw_mm
                except Exception:
                    pass

        # 3) 用 ezdxf 补充写入装饰/标注文字（QGIS 3.44 经常写不出内存文字层）
        #    关键：使用支持中文的 TrueType 字体 + MTEXT，避免 AutoCAD 默认
        #    txt.shx 字体把 Unicode 显示成 ???。
        added = 0
        if text_annotations:
            # 基于图框范围计算合理字号
            frame_extent = _frame_extent_from_dxf(doc)
            if frame_extent is not None:
                fw = max(frame_extent.width(), frame_extent.height())
                # 字号取图框宽/高的 1/40，但最小 2.5、最大 50（CRS 单位，
                # 对米级投影坐标如 EPSG:3857 约等于 mm*1000， AutoCAD 里适中）
                base_height = max(2.5, min(fw / 40.0, 50.0))
            else:
                base_height = 2.5

            # 创建/更新支持中文的 text style（优先 SimSun/宋体）
            _ensure_chinese_text_style(doc, "ChineseStyle")

            # 删除已有的装饰文字（避免重复/乱码残留）
            for ent in list(msp.query('TEXT MTEXT')):
                try:
                    if ent.dxf.layer in (LAYER_SCALE, LAYER_NORTH, LAYER_TITLE, LAYER_LABEL):
                        msp.delete_entity(ent)
                except Exception:
                    pass

            # 先把图签(TITLE)文字合并成多行 MTEXT，避免四行各自居中后堆叠
            title_anns = [a for a in text_annotations
                          if a.get("layer") == LAYER_TITLE]
            other_anns = [a for a in text_annotations
                          if a.get("layer") != LAYER_TITLE]

            def _write_mtext(ann, attachment):
                nonlocal added
                try:
                    lname = ann.get("layer", "TEXT")
                    text = ann.get("text", "")
                    x = float(ann.get("x", 0.0))
                    y = float(ann.get("y", 0.0))
                    height = float(ann.get("height", base_height))
                    if height < base_height * 0.5:
                        height = base_height
                    aci = int(ann.get("aci", DXF_ACI.get(lname, 7)))
                    if not text:
                        return
                    if lname not in doc.layers:
                        doc.layers.add(lname)
                        doc.layers.get(lname).dxf.color = aci
                    msp.add_mtext(text, dxfattribs={
                        "insert": (x, y),
                        "char_height": height,
                        "layer": lname,
                        "color": aci,
                        "style": "ChineseStyle",
                        "attachment_point": attachment,
                    })
                    added += 1
                except Exception as e:
                    print(f"[cad_export] 文字标注写入失败（已忽略）: {e}")

            # 图签：合并为右下角对齐的多行文本
            if title_anns:
                # 按 y 从大到小排序，保证工程在最上、日期在最下
                title_anns.sort(key=lambda a: float(a.get("y", 0.0)), reverse=True)
                title_text = r"\P".join(a.get("text", "") for a in title_anns)
                # 取最右下角那个点作为对齐基准（x 最大，y 最小）
                anchor = min(title_anns, key=lambda a: (float(a.get("x", 0.0)), -float(a.get("y", 0.0))))
                _write_mtext({
                    "layer": LAYER_TITLE,
                    "text": title_text,
                    "x": anchor["x"],
                    "y": anchor["y"],
                    "height": title_anns[0].get("height", base_height),
                    "aci": title_anns[0].get("aci", DXF_ACI.get(LAYER_TITLE, 4)),
                }, ezdxf.const.MTEXT_BOTTOM_RIGHT)

            # 比例尺数字：底部居中对齐，避免数字盖在比例尺线上
            for ann in other_anns:
                if ann.get("layer") == LAYER_SCALE:
                    _write_mtext(ann, ezdxf.const.MTEXT_BOTTOM_CENTER)
                elif ann.get("layer") == LAYER_NORTH:
                    _write_mtext(ann, ezdxf.const.MTEXT_MIDDLE_CENTER)
                else:
                    _write_mtext(ann, ezdxf.const.MTEXT_MIDDLE_CENTER)
        if added:
            print(f"[cad_export] 已用 ezdxf 补充写入 {added} 个文字标注")

        # 4) 给"面状"图层补 HATCH 填充。QGIS QgsDxfExport 对 Polygon 层的
        #    半透明填充经常写不出（只留描边），这里用 ezdxf 兜底补图案填充：
        #    稀疏斜线既能表达"面"的范围，又不会实心遮住底层管线和站点。
        #    仅对显式面层白名单补 HATCH，避免把管线(PIPE)、指北针线、图框等
        #    LWPOLYLINE 误填成实心带。
        _HATCH_LAYERS = {LAYER_AREA, "ZPM", "INFRASTRUCTURE"}
        try:
            hatch_cnt = 0
            for entity in list(msp):
                if entity.dxftype() not in ("LWPOLYLINE", "POLYLINE"):
                    continue
                lname = entity.dxf.layer
                if lname not in _HATCH_LAYERS:
                    continue
                try:
                    if entity.dxftype() == "POLYLINE":
                        pts = [(v[0], v[1]) for v in entity.vertices]
                    else:
                        pts = [(p[0], p[1]) for p in entity.get_points("xy")]
                    if len(pts) < 3:
                        continue
                    # 用稀疏斜线图案（ANSI31 45°线），缩放按图框大小自适应，
                    # 避免在小图里线条过密、大图里线条过稀。
                    if frame_extent is not None:
                        diag = max(frame_extent.width(), frame_extent.height())
                        pattern_scale = max(diag / 400.0, 0.5)
                    else:
                        pattern_scale = 2.0
                    hatch = msp.add_hatch(
                        color=DXF_ACI.get(lname, 4),
                        dxfattribs={"layer": lname})
                    hatch.paths.add_polyline_path(pts, is_closed=True)
                    # 设置图案：ANSI31 稀疏斜线，半透明让底层几何可见
                    hatch.set_pattern_fill(
                        "ANSI31",
                        scale=pattern_scale,
                        angle=45.0,
                    )
                    # 透明度 0.7 = 30% 不透明度，AutoCAD 2004+ 支持
                    try:
                        hatch.set_transparency(0.7)
                    except Exception:
                        pass
                    hatch_cnt += 1
                except Exception:
                    pass
            if hatch_cnt:
                print(f"[cad_export] 已为 {hatch_cnt} 个面状图层补充斜线半透明填充")
        except Exception as e:
            print(f"[cad_export] 覆盖区填充补充失败（已忽略）: {e}")

        doc.save()
        print(f"[cad_export] 已用 ezdxf 强制上色 {len(list(msp))} 个实体")
    except Exception as e:
        print(f"[cad_export] DXF 颜色后处理失败（已忽略，不影响导出文件）: {e}")


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
            "color": f"{color.red()},{color.green()},{color.blue()},60",  # 半透明填充
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


def _frame_extent_from_dxf(doc) -> "QgsRectangle | None":
    """从已写出的 DXF 中读取 FRAME 图层的图框范围，供文字字号/位置校准。"""
    try:
        xs, ys = [], []
        for entity in doc.modelspace():
            if entity.dxftype() in ("LWPOLYLINE", "POLYLINE", "LINE") \
                    and entity.dxf.layer == LAYER_FRAME:
                try:
                    if entity.dxftype() == "LINE":
                        s = entity.dxf.start
                        e = entity.dxf.end
                        xs.extend([s[0], e[0]])
                        ys.extend([s[1], e[1]])
                    else:
                        for pt in entity.get_points("xy"):
                            xs.append(pt[0])
                            ys.append(pt[1])
                except Exception:
                    pass
        if xs and ys:
            # 不依赖 QgsRectangle，直接用 namedtuple-like 对象
            class _Rect:
                def __init__(self, x1, y1, x2, y2):
                    self.xMinimum = min(x1, x2)
                    self.yMinimum = min(y1, y2)
                    self.xMaximum = max(x1, x2)
                    self.yMaximum = max(y1, y2)

                def width(self):
                    return self.xMaximum - self.xMinimum

                def height(self):
                    return self.yMaximum - self.yMinimum
            return _Rect(min(xs), min(ys), max(xs), max(ys))
    except Exception:
        pass
    return None


def _ensure_chinese_text_style(doc, style_name: str = "ChineseStyle"):
    """确保 DXF 文档里有一个支持中文的 TrueType 字体样式。"""
    try:
        styles = doc.styles
        if style_name not in styles:
            style = styles.new(style_name)
        else:
            style = styles.get(style_name)
        # 优先 SimSun（宋体），AutoCAD 简体中文版通常自带；
        # 回退用 Arial Unicode MS / simhei.ttf 等常见字体
        style.dxf.font = "SimSun.ttf"
        # 若 ezdxf 支持，设置大字体文件（shx）为空，避免 SHX 覆盖 TrueType
        if hasattr(style.dxf, "bigfont"):
            style.dxf.bigfont = ""
    except Exception as e:
        print(f"[cad_export] 中文字体样式创建失败（已忽略）: {e}")


def _compute_data_extent(layers, dst_crs):
    """计算所有导出图层在 dst_crs 下的联合 bbox；无有效图层返回 None。

    装饰层（图框/比例尺/指北针/图签）应以该范围为准，紧密包住真实数据，
    避免当前视图或框选范围远大于数据时 DXF 里出现大片空白。
    """
    extent = None
    for layer in layers:
        if not getattr(layer, "isValid", lambda: False)():
            continue
        layer_crs = layer.crs()
        layer_extent = layer.extent()
        if layer_extent is None or layer_extent.isNull():
            continue
        try:
            if layer_crs.isValid() and dst_crs.isValid() and layer_crs != dst_crs:
                transform = QgsCoordinateTransform(
                    layer_crs, dst_crs, QgsProject.instance())
                layer_extent = transform.transformBoundingBox(layer_extent)
        except Exception:
            pass
        if extent is None:
            extent = QgsRectangle(layer_extent)
        else:
            extent.combineExtentWith(layer_extent)
    return extent


def _build_decorations(extent, dst_crs, base_layers=None,
                       title_info: dict | None = None):
    """构造标准图装饰图层（图框/比例尺/指北针/图签/要素编号）。

    返回 (DxfLayer 列表, 内存层列表, 文字标注列表)。文字标注用于 ezdxf 后处理
    兜底写入，因为 QGIS 3.44 的 QgsDxfExport 对内存文字层经常写不出 TEXT 实体。

    文字标注项格式：{"layer": str, "text": str, "x": float, "y": float,
                     "height": float, "aci": int}
    """
    out = []
    mem_layers = []
    text_annotations = []
    if extent is None or extent.isNull():
        return out, mem_layers, text_annotations
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
        pad = max(extent.width(), extent.height()) * 0.02 or 1.0
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

        # ── 比例尺 SCALE（标准分段刻度 + 文字标注）──
        try:
            width_m = _to_meters(extent.width())
            scale_len_m = _nice_interval(width_m / 8.0) if width_m > 0 else 100.0
            scale_len = _to_crs_units(scale_len_m)
            sx0, sy0 = fx0 + pad * 0.6, fy0 + pad * 0.6
            seg = scale_len / 4.0  # 4 等分
            th = pad * 0.18         # 刻度短线高度（略微加大）
            bg_w = scale_len + seg * 0.25  # 背景矩形宽度
            bg_h = th * 2.4                # 背景矩形高度
            # 比例尺背景：浅色填充块，让黄色刻度线在深色背景更清晰
            scale_bg = _make_mem_layer("Polygon", crs_auth, LAYER_SCALE_BG)
            mem_layers.append(scale_bg)
            bgf = QgsFeature()
            bgf.setGeometry(_ring(sx0 - seg * 0.1, sy0 - bg_h * 0.65,
                                  sx0 + bg_w, sy0 + bg_h * 0.35))
            scale_bg.dataProvider().addFeature(bgf)
            scale_bg.updateExtents(); scale_bg.setTitle(LAYER_SCALE_BG)
            out.append(QgsDxfExport.DxfLayer(scale_bg))
            # 主刻度线（横）
            scale = _make_mem_layer("LineString", crs_auth, LAYER_SCALE)
            mem_layers.append(scale)
            sf = QgsFeature()
            sf.setGeometry(QgsGeometry.fromPolylineXY([
                QgsPointXY(sx0, sy0), QgsPointXY(sx0 + scale_len, sy0)]))
            scale.dataProvider().addFeature(sf)
            # 首尾 + 中间 5 个垂直刻度线
            for i in range(5):
                px = sx0 + seg * i
                tick = QgsFeature()
                tick.setGeometry(QgsGeometry.fromPolylineXY([
                    QgsPointXY(px, sy0 - th / 2), QgsPointXY(px, sy0 + th / 2)]))
                scale.dataProvider().addFeature(tick)
            scale.updateExtents(); scale.setTitle(LAYER_SCALE)
            out.append(QgsDxfExport.DxfLayer(scale))
            # 比例尺文字：0 / 1/4 / 2/4 / 3/4 / 全长
            stxt = _make_mem_layer("Point", crs_auth, LAYER_SCALE, with_text=True)
            mem_layers.append(stxt)
            for i in range(5):
                px = sx0 + seg * i
                # 中间三档标 m 数值，首尾标 0 / 总米数
                if i == 0:
                    txt = "0"
                elif i == 4:
                    txt = f"{scale_len_m:g} m"
                else:
                    txt = f"{scale_len_m * i / 4:g}"
                t = QgsFeature()
                t.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(px, sy0 - th)))
                t.setFields(stxt.fields())
                t.setAttributes([txt]); stxt.dataProvider().addFeature(t)
                text_annotations.append({
                    "layer": LAYER_SCALE, "text": txt,
                    "x": px, "y": sy0 - th,
                    "height": DXF_TEXT_HEIGHT_MM.get(LAYER_SCALE, 2.0),
                    "aci": DXF_ACI.get(LAYER_SCALE, 2),
                })
            stxt.updateExtents(); stxt.setTitle(LAYER_SCALE)
            out.append(QgsDxfExport.DxfLayer(stxt))
        except Exception as e:
            print(f"[cad_export] 比例尺生成失败: {e}")

        # ── 指北针 NORTH（右上角三角箭头 + N 字）──
        try:
            # 位置往图框内移，避免贴边被裁切；箭头加大更易辨识
            nx0, ny0 = fx1 - pad * 1.5, fy1 - pad * 0.8
            arrow_len = pad * 1.5
            north = _make_mem_layer("LineString", crs_auth, LAYER_NORTH)
            mem_layers.append(north)
            # 杆（底部到箭尖）
            nf = QgsFeature()
            nf.setGeometry(QgsGeometry.fromPolylineXY([
                QgsPointXY(nx0, ny0), QgsPointXY(nx0, ny0 + arrow_len * 0.8)]))
            north.dataProvider().addFeature(nf)
            # 三角形箭头（实心：用两段直线 + 底边，AutoCAD 里观感如三角）
            head = QgsFeature()
            head.setGeometry(QgsGeometry.fromPolylineXY([
                QgsPointXY(nx0, ny0 + arrow_len),
                QgsPointXY(nx0 - arrow_len * 0.28, ny0 + arrow_len * 0.72),
                QgsPointXY(nx0 + arrow_len * 0.28, ny0 + arrow_len * 0.72),
                QgsPointXY(nx0, ny0 + arrow_len)]))
            north.dataProvider().addFeature(head)
            north.updateExtents(); north.setTitle(LAYER_NORTH)
            out.append(QgsDxfExport.DxfLayer(north))
            ntxt = _make_mem_layer("Point", crs_auth, LAYER_NORTH, with_text=True)
            mem_layers.append(ntxt)
            nx_txt, ny_txt = nx0, ny0 + arrow_len + pad * 0.15
            t = QgsFeature()
            t.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(nx_txt, ny_txt)))
            t.setFields(ntxt.fields())
            t.setAttributes(["N"]); ntxt.dataProvider().addFeature(t)
            text_annotations.append({
                "layer": LAYER_NORTH, "text": "N",
                "x": nx_txt, "y": ny_txt,
                "height": DXF_TEXT_HEIGHT_MM.get(LAYER_NORTH, 3.0),
                "aci": DXF_ACI.get(LAYER_NORTH, 1),
            })
            ntxt.updateExtents(); ntxt.setTitle(LAYER_NORTH)
            out.append(QgsDxfExport.DxfLayer(ntxt))
        except Exception as e:
            print(f"[cad_export] 指北针生成失败: {e}")

        # ── 图签 TITLE（右下角信息文字 + 边框）──
        try:
            info = title_info or {}
            lines = [
                f"工程: {info.get('工程名称', '通信基建数智化平台')}",
                f"图名: {info.get('图纸名称', '通信设计方案')}",
                f"坐标系: {info.get('坐标系', crs_auth)}",
                f"日期: {info.get('日期', '')}",
            ]
            # 图签框尺寸：宽取最长行估算，高取 4 行
            title = _make_mem_layer("Point", crs_auth, LAYER_TITLE, with_text=True)
            mem_layers.append(title)
            tx = fx1 - pad * 0.6
            ty = fy0 + pad * (0.6 + (len(lines) - 1) * 1.4)
            line_h = pad * 1.4
            box_w = pad * 10.0
            box_h = line_h * (len(lines) + 0.4)
            box_x0, box_y0 = tx - pad * 0.3, ty - box_h + pad * 0.2
            box_x1, box_y1 = tx + box_w, fy0 + pad * 0.4
            # 图签矩形框
            box_layer = _make_mem_layer("Polygon", crs_auth, LAYER_TITLE)
            mem_layers.append(box_layer)
            bf = QgsFeature()
            bf.setGeometry(_ring(box_x0, box_y0, box_x1, box_y1))
            box_layer.dataProvider().addFeature(bf)
            box_layer.updateExtents(); box_layer.setTitle(LAYER_TITLE)
            out.append(QgsDxfExport.DxfLayer(box_layer))
            for i, txt in enumerate(lines):
                ty_line = ty - i * line_h
                t = QgsFeature()
                t.setGeometry(QgsGeometry.fromPointXY(
                    QgsPointXY(tx, ty_line)))
                t.setFields(title.fields())
                t.setAttributes([txt]); title.dataProvider().addFeature(t)
                text_annotations.append({
                    "layer": LAYER_TITLE, "text": txt,
                    "x": tx, "y": ty_line,
                    "height": DXF_TEXT_HEIGHT_MM.get(LAYER_TITLE, 2.5),
                    "aci": DXF_ACI.get(LAYER_TITLE, 4),
                })
            title.updateExtents(); title.setTitle(LAYER_TITLE)
            out.append(QgsDxfExport.DxfLayer(title))
        except Exception as e:
            print(f"[cad_export] 图签生成失败: {e}")

        # ── 要素编号 LABEL（取各图层 CODE/siteId 等字段在要素位置写字）──
        # 仅给『站点(SITE)』和『光交箱/分光箱(BOITE)』编号，其余点层（楼栋、
        # 技术点等）数量大，编号会严重拥挤，故跳过。每类最多 15 个，超出不标。
        try:
            _LABEL_LIMIT = {"SITE": 15, "BOITE": 15}
            for layer in (base_layers or []):
                if layer is None or not getattr(layer, "isValid", lambda: False)():
                    continue
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    continue  # 线（管线）要素多，跳过避免拥挤
                safe = _safe_layer_name(layer.name())
                limit = _LABEL_LIMIT.get(safe)
                if limit is None:
                    continue  # 仅 SITE / BOITE 参与编号
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
                cnt = 0
                for feat in layer.getFeatures():
                    if cnt >= limit:
                        break
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
                    text_annotations.append({
                        "layer": LAYER_LABEL, "text": str(val),
                        "x": pt.x(), "y": pt.y(),
                        "height": DXF_TEXT_HEIGHT_MM.get(LAYER_LABEL, 2.0),
                        "aci": DXF_ACI.get(LAYER_LABEL, 6),
                    })
                    cnt += 1
                if lab.featureCount() > 0:
                    lab.updateExtents(); lab.setTitle(LAYER_LABEL)
                    out.append(QgsDxfExport.DxfLayer(lab))
        except Exception as e:
            print(f"[cad_export] 要素编号生成失败: {e}")

        print(f"[cad_export] 已生成 {len(out)} 个装饰/标注 DXF 图层，"
              f"{len(text_annotations)} 条文字标注")
    except Exception as e:
        print(f"[cad_export] 装饰图层生成失败: {e}")
    return out, mem_layers, text_annotations


# 跨调用保活临时图层（克隆数据层 + 装饰内存层），确保它们比 QgsDxfExport 活得久，
# 避免两者同时被 GC/析构时 QgsDxfExport 访问已释放的内存层 -> 悬空指针 -> QGIS 闪退。
# 每次 export_dxf 开头会先清空它（彼时上一次 QgsDxfExport 早已析构，安全）。
_GLOBAL_KEEPALIVE = []

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

    # 释放上一批临时图层（此时上一批 QgsDxfExport 早已析构，安全），并重置模块级
    # 保活列表。临时克隆层/装饰内存层必须活到本次 QgsDxfExport 析构之后，不能随
    # export_dxf 局部变量在函数返回时一起被 GC（那是此前「导出成功但闪退」的根因）。
    global _GLOBAL_KEEPALIVE
    _GLOBAL_KEEPALIVE = []

    # 收集要导出的矢量图层
    # 重要：QgsDxfExport 在底层（C++）只对「有几何的矢量图层」安全；一旦把
    #   栅格 / 注记 / 点云 / 网格 / 无几何属性表(NoGeometry) / 未知几何类型
    # 的图层喂进去，会触发原生崩溃（segfault，Python 层 try/except 无法捕获，
    #   表现为 QGIS 直接闪退）。因此必须严格过滤，并完整记录被跳过的图层。
    layers = []
    skipped = []  # (图层名, 跳过原因) —— 写日志用，便于排错
    for layer in project.mapLayers().values():
        if not isinstance(layer, QgsVectorLayer):
            skipped.append((getattr(layer, "name", lambda: "?")(),
                            "非矢量图层(栅格/注记/点云/网格等)"))
            continue
        if not layer.isValid():
            skipped.append((layer.name(), "图层无效 isValid=False"))
            continue
        # 兼容不同 QGIS 版本：hasGeometryType() 在部分发行版不存在，
        # 统一用 wkbType() + QgsWkbTypes.geometryType() 判断是否有几何。
        wkb = layer.wkbType()
        geom_type = QgsWkbTypes.geometryType(wkb)
        if geom_type == QgsWkbTypes.NullGeometry:
            skipped.append((layer.name(), "无几何类型(属性表/NoGeometry)"))
            continue
        if geom_type not in (QgsWkbTypes.PointGeometry, QgsWkbTypes.LineGeometry,
                             QgsWkbTypes.PolygonGeometry):
            skipped.append((layer.name(), f"不支持的几何类型({geom_type})"))
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
    _text_annotations = []       # 装饰文字标注，供 ezdxf 后处理兜底写入
    for layer in layers:
        safe = _safe_layer_name(layer.name())
        # 零副作用导出：克隆数据层，所有 DXF 需要的临时改动（图层名/标题/渲染
        # 样式/标注开关）只作用于克隆层，原始 QGIS 图层完全不动，因此导出后无需
        # 任何还原，也避免了「备份的 renderer 已被 C++ 销毁后又 setRenderer 回去」
        # 导致的悬空对象崩溃。
        try:
            cloned = layer.clone()
            if cloned is None or not cloned.isValid():
                raise RuntimeError("克隆图层无效")
        except Exception as e:
            print(f"[cad_export] 数据层 {safe} 克隆失败,跳过导出: {e}")
            skipped.append((layer.name(), f"克隆失败({e})"))
            continue
        # CAD 层名必须全英文/ASCII，否则 CP1252 编码写出后中文会变成乱码，
        # AutoCAD 读取 LAYER 表时报"无效图层名"并拒绝加载。克隆层是独立对象，
        # 改它的 name/title 不影响原始图层显示。
        try:
            if hasattr(cloned, "setTitle"):
                cloned.setTitle(safe)
            cloned.setName(safe)
        except Exception:
            pass
        # DXF 样式增强：覆盖克隆层颜色/线宽，保证 AutoCAD 深色背景下清晰可见。
        # 关键：QgsDxfExport 对 QgsHeatmapRenderer 等非单符号渲染器会原生崩溃，
        # 所以必须把任意渲染器统一替换为「单符号渲染器」。若覆盖失败，该层可能
        # 导致 QGIS 闪退，宁可跳过也不要冒险导出。
        try:
            _apply_symbol_style(cloned, DXF_ACI.get(safe, 7),
                                DXF_WIDTH_MM.get(safe, 0.0))
            if not isinstance(cloned.renderer(), QgsSingleSymbolRenderer):
                raise RuntimeError("覆盖后渲染器仍非单符号")
        except Exception as e:
            print(f"[cad_export] 数据层 {safe} 样式覆盖失败,跳过导出: {e}")
            skipped.append((layer.name(), f"样式覆盖失败({e})"))
            continue
        # ezdxf 后处理会用 MTEXT 重新写入全部装饰/标注文字，因此导出时关闭
        # 克隆层原生标注可规避 QgsDxfExport 标注导出路径的原生崩溃（仅当 ezdxf 可用）。
        if HAS_EZDXF:
            try:
                cloned.setLabelsEnabled(False)
            except Exception:
                pass
        dxf_layers.append(QgsDxfExport.DxfLayer(cloned))
        # 保活：克隆层必须在 QgsDxfExport 析构之后才可被 GC（否则悬空指针 -> 闪退）。
        # 放进模块级 _GLOBAL_KEEPALIVE，跨函数存活到下次导出清理。
        _GLOBAL_KEEPALIVE.append(cloned)

    # 构造装饰图层（图框/比例尺/指北针/图签/要素编号），与真实数据同框写出。
    # 装饰层以「模型坐标」绘制，并以 setLayerTitleAsName(True) 映射到 FRAME/SCALE/
    # NORTH/TITLE/LABEL 五个 CAD 图层，导入 CAD 后仍为可编辑矢量，不依赖外部库。
    if with_decorations:
        # 装饰层基准范围：以「真实导出数据的并集 bbox」(已转换到 dst_crs) 为准，
        # 紧密包住真实数据，不受当前视图/框选范围过大影响（修复图框巨大而数据
        # 只占一小点的错位现象）。extent 仅用于控制 QgsDxfExport 的裁剪范围
        # （见下方 setExtent），不参与装饰层绘制。
        data_extent = _compute_data_extent(layers, dst_crs)
        deco_extent = data_extent
        if deco_extent is None or deco_extent.isNull():
            # 无有效数据范围（理论上不会发生，因为上面已校验 layers 非空）时，
            # 回退到传入的 extent，再回退到图层并集，确保仍有装饰。
            if extent is not None and not extent.isNull():
                deco_extent = QgsRectangle(extent)
            if deco_extent is None or deco_extent.isNull():
                deco_extent = QgsRectangle()
                for l in layers:
                    le = l.extent()
                    if le is not None and not le.isNull():
                        deco_extent.combineExtentWith(le)
        if deco_extent is not None and not deco_extent.isNull():
            try:
                deco_layers, deco_mem, deco_texts = _build_decorations(
                    deco_extent, dst_crs, base_layers=layers,
                    title_info=title_info)
                if deco_layers:
                    dxf_layers.extend(deco_layers)
                # 防 GC 回收内存层导致 QgsDxfExport 持悬空指针 -> QGIS 原生崩溃(闪退)。
                # 装饰层未加入工程，必须保活到 QgsDxfExport 析构之后；用模块级
                # _GLOBAL_KEEPALIVE 保活（跨函数存活），下次导出开头再统一清理。
                _GLOBAL_KEEPALIVE.extend(deco_mem)
                # 导出时关闭装饰文字层原生标注（文字由 ezdxf 后处理写入，避免重复
                # 并规避 QgsDxfExport 标注导出原生崩溃）。装饰层是我们新建的内存层，
                # 直接关闭即可，无需还原（原始数据图层根本没被触碰）。
                if HAS_EZDXF:
                    for _dl in deco_mem:
                        try:
                            _dl.setLabelsEnabled(False)
                        except Exception:
                            pass
                _text_annotations.extend(deco_texts)
            except Exception as e:
                print(f"[cad_export] 装饰层并入失败（已跳过）: {e}")

    # ── 导出前诊断 ───────────────────────────────────────────────
    # 把即将喂给 QgsDxfExport 的图层清单与被跳过的图层写到 QGIS 日志
    # （菜单：视图 → 日志消息面板 → 通信设计CAD导出）。即使随后发生原生崩溃，
    # 这里的记录也已落盘，便于定位到底是哪一个图层触发了闪退。
    try:
        _exp_names = [getattr(l, "name", lambda: "?")() for l in layers]
        _log_lines = [
            f"[CAD导出] 目标CRS={dst_crs.authid() if (dst_crs and dst_crs.isValid()) else '?'}  "
            f"矢量图层数={len(layers)}  实际导出(含装饰)={len(dxf_layers)}",
            f"[CAD导出] 导出图层: {', '.join(_exp_names) if _exp_names else '(无)'}",
        ]
        if skipped:
            _log_lines.append("[CAD导出] 已跳过图层(安全): "
                              + "; ".join(f"{n}({r})" for n, r in skipped))
        _log_msg = "\n".join(_log_lines)
        print(_log_msg)
        try:
            from qgis.core import QgsMessageLog
            QgsMessageLog.logMessage(_log_msg, "通信设计CAD导出", 0)
        except Exception:
            pass
    except Exception:
        pass

    try:
        def _make_configured_dxf():
            """构造并配置好 CRS/范围/图层名选项的 QgsDxfExport 实例。"""
            d = QgsDxfExport()
            if hasattr(d, "setDestinationCrs"):
                d.setDestinationCrs(dst_crs)
            # 裁剪范围：优先用传入的 extent（用户框选/当前视图），
            # 若未指定则回退到真实数据的并集范围 data_extent，避免导出空白。
            clip_extent = extent
            if clip_extent is None or clip_extent.isNull():
                clip_extent = data_extent
            # 仅在校验通过的合法矩形上调用 setExtent：空矩形、或 x/y 方向翻转
            # （xMin>xMax / yMin>yMax，常见于坐标系变换后范围被翻转）会让
            # QgsDxfExport 内部产生退化区间，可能触发原生崩溃。翻转时直接跳过
            # setExtent，让 QGIS 导出全图范围（更安全）。
            if clip_extent is not None and not clip_extent.isNull() \
                    and clip_extent.xMinimum() < clip_extent.xMaximum() \
                    and clip_extent.yMinimum() < clip_extent.yMaximum() \
                    and hasattr(d, "setExtent"):
                d.setExtent(clip_extent)
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
                    _postprocess_dxf_colors(output_path, _text_annotations)
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
                _postprocess_dxf_colors(output_path, _text_annotations)
                return output_path
            errors.append(f"addLayers: {'; '.join(errs)}")
        except Exception as e:
            errors.append(f"addLayers: {e}")

        # 3) 直接 writeToFile(路径, 编码, layers)
        try:
            dxf = _make_configured_dxf()
            res, errs = _try_write(dxf, dxf_layers)
            if _is_ok(res):
                _postprocess_dxf_colors(output_path, _text_annotations)
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
        # 原始数据图层在导出过程中未被任何方式修改（克隆层承担了全部临时改动：
        # 图层名/标题/渲染样式/标注开关），因此这里**无需还原** renderer/图层名/
        # 标注开关，也就不存在「把已被 C++ 销毁的 renderer 还原回去」的悬空对象风险。
        # 临时层（克隆数据层 + 装饰内存层）由模块级 _GLOBAL_KEEPALIVE 保活到本次
        # 调用结束；下一次 export_dxf 开头会先清空它（彼时上一次 QgsDxfExport 早已
        # 析构，安全），这里不必手动 del，避免提前 GC 引发新的悬空指针。
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
