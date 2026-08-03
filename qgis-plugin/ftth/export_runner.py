# -*- coding: utf-8 -*-
"""
FTTH 交付物导出运行器 (export_runner.py)
=========================================

封装「装载 -> 生成两表 -> 写 xlsx」全流程，供:
  - 离线校验脚本调用 (export_from_dbf)
  - QGIS 插件按钮调用 (export_from_qgis)
"""

from __future__ import annotations

import os

from .loader import load_dbf, load_qgis
from .deliverables import (
    export_boite_sommaire_xlsx,
    export_routes_optiques_xlsx,
)


def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (s or "ftth"))


def export_from_dbf(shape_dir: str, out_dir: str, prefix: str = "") -> dict:
    """从 Shape 目录装载并导出两表，返回输出路径 dict。"""
    os.makedirs(out_dir, exist_ok=True)
    proj = load_dbf(shape_dir)
    tag = _safe_name(prefix or os.path.basename(os.path.normpath(shape_dir)))
    boite_path = os.path.join(out_dir, f"{tag}_Plans_de_Boite.xlsx")
    routes_path = os.path.join(out_dir, f"{tag}_Routes_Optiques.xlsx")
    export_boite_sommaire_xlsx(proj, boite_path)
    export_routes_optiques_xlsx(proj, routes_path)
    return {
        "project": proj,
        "boite_sommaire": boite_path,
        "routes_optiques": routes_path,
        "summary": proj.summary(),
    }


def export_from_qgis(layers, out_dir: str, prefix: str = "qgis") -> dict:
    """从 QGIS 图层装载并导出两表。"""
    os.makedirs(out_dir, exist_ok=True)
    proj = load_qgis(layers)
    tag = _safe_name(prefix)
    boite_path = os.path.join(out_dir, f"{tag}_Plans_de_Boite.xlsx")
    routes_path = os.path.join(out_dir, f"{tag}_Routes_Optiques.xlsx")
    export_boite_sommaire_xlsx(proj, boite_path)
    export_routes_optiques_xlsx(proj, routes_path)
    return {
        "project": proj,
        "boite_sommaire": boite_path,
        "routes_optiques": routes_path,
        "summary": proj.summary(),
    }
