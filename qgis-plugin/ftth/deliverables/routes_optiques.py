# -*- coding: utf-8 -*-
"""
Routes_Optiques 光路由表生成器 (v1)
====================================

官方模板 (EJA01_MRJ01_Routes_Optiques.xlsx) 列结构:
  PM | Destination | Long.
  | Tiroir                         (PM 侧熔接盘)
  | [F | Tiroir | Cable | BPE+Long.Inter. | CAS] ×N段   (逐段光缆路由)
  | [F | Tiroir | Cable]          (终段 ABONNE 到用户)

CAS 连接类型:
  PASSAGE   过路箱(中间节点)
  EPISSURE  终端熔接(到达 Destination 箱体)
  ABONNE    到用户(终段，无 BPE/CAS 列)

v1 路由算法 (数据驱动，忠实于 Shape 拓扑):
  对每个住户(IMB)，其 BPE_CODE 即所服务的箱体(Destination)；
  经该箱体的 CABLE_AMON 向上追溯光缆链直到 PM 根节点；
  每段光缆作为一行中的一段 hop，长度取自 CABLE.LONGUEUR；
  Long. = 链上各段光缆长度之和。

说明(v1 局限):
  - 首列 Tiroir(PM 侧熔接盘)使用确定性占位 "TDI01-{PM后缀}"，
    真实 TDIxx-MRJxx 盘位分配需熔接计划数据(Shape 不含)，后续版本补充。
  - 仅生成结构化路由矩阵；单纤芯级熔接盘端口分配列入后续阶段。
"""

from __future__ import annotations

import openpyxl


def _pm_tray_placeholder(pm_code: str) -> str:
    suffix = (pm_code or "").split("-")[-1]
    return f"TDI01-{suffix}" if suffix else "TDI01"


def build_routes_optiques(project) -> tuple[list[str], list[list]]:
    """
    返回 (header, rows)。
    header: 依据所有路由中最大光缆段数动态生成，保证行对齐。
    rows:   每行 = 一根光纤(PM -> ... -> Destination -> ABONNE)的完整路由。
    """
    # 1) 按 BPE_CODE 归组住户
    groups: dict[str, list] = {}
    for imb in project.imbs.values():
        box = (imb.get("BPE_CODE") or "").strip()
        if box:
            groups.setdefault(box, []).append(imb)

    # 2) 计算各箱路由骨架 + 光纤数
    skeletons = {}
    max_cables = 0
    for box in sorted(groups.keys()):
        sk = project.route_for_boite(box)
        if sk is None:
            continue
        skeletons[box] = sk
        max_cables = max(max_cables, len(sk["hops"]))

    # 3) 构建表头 (按官方列模式)
    header = ["PM", "Destination", "Long.", "Tiroir"]
    for _ in range(max_cables):
        header += ["F", "Tiroir", "Cable", "BPE+Long.Inter.", "CAS"]
    header += ["F", "Tiroir", "Cable"]  # 终段 ABONNE

    # 4) 逐箱逐纤生成行
    rows = []
    for box in sorted(skeletons.keys()):
        sk = skeletons[box]
        pm = sk["pm"]
        dest = sk["destination"]
        total = round(sk["total_length"], 2)
        n_fibers = len(groups[box])
        tray = _pm_tray_placeholder(pm)
        for f in range(1, n_fibers + 1):
            cells = [pm, dest, total, tray]
            for cable, to_box, length, cas in sk["hops"]:
                cells += [f, 1, cable, f"{to_box} | {length:.3f}ml", cas]
            cells += [f, 1, "ABONNE"]
            # 补齐到表头宽度
            while len(cells) < len(header):
                cells.append("")
            rows.append(cells)

    return header, rows


def export_routes_optiques_xlsx(project, out_path: str) -> str:
    header, rows = build_routes_optiques(project)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Routes_Optiques"
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(out_path)
    return out_path
