# -*- coding: utf-8 -*-
"""
Plans_de_Boite 光交箱图 — Sommaire 汇总 + 每箱体明细 sheet 生成器
=================================================================

官方模板 (EJA01_MRJ01_Plans_de_Boite.xlsx):
  - Sommaire 汇总 sheet:   标题 + 表头(Boitier|Type|Capacite|Fonction|Onglet) + 每箱体一行
  - 每箱体一张明细 sheet (sheet 名 = 箱体 CODE):
        标题(箱体CODE)
        Reference PM : xxx ............ Reference PTEC : yyy
        Adresse : zzz
        (空行)
        经过该箱的光缆清单:  [缆段CODE, "{CAPACITE} FO", ...]
        (空行)
        熔接矩阵表头:  Nom Cable | Tube | Fibre | Type | Fibre | Tube | Nom Cable
        C1  (配线盘标识)
        (纤芯级熔接明细 = 熔接计划，8 图层 Shape 不含 -> 占位说明)

Fonction / Capacite 派生规则 (已按真实数据校正):
  BPE -> Fonction="Fenetrage",  Capacite="{CAPACITE} FO"   (芯数)
  PBO -> Fonction="Extremite",   Capacite="{NB_LOGEMEN} prises" (户数)
  其它 -> Fonction=原 TYPE,      Capacite="{CAPACITE} FO"

注: 真实数据 PBO.CAPACITE=12(芯) 但 NB_LOGEMEN=10(户)，官方样本 PBO 容量写 "10 prises"，
    故 PBO 容量必须取 NB_LOGEMEN 而非 CAPACITE。
"""

from __future__ import annotations

import openpyxl
import re

from ..model import _s  # 复用 model 的安全字符串强转


def _safe_sheet(name: str, used: set[str]) -> str:
    """openpyxl sheet 名限制: <=31 字符，且不能含 []:*?/\\ 。做截断+清洗并去重。"""
    clean = re.sub(r"[\[\]:*?/\\]", "_", name)[:31]
    if not clean:
        clean = "Boite"
    base = clean
    i = 1
    while clean in used:
        suffix = f"_{i}"
        clean = base[: 31 - len(suffix)] + suffix
        i += 1
    used.add(clean)
    return clean


def _capacite_fo(cable: dict) -> str:
    """缆段容量 -> '{n} FO'。"""
    try:
        n = int(float(cable.get("CAPACITE") or 0))
    except (TypeError, ValueError):
        n = 0
    return f"{n} FO"


def build_boite_sommaire(project) -> tuple[list, list[list]]:
    """返回 (header_rows, data_rows)。header_rows 含标题行+表头行。"""
    pm = _s(project.pm_code)
    title = f"PLANS DE BOITE - {pm}"
    header = ["Boitier", "Type", "Capacite", "Fonction", "Onglet"]
    rows = []
    for code in sorted(project.boites.keys()):
        b = project.boites[code]
        btype = _s(b.get("TYPE"))
        try:
            cap = int(float(b.get("CAPACITE") or 0))
        except (TypeError, ValueError):
            cap = 0
        if btype == "PBO":
            # 容量取住户数(prises)，功能为终端
            try:
                log = int(float(b.get("NB_LOGEMEN") or 0))
            except (TypeError, ValueError):
                log = 0
            fonction = "Extremite"
            capacite_str = f"{log} prises"
        elif btype == "BPE":
            fonction = "Fenetrage"
            capacite_str = f"{cap} FO"
        else:
            fonction = btype or ""
            capacite_str = f"{cap} FO"
        rows.append([code, btype, capacite_str, fonction, code])
    return [title, header], rows


def build_boite_detail(project, boite_code: str) -> list[list]:
    """
    生成单个箱体的明细 sheet 行(按 append 顺序)。
    返回 rows: list[list]，含 标题 / Reference PM+PTEC / Adresse /
    经过该箱的光缆清单 / 熔接矩阵表头(C1 配线盘) / 熔接计划占位说明。
    """
    b = project.boites.get(boite_code)
    if b is None:
        return [[boite_code], ["(箱体不存在)"]]

    pm_ref = _s(b.get("REF_PM")) or _s(project.pm_code)
    ptc_ref = _s(b.get("CODE_PTC")) or ""
    adresse = _s(b.get("ADRESSSE")) or ""

    rows: list[list] = []
    rows.append([boite_code])  # 标题
    rows.append([
        f"Reference PM : {pm_ref}", None, None, None, None, None,
        f"Reference PTEC : {ptc_ref}",
    ])
    rows.append([f"Adresse : {adresse}"])
    rows.append([])  # 空行
    rows.append([])

    # 经过该箱的光缆清单: 所有直接相连的光缆(去重, 排序)
    project._build_adjacency()
    cable_codes: set[str] = set()
    for cab, _other in project._adj.get(boite_code, []):
        if cab:
            cable_codes.add(cab)
    for cab in sorted(cable_codes):
        cable = project.cables.get(cab, {})
        rows.append([cab, _capacite_fo(cable)])

    rows.append([])
    rows.append([])
    rows.append([])

    # 熔接矩阵表头 + 配线盘标识(C1 占位)
    rows.append(["Nom Cable", "Tube", "Fibre", "Type", "Fibre", "Tube", "Nom Cable"])
    rows.append(["C1", None, None, None, None, None, None])
    # 纤芯级熔接明细 = 熔接计划, 8 图层 Shape 不含 -> 诚实占位说明
    rows.append([
        "(熔接计划/纤芯级对接明细待补: 8 图层 Shape 仅含光缆拓扑与容量, "
        "不含 Plan de fusion 纤芯分配; 需用运营商熔接计划表回填 Tube/Fibre 矩阵)",
    ])
    return rows


def export_plans_de_boite_xlsx(project, out_path: str) -> str:
    """写出 Plans_de_Boite.xlsx: Sommaire 汇总 + 每箱体一张明细 sheet。"""
    headers, rows = build_boite_sommaire(project)
    wb = openpyxl.Workbook()
    used: set[str] = set()

    # Sommaire sheet
    ws = wb.active
    ws.title = _safe_sheet("Sommaire", used)
    ws.append([headers[0]])   # 标题行
    ws.append(headers[1])     # 表头行
    for r in rows:
        ws.append(r)

    # 每箱体明细 sheet
    for code in sorted(project.boites.keys()):
        detail = build_boite_detail(project, code)
        ds = wb.create_sheet(title=_safe_sheet(code, used))
        for r in detail:
            ds.append(r)

    wb.save(out_path)
    return out_path


def export_boite_sommaire_xlsx(project, out_path: str) -> str:
    """兼容别名: 旧调用方仍可用，现等价生成完整多 sheet 工作簿。"""
    return export_plans_de_boite_xlsx(project, out_path)
