# -*- coding: utf-8 -*-
"""
FTTH Shape 加载器 (loader.py)
=============================

两种数据源:
  1) load_dbf(shape_dir): 直接读 .dbf (dbfread)，用于离线校验/测试。
  2) load_qgis(layers):   从 QGIS 的 QgsVectorLayer 列表装载，用于插件运行时。
     layers 为 dict: { "BOITE": <QgsVectorLayer>, ... } 或 list of layers，
     每个 layer 通过 fields()/getFeatures() 提供属性(字段名=截断 dbf 名)。

装载后字段统一为截断名 dict，交由 FtthProject 装配拓扑。
"""

from __future__ import annotations

import os

from .model import FtthProject
from .field_map import LAYER_FILE_PREFIX

try:
    from dbfread import DBF
except Exception:  # pragma: no cover - 插件环境可能未装 dbfread
    DBF = None


def _normalize(row: dict) -> dict:
    """字符串字段去首尾空格，None 保留。"""
    out = {}
    for k, v in row.items():
        if isinstance(v, str):
            v = v.strip()
        out[k.strip().upper()] = v
    return out


def load_dbf(shape_dir: str, pm_filter: list[str] | None = None) -> FtthProject:
    """从包含 8 个 .dbf 的目录装载 FTTH 数据集。

    pm_filter: 可选 PM 编码列表，仅保留归属这些 PM 的局部成果(部分导出用)。
    """
    if DBF is None:
        raise RuntimeError("dbfread 未安装，无法离线读取 .dbf")
    proj = FtthProject()
    proj.source = shape_dir
    for layer, prefix in LAYER_FILE_PREFIX.items():
        dbf_path = os.path.join(shape_dir, prefix + ".dbf")
        if not os.path.exists(dbf_path):
            # 部分数据集可能缺某层(如 ZNRO/ZPM)，跳过而非报错
            continue
        dbf = DBF(dbf_path, encoding="utf-8")
        rows = [_normalize(dict(rec)) for rec in dbf]
        proj.add_records(layer, rows)
    if pm_filter:
        proj.filter_by_pm(pm_filter)
    return proj


def load_qgis(layers) -> FtthProject:
    """
    从 QGIS 图层装载。layers 支持:
      - dict: { "BOITE": <QgsVectorLayer>, ... }
      - list: [<QgsVectorLayer>, ...]  (按 layer.name() 匹配前缀)
    字段名使用 .dbf 截断名 (QGIS 读取 dbf 时即截断名)。
    """
    proj = FtthProject()
    proj.source = "qgis"

    def _layer_key(lyr) -> str:
        name = lyr.name().upper()
        for key in LAYER_FILE_PREFIX:
            if name.startswith(key):
                return key
        return name

    if isinstance(layers, dict):
        target = layers
    else:
        target = {_layer_key(l): l for l in layers}

    for layer_key, lyr in target.items():
        if layer_key not in LAYER_FILE_PREFIX:
            continue
        rows = []
        for feat in lyr.getFeatures():
            attrs = feat.attributes()
            flds = lyr.fields()
            row = {}
            for i in range(flds.count()):
                name = flds.field(i).name().strip().upper()
                val = attrs[i]
                if isinstance(val, str):
                    val = val.strip()
                row[name] = val
            rows.append(row)
        proj.add_records(layer_key, rows)
    return proj
