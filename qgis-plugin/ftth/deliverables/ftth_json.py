# -*- coding: utf-8 -*-
"""
FTTH 数据导出为前端可用的 JSON (供 M03 前端 S1 模块读取)
========================================================

把 FtthProject 汇总 + 每个箱体的真值(类型/容量/功能/归属PM/户数/坐标/地址/PTEC)
导出成一份扁平 JSON，落到前端 public/ 后由 Vue 页面 fetch 读取。
这样无需改造 Java 后端即可让 Web 端看到 S1 成果(演示链路最短路径)。

注: 纤芯级熔接明细(Plan de fusion) 不在 8 图层 Shape 中，此处不含。
"""

from __future__ import annotations

import json
import datetime

from ..model import _s


def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def build_ftth_json(project) -> dict:
    s = project.summary()
    pm_list = project.pm_codes()
    boites = []
    for code in sorted(project.boites.keys()):
        b = project.boites[code]
        btype = _s(b.get("TYPE"))
        try:
            cap = int(float(b.get("CAPACITE") or 0))
        except (TypeError, ValueError):
            cap = 0
        if btype == "PBO":
            try:
                log = int(float(b.get("NB_LOGEMEN") or 0))
            except (TypeError, ValueError):
                log = 0
            fonction = "Extremite"
        elif btype == "BPE":
            fonction = "Fenetrage"
            log = project.logements_of_boite(code)
        else:
            fonction = btype or ""
            log = project.logements_of_boite(code)
        pm = project.pm_of_boite(code)
        boites.append({
            "code": code,
            "type": btype,
            "capacite_fo": cap,
            "fonction": fonction,
            "pm": pm,
            "ref_pm_raw": _s(b.get("REF_PM")),
            "logements": log,
            "x": _num(b.get("X")),
            "y": _num(b.get("Y")),
            "adresse": _s(b.get("ADRESSSE")),
            "ptec": _s(b.get("CODE_PTC")),
        })
    # ---- 光缆拓扑 (箱体↔箱体 / 箱体↔PM站点 的连接关系) ----
    # 数据来自 CABLE.ORIGINE -> CABLE.EXTREMITE；端点坐标回退到 BOITE/SITE 任一存在的图层。
    # 每根缆预解析 from/to 经纬度，前端直接连 polyline，无需再查箱体坐标。
    known_pm = set(pm_list)
    cables = []
    for code in sorted(project.cables.keys()):
        c = project.cables[code]
        o = (c.get("ORIGINE") or "").strip()
        e = (c.get("EXTREMITE") or "").strip()
        op = project.node_position(o)
        ep = project.node_position(e)
        if not op or not ep:
            continue  # 端点无法定位则跳过，避免画断线
        try:
            cap = int(float(c.get("CAPACITE") or 0))
        except (TypeError, ValueError):
            cap = 0
        try:
            lng = float(c.get("LONGUEUR") or 0)
        except (TypeError, ValueError):
            lng = 0.0
        pm = _s(c.get("REF_PM"))
        if pm and pm not in known_pm:
            pm = ""  # 归一化脏 PM (如 JAD-MAR1076)，避免前端分组出错
        cables.append({
            "code": code,
            "nom": _s(c.get("NOM")),
            "origine": o,
            "extremite": e,
            "from": [round(op[0], 6), round(op[1], 6)],
            "to": [round(ep[0], 6), round(ep[1], 6)],
            "capacite_fo": cap,
            "longueur": round(lng, 3),
            "type_cable": _s(c.get("TYPE_CABLE")),
            "pm": pm,
        })

    # ---- PM 站点根节点 (OLT/NRO 局站) ----
    sites = []
    for code in sorted(project.sites.keys()):
        st = project.sites[code]
        try:
            sx = float(st.get("X")); sy = float(st.get("Y"))
        except (TypeError, ValueError):
            continue
        sites.append({
            "code": code,
            "type": _s(st.get("TYPE")),
            "x": round(sx, 6),
            "y": round(sy, 6),
            "adresse": _s(st.get("ADRESSSE")),
        })

    return {
        "source": project.source,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "summary": s,
        "pm_list": pm_list,
        "boites": boites,
        "cables": cables,
        "sites": sites,
    }


def export_ftth_json(project, out_path: str) -> str:
    data = build_ftth_json(project)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_path
