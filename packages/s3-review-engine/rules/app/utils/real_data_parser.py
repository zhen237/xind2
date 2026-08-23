# -*- coding: utf-8 -*-
"""
真实工程数据解析器（通信光纤 FTTH 竣工图 Shapefile）

【数据来源】
本地真实工程数据位于：
  D:\\1通信基建数智化平台\\a挑战杯赛题\\真实数据\\真实数据\\Plan_de_récolement\\Shape
该目录为摩洛哥 JAD-MARJANE FTTH（光纤到户）通信基建竣工图，包含 8 个图层：
  CABLE(光缆) / BOITE(光交/分纤箱) / PTECH(技术点/杆井) / SITE(站点/机柜)
  IMB(楼宇) / INFRASTRUCTURE(管道基础设施) / ZNRO(OLT范围) / ZPM(分纤区)

【解析方式】
Shapefile 的 .dbf 属性表采用标准 DBF III/IV 格式，本模块使用 Python 标准库直接解析
（struct + 字段定义区），不依赖 openpyxl / geopandas 等第三方库，规避环境兼容性问题。
解析后将真实字段映射为系统 DeviceParam 结构，供审查引擎做真实参数化比对。

【字段映射要点】
- CABLE：DIAMETRE(缆径) / CAPACITE(光纤容量) / NB_FIBRE_U(已用光纤) / MODE_POSE(敷设方式)
          / LONGUEUR(长度) / TYPE_CABLE(类型) / TYPE_FIBRE(光纤型号) / X,Y(坐标)
- BOITE：CAPACITE(端口容量) / NB_FIBRE_U(覆盖光纤数) / TYPE(箱体类型 BPE/PBO/BPI)
- PTECH：TYPE(井/杆) / NATURE / HAUTEUR_AP(杆高)
- 其余图层按 deviceType 归类，保留真实 CODE / 坐标等字段
注：真实数据为通信光纤网络，不承载电流、亦未采集接地电阻字段，
因此载流量、接地电阻规则对本数据不适用（引擎侧如实跳过，不造假）。
"""
import os
import struct
from typing import Dict, Any, List, Optional

# 真实数据 Shapefile 所在目录（默认值，可由调用方覆盖）
DEFAULT_SHAPE_DIR = (
    "D:/1通信基建数智化平台/a挑战杯赛题/真实数据/真实数据/Plan_de_récolement/Shape"
)

# 8 个图层对应的 .dbf 文件
LAYER_FILES = {
    "CABLE": "CABLE.dbf",
    "BOITE": "BOITE.dbf",
    "PTECH": "PTECH.dbf",
    "SITE": "SITE.dbf",
    "IMB": "IMB.dbf",
    "INFRASTRUCTURE": "INFRASTRUCTURE.dbf",
    "ZNRO": "ZNRO.dbf",
    "ZPM": "ZPM.dbf",
}


def _read_dbf(path: str):
    """标准库解析 DBF，返回 (fields, rows)。fields: [(name,type,length),...]"""
    with open(path, "rb") as f:
        data = f.read()
    hdrlen = struct.unpack("<H", data[8:10])[0]
    reclen = struct.unpack("<H", data[10:12])[0]
    nrec = struct.unpack("<I", data[4:8])[0]
    nfields = (hdrlen - 33) // 32
    fields = []
    for i in range(nfields):
        c = data[32 + i * 32: 32 + (i + 1) * 32]
        name = c[0:11].split(b"\x00")[0].decode("cp1252", "ignore")
        typ = chr(c[11])
        length = c[16]
        fields.append((name, typ, length))
    rows = []
    off = hdrlen
    for r in range(nrec):
        rec = data[off + r * reclen: off + (r + 1) * reclen]
        if rec[0:1] == b"\x2a":  # 删除标记
            continue
        row = {}
        p = 1
        for (name, typ, length) in fields:
            row[name] = rec[p:p + length].decode("cp1252", "ignore").strip()
            p += length
        rows.append(row)
    return fields, rows


def _f(v: Optional[str]) -> Optional[float]:
    """安全转 float，空或非数字返回 None"""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _coords(r: Dict[str, str]) -> str:
    """由真实 X/Y 坐标构造 [x,y,0] 字符串（后端保留坐标字段，前端不展示地图）"""
    x = r.get("X", "")
    y = r.get("Y", "")
    if x and y:
        try:
            return "[{},{},0]".format(float(x), float(y))
        except (ValueError, TypeError):
            return ""
    return ""


def _map_device_type(layer: str, r: Dict[str, str]) -> str:
    """将真实图层与类型字段映射为系统统一 deviceType"""
    if layer == "CABLE":
        return "communication_cable"
    if layer == "BOITE":
        t = (r.get("TYPE") or "").upper()
        if "PBO" in t:
            return "optical_splitter_box"  # 分纤箱
        if "BPE" in t:
            return "optical_box"           # 光交箱
        return "optical_box"
    if layer == "PTECH":
        t = (r.get("TYPE") or "").upper()
        if "POTEAU" in t:
            return "tower"                 # 杆
        return "well"                      # 井/人孔
    if layer == "SITE":
        return "site"
    if layer == "IMB":
        return "building"
    if layer == "INFRASTRUCTURE":
        return "infrastructure"
    if layer in ("ZNRO", "ZPM"):
        return "zone"
    return "other"


def _to_device(layer: str, r: Dict[str, str]) -> Dict[str, Any]:
    """将单条真实记录映射为系统 DeviceParam 结构"""
    code = r.get("CODE", "")
    device = {
        "deviceId": code,
        "deviceName": r.get("NOM") or code,
        "deviceType": _map_device_type(layer, r),
        "sourceLayer": layer,
        "layerCode": code,
        "coordinates": _coords(r),
        "city": r.get("VILLE", ""),
        "status": r.get("STATUT", ""),
    }
    # 图层特定真实工程字段
    if layer == "CABLE":
        device["cableDiameter"] = _f(r.get("DIAMETRE"))      # 缆径（真实数据多为 0）
        device["capacity"] = _f(r.get("CAPACITE"))           # 光纤容量
        device["fibreUsed"] = _f(r.get("NB_FIBRE_U"))        # 已用光纤数
        device["modePose"] = r.get("MODE_POSE", "")          # 敷设方式
        device["length"] = _f(r.get("LONGUEUR"))             # 长度(米)
        device["cableType"] = r.get("TYPE_CABLE", "")        # DISTRIBUTION/TRANSPORT
        device["material"] = r.get("TYPE_FIBRE", "")         # 光纤型号 G657A1 等
    elif layer == "BOITE":
        device["capacity"] = _f(r.get("CAPACITE"))           # 端口容量
        device["fibreUsed"] = _f(r.get("NB_FIBRE_U"))        # 覆盖光纤数
        device["boxType"] = r.get("TYPE", "")                # BPE/PBO/BPI
    elif layer == "PTECH":
        device["techType"] = r.get("TYPE", "")               # CHAMBRE/POTEAU
        device["nature"] = r.get("NATURE", "")
        device["height"] = _f(r.get("HAUTEUR_AP"))           # 杆高(米)
    elif layer == "SITE":
        device["siteType"] = r.get("TYPE", "")               # NRO/PM
    return device


def parse_real_data(shape_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    解析真实工程 Shapefile 目录，返回系统可识别的 design_data 结构。
    :param shape_dir: Shapefile .dbf 所在目录；为空时使用 DEFAULT_SHAPE_DIR
    :return: {"designTaskId","designTaskName","designType","devices":[...],"metadata":{...}}
    """
    shape_dir = shape_dir or DEFAULT_SHAPE_DIR
    devices: List[Dict[str, Any]] = []
    layer_counts: Dict[str, int] = {}

    for layer, fname in LAYER_FILES.items():
        p = os.path.join(shape_dir, fname)
        if not os.path.exists(p):
            layer_counts[layer] = 0
            continue
        _, rows = _read_dbf(p)
        layer_counts[layer] = len(rows)
        for r in rows:
            devices.append(_to_device(layer, r))

    metadata = {
        "projectName": "JAD-MARJANE FTTH 通信光纤网络工程",
        "dataSource": "真实工程竣工图 Shapefile (Plan de récolement)",
        "region": "El Jadida, Maroc",
        "standardReference": "GB 51158 通信线路工程设计规范 / YD/T 901 层绞式光缆 / YD 5098 通信局站防雷接地设计规范",
        "layerCounts": layer_counts,
        "totalDevices": len(devices),
    }

    return {
        "designTaskId": "JAD-MARJANE-FTTH",
        "designTaskName": metadata["projectName"],
        "designType": "communication_optical",
        "sourceLayer": "multiple",
        "devices": devices,
        "metadata": metadata,
    }


if __name__ == "__main__":
    import json
    d = parse_real_data()
    print("devices:", len(d["devices"]))
    print("layerCounts:", d["metadata"]["layerCounts"])
    # 打印前 2 条样本
    print(json.dumps(d["devices"][:2], ensure_ascii=False, indent=2))
