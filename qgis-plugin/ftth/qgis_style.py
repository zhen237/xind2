# -*- coding: utf-8 -*-
"""
FTTH QGIS 画布符号化与异常高亮 (qgis_style.py)
=============================================

依赖 qgis.core / qgis.gui，仅在 QGIS 插件运行时可用（桌面端）。本仓库 CI 环境
无法 import qgis，故仅做 py_compile 语法校验，运行时需在 QGIS 桌面端实测。

提供:
  - load_ftth_layers(shape_dir)        : 加载 8 个 Shape 为 QgsVectorLayer
  - apply_ftth_styles(layers, ...)     : .qml 优先 + 程序化渲染器回退
  - make_renderer(layer_name)          : 生成单值/分类渲染器(与前端调色板一致)
  - export_ftth_styles(layers, out_dir): 导出 .qml 供团队复用
  - highlight_anomalies(layers, anomalies, canvas): 红框高亮异常要素(按 CODE)
  - clear_highlights(rubberbands)      : 清理高亮
  - combined_extent(layers)            : 返回图层联合范围

调色板与前端 Cesium 一致:
  PBO 青 #22d3ee / BPE 橙 #fb923c / SITE(PM) 金 #fbbf24
  配线缆 蓝 #60a5fa / 运输缆 绿 #22c55e / 杆路 品红 #e879f9 / 管道 天蓝 #0ea5e9
  ZNRO 玫红 #f43f5e / ZPM 蓝 #3b82f6 (面, 半透明填充)
"""

from __future__ import annotations

import os
from collections import defaultdict

from qgis.core import (
    QgsVectorLayer, QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol,
    QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsCoordinateReferenceSystem, QgsWkbTypes,
)
from qgis.gui import QgsRubberBand
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt

from .field_map import LAYER_FILE_PREFIX

# 图层渲染顺序(底→顶)：面在最下，点在上
FTTH_LAYER_ORDER = [
    "ZNRO", "ZPM", "INFRASTRUCTURE", "CABLE", "PTECH", "SITE", "BOITE", "IMB",
]

# 调色板（与前端 Cesium 一致）
COLOR = {
    "IMB": "#64748b",                # slate  - 楼栋住户(点)
    "SITE": "#fbbf24",               # gold   - 站点 PM(点)
    "BOITE_PBO": "#22d3ee",          # cyan   - 光分配箱 PBO(点)
    "BOITE_BPE": "#fb923c",          # orange - 光分纤箱 BPE(点)
    "CABLE_DISTRIBUTION": "#60a5fa", # blue   - 配线缆(线)
    "CABLE_TRANSPORT": "#22c55e",    # green  - 主干/运输缆(线)
    "CABLE_AUTRE": "#94a3b8",        # slate  - 其它缆(线)
    "PTECH": "#e879f9",              # magenta- 杆/井技术点(点)
    "INFRASTRUCTURE": "#0ea5e9",     # sky    - 管道/杆路(线)
    "ZNRO": "#f43f5e",               # rose   - OLT 覆盖范围(面)
    "ZPM": "#3b82f6",                # blue   - PM/SRO 范围(面)
}

# 需要按字段分类的图层
_CATEGORY_FIELD = {
    "BOITE": "TYPE",        # PBO / BPE
    "SITE": "TYPE",         # PM / ...
    "CABLE": "TYPE_CABLE",  # DISTRIBUTION / TRANSPORT / ...
}


def _symbol_for(layer_name: str, value=None) -> object:
    """按图层(及分类值)生成基础符号。"""
    v = (str(value).strip().upper() if value is not None else "")

    if layer_name == "BOITE":
        color = COLOR["BOITE_PBO"] if v == "PBO" else COLOR["BOITE_BPE"]
        return QgsMarkerSymbol.createSimple({
            "color": color, "size": "4", "outline_color": "#0f172a",
            "outline_width": "0.4",
        })
    if layer_name == "SITE":
        return QgsMarkerSymbol.createSimple({
            "color": COLOR["SITE"], "size": "5", "outline_color": "#0f172a",
            "outline_width": "0.5",
        })
    if layer_name == "IMB":
        return QgsMarkerSymbol.createSimple({
            "color": COLOR["IMB"], "size": "2.4", "outline_color": "#0f172a",
            "outline_width": "0.2",
        })
    if layer_name == "PTECH":
        return QgsMarkerSymbol.createSimple({
            "color": COLOR["PTECH"], "size": "3", "outline_color": "#0f172a",
            "outline_width": "0.3",
        })
    if layer_name == "CABLE":
        if v.startswith("TRANSPORT"):
            color = COLOR["CABLE_TRANSPORT"]
        elif v.startswith("DISTRIBUTION"):
            color = COLOR["CABLE_DISTRIBUTION"]
        else:
            color = COLOR["CABLE_AUTRE"]
        return QgsLineSymbol.createSimple({
            "color": color, "width": "0.8", "line_style": "solid",
        })
    if layer_name == "INFRASTRUCTURE":
        return QgsLineSymbol.createSimple({
            "color": COLOR["INFRASTRUCTURE"], "width": "0.6", "line_style": "dash",
        })
    if layer_name in ("ZNRO", "ZPM"):
        fill = COLOR[layer_name]
        # 8 位 hex 含 alpha(#RRGGBBAA)，约 20% 不透明填充
        return QgsFillSymbol.createSimple({
            "color": fill + "33", "outline_color": fill, "outline_width": "0.8",
        })
    # 兜底
    return QgsMarkerSymbol.createSimple({
        "color": "#888888", "size": "3", "outline_color": "#0f172a",
    })


def make_renderer(layer_name: str):
    """生成程序化单值渲染器(非分类图层)。"""
    return QgsSingleSymbolRenderer(_symbol_for(layer_name))


def _categorized_renderer(layer: QgsVectorLayer, field: str, layer_name: str):
    """按字段实际取值构建分类渲染器。"""
    values = set()
    for feat in layer.getFeatures():
        values.add((feat[field] or "").strip().upper())
    cats = []
    for v in sorted(values):
        sym = _symbol_for(layer_name, v)
        cats.append(QgsRendererCategory(v, sym, v or "(空)"))
    if not cats:
        return QgsSingleSymbolRenderer(_symbol_for(layer_name))
    return QgsCategorizedSymbolRenderer(field, cats)


def load_ftth_layers(shape_dir: str) -> dict:
    """加载 8 个 Shape 为 QgsVectorLayer，返回 {图层名: layer}。

    数据坐标为经纬度(EPSG:4326)；若 .shp 无 .prj 则兜底设为 4326。
    缺失某层(如部分数据集无 ZNRO/ZPM)则跳过。
    """
    layers = {}
    for name in FTTH_LAYER_ORDER:
        prefix = LAYER_FILE_PREFIX.get(name, name)
        shp = os.path.join(shape_dir, prefix + ".shp")
        if not os.path.exists(shp):
            continue
        layer = QgsVectorLayer(shp, name, "ogr")
        if not layer.isValid():
            continue
        crs = layer.crs()
        if crs is None or not crs.authId():
            layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        layers[name] = layer
    return layers


def apply_ftth_styles(layers: dict, style_dir: str | None = None) -> None:
    """为每个图层应用样式：style_dir 下同名 .qml 优先，否则程序化回退。"""
    for name, layer in layers.items():
        qml = os.path.join(style_dir, name + ".qml") if style_dir else None
        if qml and os.path.exists(qml):
            ok, _err = layer.loadNamedStyle(qml)
            if ok:
                layer.triggerRepaint()
                continue
        # 程序化回退
        if name in _CATEGORY_FIELD:
            field = _CATEGORY_FIELD[name]
            layer.setRenderer(_categorized_renderer(layer, field, name))
        else:
            layer.setRenderer(make_renderer(name))
        layer.triggerRepaint()


def export_ftth_styles(layers: dict, out_dir: str) -> dict:
    """把当前渲染器导出为 .qml，便于团队复用与版本管理。返回 {层: 路径}。"""
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for name, layer in layers.items():
        p = os.path.join(out_dir, name + ".qml")
        layer.saveNamedStyle(p)
        paths[name] = p
    return paths


def combined_extent(layers: dict):
    """返回所有图层联合范围(QgsRectangle)；无边距。"""
    ext = None
    for layer in layers.values():
        e = layer.extent()
        if e is None or e.isEmpty() or not e.isFinite():
            continue
        ext = e if ext is None else ext.combineExtentWith(e)
    return ext


def _new_rubberband(canvas, geom_type: int) -> QgsRubberBand:
    """创建一个红色高亮 RubberBand。"""
    if geom_type == QgsWkbTypes.PointGeometry:
        rb = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb.setIconSize(11)
    else:
        rb = QgsRubberBand(canvas, geom_type)
    rb.setColor(QColor(239, 68, 68))   # red-500
    rb.setWidth(2.5)
    rb.setBrushStyle(Qt.NoBrush)
    return rb


def highlight_anomalies(layers: dict, anomalies: dict, canvas) -> list:
    """对 anomalies[{图层: [CODE...]}] 中的要素用红色 RubberBand 高亮。

    anomalies 的 key 必须为 8 个 Shape 层名之一；value 为异常要素 CODE 集合。
    返回 rubberbands 列表，供 clear_highlights 清理。
    """
    rubberbands = []
    for name, codes in (anomalies or {}).items():
        layer = layers.get(name)
        if layer is None or canvas is None:
            continue
        code_set = set(str(c).strip().upper() for c in codes)
        if not code_set:
            continue
        rb = None
        for feat in layer.getFeatures():
            code = str(feat["CODE"] or "").strip().upper()
            if code not in code_set:
                continue
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            if rb is None:
                rb = _new_rubberband(canvas, layer.geometryType())
            rb.addGeometry(geom.constGet().clone(), layer)
        if rb is not None:
            rubberbands.append(rb)
    return rubberbands


def clear_highlights(rubberbands: list) -> None:
    """清理高亮 RubberBand。"""
    for rb in (rubberbands or []):
        try:
            rb.reset()
        except Exception:
            pass
