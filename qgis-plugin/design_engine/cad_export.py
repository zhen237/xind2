# -*- coding: utf-8 -*-
"""CAD 图纸导出引擎 (T7) — DWG / DXF

补齐 layout_export.py 仅有 PDF/PNG 的缺口（FR-9 / AC-5）。

实现策略（诚实且可落地）：
- **DXF**：手写 ASCII DXF R12（AC1009）。纯标准库，无第三方依赖，
  生成的文件可被 AutoCAD / LibreCAD / QGIS / 中望 CAD 直接打开。
  支持图层（LAYER 表）、站点(POINT+TEXT)、管线(LINE 段)、
  机房(CIRCLE+TEXT)、覆盖边界(POLYLINE→LINE 段)。
- **DWG**：DWG 是 Autodesk 专有二进制格式，无法在不引入 ODA/Teigha 等
  商业/重量级依赖的情况下合规生成。因此本模块：
    1. 始终先生成一份等效 DXF（标准、可打开）；
    2. 若系统 PATH 中存在 DWG 转换工具（odaconvert / teigha / dxf2dwg），
       则调用其把 DXF 转 DWG；
    3. 否则优雅降级：返回 dwg_created=False 并附带说明，由调用方提示用户
       "已生成标准 DXF，DWG 需经 CAD 另存/转换工具"。

纯标准库实现，可脱离 QGIS 在沙箱单测。QGIS 适配函数 `export_design_to_cad`
以懒加载方式 import qgis，仅在桌面插件内调用。
"""

import os
import shutil
from typing import List, Dict, Optional, Tuple

# ============================================================
#  图层定义
# ============================================================
LAYER_SITES = "SITES"
LAYER_PIPELINES = "PIPELINES"
LAYER_ROOMS = "ROOMS"
LAYER_COVERAGE = "COVERAGE"

DEFAULT_LAYERS = [LAYER_SITES, LAYER_PIPELINES, LAYER_ROOMS, LAYER_COVERAGE]


def _fmt(value) -> str:
    """DXF 数值格式化：浮点保留 7 位，整数原样。"""
    if isinstance(value, float):
        return "{:.7f}".format(value)
    return str(value)


def _point_entity(layer: str, x: float, y: float, z: float = 0.0) -> List[Tuple[str, str]]:
    return [("8", layer), ("10", _fmt(x)), ("20", _fmt(y)), ("30", _fmt(z))]


def _line_entity(layer: str, x1, y1, x2, y2) -> List[Tuple[str, str]]:
    return [
        ("8", layer),
        ("10", _fmt(x1)), ("20", _fmt(y1)), ("30", "0.0"),
        ("11", _fmt(x2)), ("21", _fmt(y2)), ("31", "0.0"),
    ]


def _circle_entity(layer: str, cx, cy, r) -> List[Tuple[str, str]]:
    return [("8", layer), ("10", _fmt(cx)), ("20", _fmt(cy)), ("30", "0.0"), ("40", _fmt(r))]


def _text_entity(layer: str, x, y, text, height=50.0) -> List[Tuple[str, str]]:
    return [
        ("8", layer),
        ("10", _fmt(x)), ("20", _fmt(y)), ("30", "0.0"),
        ("40", _fmt(height)),
        ("1", str(text)),
    ]


def _emit_entity(out, entity_type: str, fields: List[Tuple[str, str]]):
    out.append("0")
    out.append(entity_type)
    for code, value in fields:
        out.append(code)
        out.append(value)


def entities_to_dxf(entities: List[Dict], layers: Optional[List[str]] = None) -> str:
    """把实体列表渲染为 ASCII DXF R12 文本。

    Args:
        entities: [{'type':'point'|'line'|'circle'|'text', 'layer':str, ...}]
        layers: 需要建立的图层名列表

    Returns:
        DXF 文件完整文本
    """
    layers = layers or DEFAULT_LAYERS
    out: List[str] = []

    # HEADER
    out.append("0"); out.append("SECTION")
    out.append("2"); out.append("HEADER")
    out.append("9"); out.append("$ACADVER")
    out.append("1"); out.append("AC1009")  # R12
    out.append("0"); out.append("ENDSEC")

    # TABLES — LAYER
    out.append("0"); out.append("SECTION")
    out.append("2"); out.append("TABLES")
    out.append("0"); out.append("TABLE")
    out.append("2"); out.append("LAYER")
    out.append("70"); out.append("1")
    for layer in layers:
        out.append("0"); out.append("LAYER")
        out.append("2"); out.append(layer)
        out.append("70"); out.append("0")   # 图层开启
        out.append("62"); out.append("7")   # 颜色：白(7)
        out.append("6"); out.append("CONTINUOUS")
    out.append("0"); out.append("ENDTAB")
    out.append("0"); out.append("ENDSEC")

    # ENTITIES
    out.append("0"); out.append("SECTION")
    out.append("2"); out.append("ENTITIES")
    for e in entities:
        t = e.get("type")
        layer = e.get("layer", LAYER_SITES)
        if t == "point":
            _emit_entity(out, "POINT", _point_entity(layer, e["x"], e["y"]))
        elif t == "line":
            _emit_entity(out, "LINE", _line_entity(layer, e["x1"], e["y1"], e["x2"], e["y2"]))
        elif t == "circle":
            _emit_entity(out, "CIRCLE", _circle_entity(layer, e["cx"], e["cy"], e["r"]))
        elif t == "text":
            _emit_entity(out, "TEXT", _text_entity(layer, e["x"], e["y"], e["text"]))
    out.append("0"); out.append("ENDSEC")

    # EOF
    out.append("0"); out.append("EOF")
    return "\n".join(out) + "\n"


def _design_to_entities(design: Dict) -> List[Dict]:
    """把归一化 design 字典转为 DXF 实体列表。"""
    entities: List[Dict] = []

    # 站点
    for s in design.get("sites", []) or []:
        lon = float(s.get("longitude", s.get("lon", 0)))
        lat = float(s.get("latitude", s.get("lat", 0)))
        sid = s.get("siteId", s.get("site_id", ""))
        entities.append({"type": "point", "layer": LAYER_SITES, "x": lon, "y": lat})
        entities.append({"type": "text", "layer": LAYER_SITES,
                         "x": lon, "y": lat, "text": str(sid), "height": 50.0})

    # 管线（每个坐标段画一条 LINE）
    for p in design.get("pipelines", []) or []:
        coords = p.get("coordinates")
        if coords is None and hasattr(p, "coordinates"):
            coords = p.coordinates  # 支持 Pipeline 对象
        if not coords or len(coords) < 2:
            continue
        for i in range(len(coords) - 1):
            a = coords[i]
            b = coords[i + 1]
            entities.append({
                "type": "line", "layer": LAYER_PIPELINES,
                "x1": float(a[0]), "y1": float(a[1]),
                "x2": float(b[0]), "y2": float(b[1]),
            })

    # 机房（圆 + 标注）
    for r in design.get("rooms", []) or []:
        lon = float(r.get("longitude", r.get("lon", 0)))
        lat = float(r.get("latitude", r.get("lat", 0)))
        rid = r.get("room_id", r.get("roomId", r.get("name", "ROOM")))
        cap = r.get("capacity", "")
        entities.append({"type": "circle", "layer": LAYER_ROOMS,
                         "cx": lon, "cy": lat, "r": 0.0008})
        entities.append({"type": "text", "layer": LAYER_ROOMS,
                         "x": lon, "y": lat, "text": str(rid), "height": 60.0})

    # 覆盖边界（GeoJSON 多边形 → LINE 段）
    cov = design.get("coverage")
    if isinstance(cov, dict) and cov.get("type") == "FeatureCollection":
        for feat in cov.get("features", []):
            geom = feat.get("geometry", {})
            if geom.get("type") == "Polygon":
                ring = geom["coordinates"][0]
                for i in range(len(ring) - 1):
                    a = ring[i]; b = ring[i + 1]
                    entities.append({
                        "type": "line", "layer": LAYER_COVERAGE,
                        "x1": float(a[0]), "y1": float(a[1]),
                        "x2": float(b[0]), "y2": float(b[1]),
                    })

    return entities


def export_design_to_dxf(design: Dict, path: str,
                         layers: Optional[List[str]] = None) -> str:
    """把设计导出为 DXF 文件，返回实际写出路径。"""
    entities = _design_to_entities(design)
    dxf_text = entities_to_dxf(entities, layers)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(dxf_text)
    return path


def _find_dwg_converter() -> Optional[str]:
    """探测系统可用的 DXF→DWG 转换工具。"""
    for tool in ("odaconvert", "teigha", "dxf2dwg", "dwg2dxf"):
        if shutil.which(tool):
            return tool
    return None


def export_design_to_dwg(design: Dict, path: str,
                         layers: Optional[List[str]] = None) -> Dict:
    """导出 DWG。

    始终先生成等效 DXF；若找到 DWG 转换工具则转 DWG，否则优雅降级。

    Returns:
        {
          'dwg_path': str|None,
          'dxf_path': str,
          'dwg_created': bool,
          'converter': str|None,
          'note': str,
        }
    """
    dxf_path = path
    if not dxf_path.lower().endswith(".dxf"):
        dxf_path = path + ".dxf"
    export_design_to_dxf(design, dxf_path, layers)

    converter = _find_dwg_converter()
    dwg_path = None
    dwg_created = False
    note = ""

    if converter:
        import subprocess
        target = dxf_path[:-4] + ".dwg"
        try:
            subprocess.run([converter, dxf_path, target], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(target) and os.path.getsize(target) > 0:
                dwg_path = target
                dwg_created = True
                note = "已通过 %s 将 DXF 转换为 DWG" % converter
            else:
                note = "转换器 %s 未产出有效 DWG，已保留 DXF" % converter
        except Exception as e:  # noqa: BLE001
            note = "DWG 转换失败(%s)：%s；已保留等效 DXF" % (converter, e)
    else:
        note = ("未检测到 DWG 转换工具（ODA/Teigha 等）。已生成标准 DXF，"
                "可被 AutoCAD/LibreCAD/中望CAD 直接打开；如需 DWG 请在 CAD 中另存。")

    return {
        "dwg_path": dwg_path,
        "dxf_path": dxf_path,
        "dwg_created": dwg_created,
        "converter": converter,
        "note": note,
    }


# ============================================================
#  QGIS 适配器（懒加载，桌面插件内使用）
# ============================================================
def export_design_to_cad(
    sites: List[Dict],
    pipelines: Optional[List] = None,
    rooms: Optional[List] = None,
    coverage: Optional[Dict] = None,
    path: str = "",
    fmt: str = "dxf",
) -> Dict:
    """从 Python 对象（无需 QGIS）导出 CAD。

    供 design_dock 直接调用：传入 self.generated_sites /
    self.generated_pipelines / self.machine_rooms。

    Args:
        sites: 站点 dict 列表
        pipelines: Pipeline 对象或 dict 列表
        rooms: 机房 dict 列表
        coverage: 覆盖 GeoJSON（可选）
        path: 输出路径（.dxf 或 .dwg）
        fmt: 'dxf' | 'dwg'

    Returns:
        export_design_to_dwg 的返回结构（dxf 模式 dwg_created=False）
    """
    design = {
        "sites": sites or [],
        "pipelines": pipelines or [],
        "rooms": rooms or [],
        "coverage": coverage,
    }
    if fmt.lower() == "dwg":
        return export_design_to_dwg(design, path)
    out = export_design_to_dxf(design, path)
    return {
        "dwg_path": None, "dxf_path": out, "dwg_created": False,
        "converter": None, "note": "已导出标准 DXF",
    }
