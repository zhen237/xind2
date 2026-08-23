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
    )
    HAS_QGIS = True
except Exception:  # pragma: no cover - 非 QGIS 环境（离线测试）
    HAS_QGIS = False


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


def export_dxf(
    project=None,
    output_path: str = "",
    extent: "QgsRectangle | None" = None,
    extent_crs: "QgsCoordinateReferenceSystem | None" = None,
    layer_filter: list[str] | None = None,
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
    for layer in layers:
        safe = _safe_layer_name(layer.name())
        if hasattr(layer, "setTitle"):
            try:
                layer.setTitle(safe)
            except Exception:
                pass
        dxf_layers.append(QgsDxfExport.DxfLayer(layer))

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
    #  - 新版(>=3.4): setLayers(dxfLayers) 后 writeToFile(fileName, encoding)
    #  - 旧版:        writeToFile(fileName, encoding, dxfLayers)
    #  - 更旧(2.x):   addLayers(dxfLayers) 后 writeToFile(fileName, encoding)
    # 每个 API 都用全新的 QgsDxfExport 实例尝试，避免状态污染。
    errors = []
    res = None

    # 1) 新版 API
    try:
        dxf = _make_configured_dxf()
        dxf.setLayers(dxf_layers)
        res = dxf.writeToFile(output_path, "CP1252")
    except Exception as e:
        errors.append(f"setLayers+writeToFile: {e}")

    # 2) 旧版三参数 API
    if res is None or res != 0:
        try:
            dxf = _make_configured_dxf()
            res = dxf.writeToFile(output_path, "CP1252", dxf_layers)
        except Exception as e:
            errors.append(f"writeToFile(3 args): {e}")

    # 3) 更旧 addLayers API
    if res is None or res != 0:
        try:
            dxf = _make_configured_dxf()
            dxf.addLayers(dxf_layers)
            res = dxf.writeToFile(output_path, "CP1252")
        except Exception as e:
            errors.append(f"addLayers+writeToFile: {e}")

    if res is None or res != 0:
        raise RuntimeError(
            "当前 QGIS 版本的 QgsDxfExport 无法完成 DXF 导出。\n"
            f"已尝试接口: {'; '.join(errors)}\n"
            f"最终返回码: {res}\n"
            "建议：升级 QGIS 到 3.28+，或确认项目中有可导出的矢量图层。"
        )

    if not os.path.isfile(output_path):
        raise RuntimeError(f"DXF 导出失败，未生成文件: {output_path}")

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
