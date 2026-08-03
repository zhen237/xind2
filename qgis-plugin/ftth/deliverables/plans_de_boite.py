# -*- coding: utf-8 -*-
"""
Plans_de_Boite 光交箱图 — Sommaire 汇总表生成器
================================================

官方模板 (EJA01_MRJ01_Plans_de_Boite.xlsx → Sommaire):
  标题行: PLANS DE BOITE - {PM}
  表头:   Boitier | Type | Capacite | Fonction | Onglet
  每行:   箱体编码 | 类型 | 容量(FO) | 功能 | 对应分表名

v1 范围: 仅生成结构化 Sommaire 汇总表 (与官方格式逐列一致)。
单箱熔接盘图(每箱一张 sheet 的图形化布局)属图形绘制，列入后续阶段。

Fonction 派生规则:
  BPE / PBO -> "Fenetrage" (熔接盘成端)
  其他 TYPE -> 原 TYPE 值
"""

from __future__ import annotations

import openpyxl


def build_boite_sommaire(project) -> tuple[list[str], list[list]]:
    """返回 (header_rows, data_rows)。header_rows 含标题行+表头行。"""
    pm = project.pm_code or ""
    title = f"PLANS DE BOITE - {pm}"
    header = ["Boitier", "Type", "Capacite", "Fonction", "Onglet"]
    rows = []
    # 按 CODE 排序，稳定输出
    for code in sorted(project.boites.keys()):
        b = project.boites[code]
        btype = (b.get("TYPE") or "").strip()
        try:
            cap = int(float(b.get("CAPACITE") or 0))
        except (TypeError, ValueError):
            cap = 0
        fonction = "Fenetrage" if btype in ("BPE", "PBO") else (btype or "")
        rows.append([code, btype, f"{cap} FO", fonction, code])
    return [title, header], rows


def export_boite_sommaire_xlsx(project, out_path: str) -> str:
    headers, rows = build_boite_sommaire(project)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sommaire"
    ws.append([headers[0]])        # 标题行
    ws.append(headers[1])          # 表头行
    for r in rows:
        ws.append(r)
    wb.save(out_path)
    return out_path
