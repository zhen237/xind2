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
    export_plans_de_boite_xlsx,
    export_routes_optiques_xlsx,
    export_plan_de_baie_xlsx,
    export_synoptique_xlsx,
    export_ftth_json,
)


def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (s or "ftth"))


def _export_all(proj, out_dir: str, tag: str) -> dict:
    """写出全部四类交付物(光交箱汇总/光路由表/机柜熔接盘图/系统图)，返回路径 dict。"""
    os.makedirs(out_dir, exist_ok=True)
    boite_path = os.path.join(out_dir, f"{tag}_Plans_de_Boite.xlsx")
    routes_path = os.path.join(out_dir, f"{tag}_Routes_Optiques.xlsx")
    export_plans_de_boite_xlsx(proj, boite_path)
    export_routes_optiques_xlsx(proj, routes_path)

    plan_de_baie = {}
    synoptique = {}
    for pm in proj.pm_codes():
        pm_safe = _safe_name(pm)
        pdb_path = os.path.join(out_dir, f"{tag}_Plan_de_Baie_{pm_safe}.xlsx")
        syn_path = os.path.join(out_dir, f"{tag}_Synoptique_{pm_safe}.xlsx")
        export_plan_de_baie_xlsx(proj, pdb_path, pm)
        export_synoptique_xlsx(proj, syn_path, pm)
        plan_de_baie[pm] = pdb_path
        synoptique[pm] = syn_path

    # 前端 S1 模块可用 JSON (箱体点位 + 汇总)
    ftth_json_path = os.path.join(out_dir, f"{tag}_ftth-data.json")
    export_ftth_json(proj, ftth_json_path)

    return {
        "project": proj,
        "boite_sommaire": boite_path,
        "routes_optiques": routes_path,
        "plan_de_baie": plan_de_baie,
        "synoptique": synoptique,
        "ftth_json": ftth_json_path,
        "summary": proj.summary(),
    }


def export_from_dbf(shape_dir: str, out_dir: str, prefix: str = "") -> dict:
    """从 Shape 目录装载并导出四类交付物，返回输出路径 dict。"""
    proj = load_dbf(shape_dir)
    tag = _safe_name(prefix or os.path.basename(os.path.normpath(shape_dir)))
    return _export_all(proj, out_dir, tag)


def export_from_qgis(layers, out_dir: str, prefix: str = "qgis") -> dict:
    """从 QGIS 图层装载并导出四类交付物。"""
    proj = load_qgis(layers)
    tag = _safe_name(prefix)
    return _export_all(proj, out_dir, tag)
