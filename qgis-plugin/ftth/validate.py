# -*- coding: utf-8 -*-
"""
FTTH 数据自检器 (validate.py)
=============================

复用 S3 子赛题「图层表字段说明和数据校验规则.xlsx」中的行业标准校验规则，
对 FTTH 数据集(竣工/设计)做智能化审查，输出结构化报告。

覆盖 45 条规则中的可计算子集:
  - 文件完整性 / 命名规范 (1.x)
  - 坐标系一致性 (2)
  - 空图层检查 (3)
  - 图层字段非空 + CODE 唯一 (4.x)
  - 引用完整性(孤立性) (5.x)
  - 几何一致性: 点面包含 + 端点重合 (6.3-6.6, 需 pyshp 读 .shp)
  - 容量约束 (7.1/7.2)

对依赖多边形相交精确计算的 6.1/6.2，本环境仅做包围盒近似并明确标注。

anomalies 输出:
  validate_project(...) 返回的 dict 中新增 "anomalies" 字段，结构为
  { 图层名: [异常要素 CODE 列表] }，供 QGIS 画布按要素高亮使用。

用法:
  from ftth.validate import validate_project
  report = validate_project(project, shape_dir=".../Shape")  # shape_dir 可选(几何类需要)
  anomalies = report["anomalies"]   # {"BOITE": [...], "CABLE": [...], ...}
"""

from __future__ import annotations

import datetime
import os
from collections import defaultdict

# 字段名漂移别名: 校验规则 xlsx 列的名字 -> 实际 .dbf 截断字段名
# (xlsx 里 >10 字符的字段按前 10 字符匹配；个别拼写漂移需显式映射)
FIELD_ALIASES = {
    "NB_LOGEMENT": "NB_LOGEMEN",   # xlsx 拼写 vs dbf 实际
}

# 自动修复建议: 规则 id(可前缀匹配) -> 给用户的 actionable 修复指引。
# 前端「数据自检」面板按此展示「建议」一列，指导用户就地修正。
SUGGESTIONS = {
    "1.": "检查对应 .shp/.dbf/.shx 是否齐全并符合命名规范，缺失图层需回到采集端补全后重新导出。",
    "2": "统一各图层 .prj 坐标系(建议项目统一 EPSG，如 RGF93/Lambert)，重投影后重新导出。",
    "3": "空图层需在数据源补齐要素，或将不需要的图层从交付清单中移除。",
    "4.": "规范字段为空或缺失：回填字段值；字段名缺失多为 dbf 10 字符截断导致，请按字段别名映射在源端校正。",
    "5.1": "核对 SITE(PM) 与 ZPM 的 CODE 是否一一对应，修正命名或补建缺失的 ZPM/SITE。",
    "5.2": "孤立 PBO 的 REF_PM 指向了不存在的 PM；无 PBO 的 PM 需增补至少一个 PBO 箱体。",
    "5.3": "配线缆 REF_PM 必须对应已建 SITE(PM)；无配线缆的 PM 需补画配线缆段。",
    "5.4": "缆端点指向不存在的箱体/站点(幽灵引用)，或节点未被任何配线缆连接；修正缆端点 CODE，或补连配线缆。",
    "6.1": "ZNRO 多边形包围盒重叠(近似判定)；用 shapely 精确判定，确认是否为相切或真实相交。",
    "6.2": "ZPM 多边形包围盒重叠(近似判定)；用 shapely 精确判定，确认是否为相切或真实相交。",
    "6.3": "PM 站点坐标不在对应 ZPM 多边形内；核对坐标或修正 ZPM 边界。",
    "6.4": "PBO 坐标不在归属 ZPM 多边形内；核对坐标或修正 ZPM 边界。",
    "6.5": "配线缆端点越界归属 ZPM；核对缆端点坐标。",
    "6.6": "缆端点坐标与引用节点不重合或存在自环(ORIGINE=EXTREMITE)；修正端点坐标，删除自环缆。",
    "7.1": "PBO 覆盖户数(NB_FIBRE_UTIL)超过端口数(CAPACITE)；扩容端口或调整覆盖规划。",
    "7.2": "部分 PM 上游配线缆芯数不足以覆盖其 PBO 端口；增补配线缆芯或调整 PBO 挂接。",
}


def _pick_suggestion(rid: str) -> str:
    """按规则 id 最长前缀匹配返回修复建议；无匹配返回空串。"""
    best = ""
    for key in sorted(SUGGESTIONS, key=len, reverse=True):
        if rid.startswith(key):
            return SUGGESTIONS[key]
    return best


def _trunc(name: str) -> str:
    return name[:10]


def _match_field(required: str, actual_fields: set) -> str | None:
    """在真实 dbf 字段集合里匹配规则要求的字段名。

    策略: 精确 -> 10字符截断 -> 别名 -> 别名截断。
    返回命中的真实字段名；都没命中发现 -> None。
    """
    if required in actual_fields:
        return required
    t = _trunc(required)
    if t in actual_fields:
        return t
    alias = FIELD_ALIASES.get(required)
    if alias and alias in actual_fields:
        return alias
    if alias:
        ta = _trunc(alias)
        if ta in actual_fields:
            return ta
    return None


def _num(v):
    """把 dbf 数值字段(可能 int/float/str/None)安全转 float；失败返回 None。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ----------------------------------------------------------------------------
# 规则结果容器
# ----------------------------------------------------------------------------
class Rule:
    def __init__(self, rid, category, name, severity="error"):
        self.rid = rid
        self.category = category
        self.name = name
        self.severity = severity        # error | warn
        self.status = "pass"            # pass | fail | skip | warn
        self.detail = ""
        self.samples = []               # 失败/异常样本(限量)
        self.suggestion = ""            # 自动修复建议(失败/警告时填充)

    def to_dict(self):
        return {
            "id": self.rid,
            "category": self.category,
            "name": self.name,
            "severity": self.severity,
            "status": self.status,
            "detail": self.detail,
            "samples": self.samples[:20],
            "suggestion": self.suggestion,
        }


def _actual_fields(records: dict) -> set:
    """取某图层实际出现的字段名集合(取第一条记录的 key)。"""
    if not records:
        return set()
    return set(next(iter(records.values())).keys())


# ============================================================================
# 各规则组实现
# ============================================================================

def _check_files_and_naming(project, shape_dir, rules, anomalies):
    """1.x 文件完整性 + 命名规范 + 2 坐标系一致性 + 3 空图层"""
    layer_keywords = ["IMB", "SITE", "BOITE", "CABLE", "PTECH",
                      "INFRASTRUCTURE", "ZNRO", "ZPM"]
    if not shape_dir or not os.path.isdir(shape_dir):
        r = Rule("1.x", "文件完整性检查", "图层文件完整性/命名/坐标系/空图层")
        r.status = "skip"
        r.detail = "未提供 Shape 目录，文件级检查跳过(数据已通过 loader 装载，隐含文件存在)。"
        rules.append(r)
        return

    # 1.1 8 图层文件齐全 + 1.2-1.9 命名规范
    present = {}
    for kw in layer_keywords:
        shp = os.path.join(shape_dir, f"{kw}.shp")
        dbf = os.path.join(shape_dir, f"{kw}.dbf")
        shx = os.path.join(shape_dir, f"{kw}.shx")
        ok = os.path.exists(shp) and os.path.exists(dbf) and os.path.exists(shx)
        present[kw] = ok
        r = Rule(f"1.{layer_keywords.index(kw)+1}", "文件完整性检查",
                 f"{kw} 图层文件齐全(.shp/.dbf/.shx)")
        if ok:
            r.status = "pass"
            r.detail = f"{kw}.shp/.dbf/.shx 均存在"
        else:
            r.status = "fail"
            r.detail = f"{kw} 图层缺少配套文件"
            # 整层缺失：记录该层(以层名作为占位，便于画布提示层缺失)
            anomalies[kw].add("__LAYER_MISSING__")
        rules.append(r)

    # 2 坐标系一致性
    r = Rule("2", "坐标系一致性检查", "各图层 .prj 坐标系一致")
    prjs = {}
    for kw in layer_keywords:
        p = os.path.join(shape_dir, f"{kw}.prj")
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="ignore") as f:
                prjs[kw] = f.read().strip()
    if prjs and len(set(prjs.values())) == 1:
        r.status = "pass"
        r.detail = f"全部 {len(prjs)} 个图层坐标系一致: {prjs[layer_keywords[0]]}"
    elif prjs:
        r.status = "fail"
        r.detail = "存在不同坐标系: " + "; ".join(f"{k}={v[:30]}" for k, v in prjs.items())
        r.samples = [f"{k}: {v}" for k, v in prjs.items() if v != prjs[layer_keywords[0]]]
    else:
        r.status = "skip"
        r.detail = "未找到 .prj 文件"
    rules.append(r)

    # 3 空图层检查
    store_map = {"IMB": project.imbs, "SITE": project.sites, "BOITE": project.boites,
                 "CABLE": project.cables, "PTECH": project.ptechs,
                 "INFRASTRUCTURE": project.infras, "ZNRO": project.znro, "ZPM": project.zpm}
    r = Rule("3", "空图层检查", "8 图层均至少有 1 条数据")
    empty = [kw for kw in layer_keywords if len(store_map[kw]) == 0]
    if not empty:
        r.status = "pass"
        r.detail = "全部图层均有数据: " + ", ".join(
            f"{kw}={len(store_map[kw])}" for kw in layer_keywords)
    else:
        r.status = "fail"
        r.detail = "存在空图层: " + ", ".join(empty)
        for kw in empty:
            anomalies[kw].add("__LAYER_EMPTY__")
    rules.append(r)


def _check_fields(project, rules, anomalies):
    """4.x 图层字段非空 + CODE 唯一"""
    # (图层名, 规范要求非空字段列表) —— 取自校验规则 xlsx 4.1/4.3/4.5/4.7/4.9/4.11/4.13/4.15
    field_specs = {
        "IMB": ["CODE", "REF_PLAQUE", "REGION", "PROVINCE", "VILLE", "COMMUNE",
                "CODE_POSTAL", "NUMERO_VOIE", "TYPE_VOIE", "CODE_VOIE", "TYPE_BATIMENT",
                "TYPE_CLIENT", "NB_LOC_RES", "NB_LOC_PRO", "NB_LOC_TOT", "RACCORDEMENT",
                "STATUT", "NB_ETAGE", "COL_MONTANTE", "SOUS_SOL", "SOUS_SOL_COMMUN",
                "BPE_CODE", "X", "Y"],
        "BOITE": ["CODE", "CODE_PTC", "REF_PLAQUE", "REF_NRO", "REF_PM", "TYPE",
                  "TYPE_STRUCTURE", "MODE_POSE", "CAPACITE", "NB_LOGEMENT", "NB_SPLICES",
                  "NB_FIBRE_UTIL", "FABRIQUANT", "REF_BPE", "NB_CASSETTES_MAX",
                  "CABLE_AMONT", "STATUT", "PROPRIETAIRE", "GESTIONNAIRE", "ADRESSSE",
                  "VILLE", "CODE_POSTAL", "X", "Y"],
        "CABLE": ["CODE", "REF_PLAQUE", "REF_NRO", "REF_PM", "CODE_INFRA", "ORIGINE",
                  "EXTREMITE", "TYPE_CABLE", "DIAMETRE", "MODE_POSE", "CAPACITE", "MODULO",
                  "FABRIQUANT", "REF_PRODUIT", "TYPE_FIBRE", "NB_FIBRE_UTIL",
                  "NB_FIBRE_DISP", "STATUT", "PROPRIETAIRE", "GESTIONNAIRE", "TYPE_PROP",
                  "LONGUEUR"],
        "PTECH": ["CODE", "REF_PLAQUE", "TYPE", "NATURE", "HAUTEUR_APPUI", "TYPE_APPUI",
                  "EFFORT_APPUI", "NB_BOITIERS", "STATUT", "PROPRIETAIRE", "GESTIONNAIRE",
                  "ADRESSSE", "VILLE", "CODE_POSTAL", "X", "Y"],
        "INFRASTRUCTURE": ["CODE", "REF_PLAQUE", "ORIGINE", "EXTREMITE", "COMPOSITION",
                           "TYPE", "TYPE_LOG", "STATUT", "PROPRIETAIRE", "GESTIONNAIRE",
                           "LONGUEUR"],
        "ZPM": ["CODE", "REF_PLAQUE", "REF_NRO", "REF_PM", "STATUT", "NB_PRISES"],
        "ZNRO": ["CODE", "REF_PLAQUE", "REF_NRO", "STATUT", "NB_PRISES"],
        "SITE": ["CODE", "REF_PLAQUE", "REF_NRO", "TYPE", "FABRIQUANT", "REF_PRODUIT",
                 "MODE_POSE", "STATUT", "PROPRIETAIRE", "GESTIONNAIRE", "ADRESSSE",
                 "COMMUNE", "CODE_POSTAL", "X", "Y"],
    }
    store_map = {"IMB": project.imbs, "SITE": project.sites, "BOITE": project.boites,
                 "CABLE": project.cables, "PTECH": project.ptechs,
                 "INFRASTRUCTURE": project.infras, "ZNRO": project.znro, "ZPM": project.zpm}

    for layer, required in field_specs.items():
        recs = store_map[layer]
        actual = _actual_fields(recs)
        # 4.x.1 字段存在且值非空
        r = Rule(f"4.{list(field_specs).index(layer)+1}a", "图层字段检查",
                 f"{layer} 规范字段非空")
        missing_fields = []     # 规范列出但实际图层没有的字段(信息级)
        empty_samples = defaultdict(list)
        if not recs:
            r.status = "skip"
            r.detail = f"{layer} 图层为空，跳过字段检查"
            rules.append(r)
            continue
        for req in required:
            hit = _match_field(req, actual)
            if hit is None:
                missing_fields.append(req)
                continue
            for code, row in recs.items():
                val = row.get(hit)
                if val is None or str(val).strip() == "":
                    empty_samples[req].append(code)
        if missing_fields:
            # 字段缺失多为截断/命名偏差，信息级提示，不计入失败
            r.status = "warn"
            r.detail = (f"字段非空检查通过；但规范列出 {len(missing_fields)} 个字段未在"
                        f"本图层出现(可能为截断/命名偏差): {', '.join(missing_fields)}")
        else:
            r.detail = f"{layer} 全部 {len(required)} 个规范字段存在且非空"
        if empty_samples:
            r.status = "fail"
            r.detail = (f"{layer} 存在空值字段: " +
                        "; ".join(f"{k}({len(v)}条)" for k, v in empty_samples.items()))
            r.samples = [f"{k}: {v[:5]}" for k, v in empty_samples.items()]
            # 异常要素归属本图层
            for codes in empty_samples.values():
                anomalies[layer].update(codes)
        rules.append(r)

        # 4.x.2 CODE 唯一
        r2 = Rule(f"4.{list(field_specs).index(layer)+1}b", "图层字段检查",
                  f"{layer} CODE 字段唯一")
        seen = defaultdict(list)
        for code, row in recs.items():
            c = (row.get("CODE") or "").strip()
            if c:
                seen[c].append(code)
        dups = {c: v for c, v in seen.items() if len(v) > 1}
        if dups:
            r2.status = "fail"
            r2.detail = f"{layer} 存在 {len(dups)} 个重复 CODE"
            r2.samples = [f"{c}: {v[:5]}" for c, v in list(dups.items())[:10]]
            anomalies[layer].update(dups.keys())
        else:
            r2.status = "pass"
            r2.detail = f"{layer} 全部 {len(recs)} 条 CODE 唯一"
        rules.append(r2)


def _check_isolation(project, rules, anomalies):
    """5.x 引用完整性(孤立性)双向检查"""
    boites = project.boites
    sites = project.sites
    cables = project.cables
    zpm = project.zpm

    pm_sites = {c: s for c, s in sites.items() if (s.get("TYPE") or "").strip() == "PM"}
    pbo = {c: b for c, b in boites.items() if (b.get("TYPE") or "").strip() == "PBO"}
    bpe = {c: b for c, b in boites.items() if (b.get("TYPE") or "").strip() == "BPE"}
    dist_cables = {c: k for c, k in cables.items()
                   if (k.get("TYPE_CABLE") or "").strip() == "DISTRIBUTION"}

    # 5.1 SITE(PM) <-> ZPM 双向
    r = Rule("5.1", "孤立性检查", "SITE(PM) 与 ZPM 双向对应 (SITE.CODE=ZPM.CODE)")
    pm_codes = set(pm_sites)
    zpm_codes = set(zpm)
    only_pm = pm_codes - zpm_codes
    only_zpm = zpm_codes - pm_codes
    if not only_pm and not only_zpm:
        r.status = "pass"
        r.detail = f"PM 站点 {len(pm_codes)} 个与 ZPM {len(zpm_codes)} 个一一对应"
    else:
        r.status = "fail"
        r.detail = (f"不一致: 仅在SITE(PM)出现 {sorted(only_pm)}; "
                    f"仅在ZPM出现 {sorted(only_zpm)}")
        r.samples = list(only_pm)[:10] + list(only_zpm)[:10]
        anomalies["SITE"].update(only_pm)
        anomalies["ZPM"].update(only_zpm)
    rules.append(r)

    # 5.2 PBO.REF_PM <-> SITE(PM)
    r = Rule("5.2", "孤立性检查", "PBO.REF_PM 必须对应 SITE(PM)，且每个PM至少有1个PBO")
    orphan_pbo = [c for c, b in pbo.items()
                  if (b.get("REF_PM") or "").strip() not in pm_codes]
    pm_without_pbo = [pm for pm in pm_codes
                      if not any((b.get("REF_PM") or "").strip() == pm for b in pbo.values())]
    if not orphan_pbo and not pm_without_pbo:
        r.status = "pass"
        r.detail = f"全部 {len(pbo)} 个 PBO 归属合法 PM；每个 PM 均有 PBO"
    else:
        r.status = "fail"
        r.detail = (f"孤立 PBO(REF_PM 无效) {len(orphan_pbo)} 个; "
                    f"无 PBO 的 PM {len(pm_without_pbo)} 个")
        r.samples = (orphan_pbo[:10] + [f"PM无PBO:{p}" for p in pm_without_pbo[:10]])
        anomalies["BOITE"].update(orphan_pbo)
        for s in pm_without_pbo:
            anomalies["SITE"].add(s)
    rules.append(r)

    # 5.3 DISTRIBUTION 缆 REF_PM <-> SITE(PM)
    r = Rule("5.3", "孤立性检查",
             "DISTRIBUTION 缆 REF_PM 必须对应 SITE(PM)，且每个PM至少有1条")
    orphan_cab = [c for c, k in dist_cables.items()
                  if (k.get("REF_PM") or "").strip() not in pm_codes]
    pm_without_cab = [pm for pm in pm_codes
                      if not any((k.get("REF_PM") or "").strip() == pm
                                 for k in dist_cables.values())]
    if not orphan_cab and not pm_without_cab:
        r.status = "pass"
        r.detail = f"全部 {len(dist_cables)} 条配线缆归属合法 PM；每个 PM 均有配线缆"
    else:
        r.status = "fail"
        r.detail = (f"REF_PM 无效配线缆 {len(orphan_cab)} 条; "
                    f"无配线缆的 PM {len(pm_without_cab)} 个")
        r.samples = (orphan_cab[:10] + [f"PM无缆:{p}" for p in pm_without_cab[:10]])
        anomalies["CABLE"].update(orphan_cab)
        for s in pm_without_cab:
            anomalies["SITE"].add(s)
    rules.append(r)

    # 5.4 缆端点 <-> 箱体/站点 双向
    r = Rule("5.4", "孤立性检查",
             "缆端点(全部类型)须解析到 BOITE/SITE；节点须出现在 DISTRIBUTION 缆端点(规范)")
    node_codes = set(boites) | set(pm_sites)
    # 正向: 所有缆类型的端点都必须解析到已知节点(抓幽灵引用如 JAD-MAR1076)
    unresolved_ends = []
    for c, k in cables.items():
        o = (k.get("ORIGINE") or "").strip()
        e = (k.get("EXTREMITE") or "").strip()
        if o and o not in node_codes:
            unresolved_ends.append(f"{c}.ORIGINE={o}")
        if e and e not in node_codes:
            unresolved_ends.append(f"{c}.EXTREMITE={e}")
    # 逆向: 按规范, 每个节点至少出现在一条 DISTRIBUTION 缆端点
    covered_dist = set()
    for k in dist_cables.values():
        covered_dist.add((k.get("ORIGINE") or "").strip())
        covered_dist.add((k.get("EXTREMITE") or "").strip())
    # 辅助: 非 distribution 缆连接的节点(用于孤立项注解, 避免误报)
    covered_other = set()
    for k in cables.values():
        if (k.get("TYPE_CABLE") or "").strip() == "DISTRIBUTION":
            continue
        covered_other.add((k.get("ORIGINE") or "").strip())
        covered_other.add((k.get("EXTREMITE") or "").strip())
    orphan_note = []
    orphan_isolated = []   # 完全孤立(任何缆型都不连接) -> 才纳入高亮
    for c in node_codes:
        if c not in covered_dist:
            if c in covered_other:
                orphan_note.append(f"{c}(经非配线缆连接)")
            else:
                orphan_note.append(f"{c}(完全孤立)")
                orphan_isolated.append(c)
    if not unresolved_ends and not orphan_note:
        r.status = "pass"
        r.detail = (f"全部缆端点解析正常；{len(node_codes)} 个节点均被配线缆连接")
    else:
        r.status = "fail"
        r.detail = (f"端点无法解析 {len(unresolved_ends)} 处(幽灵引用); "
                    f"未出现在配线缆端点的节点 {len(orphan_note)} 个 "
                    f"(其中经其他缆型连接的为规范范围外连接，不计入异常高亮)")
        r.samples = (unresolved_ends[:10] + orphan_note[:10])
        for s in unresolved_ends:
            # 形如 "CABLE.ORIGINE=NODE" -> 缆 CODE 归 CABLE，NODE 归 BOITE/SITE 候选
            left, _, node = s.partition("=")
            cable_code = left.split(".", 1)[0].strip()
            if cable_code:
                anomalies["CABLE"].add(cable_code)
            node = node.strip()
            if node:
                anomalies["BOITE"].add(node)
                anomalies["SITE"].add(node)
        # 仅完全孤立的节点纳入高亮(经其他缆型连接的属规范范围外，非失败)
        for c in orphan_isolated:
            anomalies["BOITE"].add(c)
            anomalies["SITE"].add(c)
    rules.append(r)


# ---- 几何工具 (pyshp) ----
def _point_in_polygon(lon, lat, points):
    """射线法判断点是否在多边形内(points: [(x,y),...])。"""
    n = len(points)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = points[i][0], points[i][1]
        xj, yj = points[j][0], points[j][1]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def _load_polygons(shape_dir, layer):
    """读 .shp 多边形, 返回 {CODE: [points...]}。失败返回 None。"""
    try:
        import shapefile
    except ImportError:
        return None
    path = os.path.join(shape_dir, f"{layer}.shp")
    if not os.path.exists(path):
        return None
    sr = shapefile.Reader(path)
    fields = [f[0] for f in sr.fields[1:]]
    code_idx = fields.index("CODE") if "CODE" in fields else 0
    out = {}
    for rec, shp in zip(sr.iterRecords(), sr.iterShapes()):
        code = str(rec[code_idx]).strip()
        pts = list(shp.points)
        if pts:
            out[code] = pts
    sr.close()
    return out


def _load_cable_endpoints(shape_dir):
    """读 CABLE.shp, 返回 {CODE: (first_pt, last_pt)}。失败返回 None。"""
    try:
        import shapefile
    except ImportError:
        return None
    path = os.path.join(shape_dir, "CABLE.shp")
    if not os.path.exists(path):
        return None
    sr = shapefile.Reader(path)
    fields = [f[0] for f in sr.fields[1:]]
    code_idx = fields.index("CODE") if "CODE" in fields else 0
    out = {}
    for rec, shp in zip(sr.iterRecords(), sr.iterShapes()):
        code = str(rec[code_idx]).strip()
        pts = list(shp.points)
        if pts:
            out[code] = (pts[0], pts[-1])
    sr.close()
    return out


def _check_geometry(project, shape_dir, rules, anomalies):
    """6.x 几何一致性。需要 shape_dir + pyshp。"""
    if not shape_dir or not os.path.isdir(shape_dir):
        r = Rule("6.x", "几何检测", "点面包含/端点重合几何检查")
        r.status = "skip"
        r.detail = "未提供 Shape 目录，无法读取 .shp 几何，几何类规则跳过。"
        rules.append(r)
        return

    boites = project.boites
    sites = project.sites
    cables = project.cables
    zpm_polys = _load_polygons(shape_dir, "ZPM")
    cable_ends = _load_cable_endpoints(shape_dir)

    # 6.3 SITE(PM) 点必须位于其 ZPM 多边形内
    r = Rule("6.3", "几何检测", "SITE(PM) 坐标必须落入对应 ZPM 多边形")
    if not zpm_polys:
        r.status = "skip"
        r.detail = "ZPM.shp 未读到，跳过"
    else:
        pm_sites = {c: s for c, s in sites.items()
                    if (s.get("TYPE") or "").strip() == "PM"}
        bad = []
        for code, s in pm_sites.items():
            try:
                x, y = float(s["X"]), float(s["Y"])
            except (TypeError, ValueError, KeyError):
                continue
            poly = zpm_polys.get(code)
            if poly and not _point_in_polygon(x, y, poly):
                bad.append(code)
        if not bad:
            r.status = "pass"
            r.detail = f"全部 {len(pm_sites)} 个 PM 均落在对应 ZPM 内"
        else:
            r.status = "fail"
            r.detail = f"{len(bad)} 个 PM 坐标不在对应 ZPM 多边形内"
            r.samples = bad[:10]
            anomalies["SITE"].update(bad)
    rules.append(r)

    # 6.4 PBO 点必须位于其 ZPM 多边形内 (REF_PM=ZPM.CODE)
    r = Rule("6.4", "几何检测", "PBO 坐标必须落入其归属 ZPM 多边形")
    if not zpm_polys:
        r.status = "skip"
        r.detail = "ZPM.shp 未读到，跳过"
    else:
        bad = []
        for code, b in boites.items():
            if (b.get("TYPE") or "").strip() != "PBO":
                continue
            pm = (b.get("REF_PM") or "").strip()
            poly = zpm_polys.get(pm)
            if not poly:
                continue
            try:
                x, y = float(b["X"]), float(b["Y"])
            except (TypeError, ValueError, KeyError):
                continue
            if not _point_in_polygon(x, y, poly):
                bad.append(code)
        if not bad:
            r.status = "pass"
            r.detail = "全部 PBO 均落在归属 ZPM 内"
        else:
            r.status = "fail"
            r.detail = f"{len(bad)} 个 PBO 坐标不在归属 ZPM 内"
            r.samples = bad[:10]
            anomalies["BOITE"].update(bad)
    rules.append(r)

    # 6.5 DISTRIBUTION 缆端点必须位于其 ZPM 多边形内
    r = Rule("6.5", "几何检测", "DISTRIBUTION 缆端点必须落入归属 ZPM 多边形")
    if not zpm_polys:
        r.status = "skip"
        r.detail = "ZPM.shp 未读到，跳过"
    else:
        bad = []
        for code, k in cables.items():
            if (k.get("TYPE_CABLE") or "").strip() != "DISTRIBUTION":
                continue
            pm = (k.get("REF_PM") or "").strip()
            poly = zpm_polys.get(pm)
            if not poly or not cable_ends:
                continue
            ends = cable_ends.get(code)
            if not ends:
                continue
            for (x, y) in ends:
                if not _point_in_polygon(x, y, poly):
                    bad.append(code)
                    break
        if not bad:
            r.status = "pass"
            r.detail = "全部配线缆端点均落在归属 ZPM 内"
        else:
            r.status = "fail"
            r.detail = f"{len(bad)} 条配线缆存在端点越界 ZPM"
            r.samples = bad[:10]
            anomalies["CABLE"].update(bad)
    rules.append(r)

    # 6.6 缆端点坐标必须与其引用的箱体/站点坐标重合；ORIGINE != EXTREMITE
    r = Rule("6.6", "几何检测",
             "CABLE 端点坐标须与引用 BOITE/SITE 坐标重合；ORIGINE≠EXTREMITE")
    if not cable_ends:
        r.status = "skip"
        r.detail = "CABLE.shp 未读到，跳过"
    else:
        tol = 1e-3  # ~100m 容差
        bad_same = []
        bad_miss = []
        for code, k in cables.items():
            o = (k.get("ORIGINE") or "").strip()
            e = (k.get("EXTREMITE") or "").strip()
            if o and e and o == e:
                bad_same.append(code)
            ends = cable_ends.get(code)
            if not ends:
                continue
            first, last = ends
            for end_code, (ex, ey) in ((o, first), (e, last)):
                if not end_code:
                    continue
                node = boites.get(end_code) or sites.get(end_code)
                if node is None:
                    continue
                try:
                    nx, ny = float(node["X"]), float(node["Y"])
                except (TypeError, ValueError, KeyError):
                    continue
                if abs(ex - nx) > tol or abs(ey - ny) > tol:
                    bad_miss.append(f"{code}:{end_code}")
        if not bad_same and not bad_miss:
            r.status = "pass"
            r.detail = "全部缆端点与引用节点坐标重合，且无自环"
        else:
            r.status = "fail"
            r.detail = (f"ORIGINE=EXTREMITE 自环 {len(bad_same)} 条; "
                        f"端点坐标不重合 {len(bad_miss)} 处")
            r.samples = (bad_same[:10] + bad_miss[:10])
            anomalies["CABLE"].update(bad_same)
            for s in bad_miss:
                cable_code, _, node = s.partition(":")
                if cable_code:
                    anomalies["CABLE"].add(cable_code)
                if node:
                    anomalies["BOITE"].add(node)
                    anomalies["SITE"].add(node)
    rules.append(r)

    # 6.1/6.2 多边形重叠(近似: 包围盒) —— 精确需 shapely
    for layer, rid in (("ZNRO", "6.1"), ("ZPM", "6.2")):
        r = Rule(rid, "几何检测", f"{layer} 多边形互不重叠(包围盒近似)")
        polys = _load_polygons(shape_dir, layer)
        if not polys:
            r.status = "skip"
            r.detail = f"{layer}.shp 未读到，跳过"
        else:
            boxes = {}
            overlap = []
            for code, pts in polys.items():
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                boxes[code] = (min(xs), min(ys), max(xs), max(ys))
            cl = list(boxes)
            for i in range(len(cl)):
                for j in range(i + 1, len(cl)):
                    a, b = boxes[cl[i]], boxes[cl[j]]
                    if (a[0] < b[2] and b[0] < a[2] and
                            a[1] < b[3] and b[1] < a[3]):
                        overlap.append(f"{cl[i]}/{cl[j]}")
            if not overlap:
                r.status = "pass"
                r.detail = (f"{layer} 全部 {len(polys)} 个多边形包围盒无重叠"
                            f"(近似，精确相交需 shapely)")
            else:
                r.status = "warn"
                r.detail = (f"{layer} 发现 {len(overlap)} 对包围盒重叠"
                            f"(近似，可能为相切或真实相交，需 shapely 精确判定)")
                r.samples = overlap[:10]
                for s in overlap:
                    for part in s.split("/"):
                        anomalies[layer].add(part.strip())
        rules.append(r)


def _check_capacity(project, rules, anomalies):
    """7.x 容量约束"""
    boites = project.boites

    # 7.1 PBO: NB_FIBRE_UTIL <= CAPACITE(端口数)
    r = Rule("7.1", "数据检测", "PBO 设计覆盖户数(NB_FIBRE_UTIL) ≤ 端口数(CAPACITE)")
    violations = []
    for code, b in boites.items():
        if (b.get("TYPE") or "").strip() != "PBO":
            continue
        util = _num(b.get("NB_FIBRE_UTIL"))
        cap = _num(b.get("CAPACITE"))
        if util is None or cap is None:
            continue
        if util > cap:
            violations.append(f"{code}:util={util}>cap={cap}")
    if not violations:
        r.status = "pass"
        r.detail = "全部 PBO 覆盖户数未超过端口容量"
    else:
        r.status = "fail"
        r.detail = f"{len(violations)} 个 PBO 覆盖户数超出端口容量"
        r.samples = violations[:10]
        for s in violations:
            anomalies["BOITE"].add(s.split(":", 1)[0].strip())
    rules.append(r)

    # 7.2 每 PM: Σ(PBO CAPACITE) <= Σ(DISTRIBUTION 缆 CAPACITE, ORIGINE=PM)
    r = Rule("7.2", "数据检测",
             "每 PM 下 PBO 端口(CAPACITE)之和 ≤ 以该PM为起点的配线缆芯数之和")
    sites = project.sites
    cables = project.cables
    pm_sites = {c: s for c, s in sites.items()
                if (s.get("TYPE") or "").strip() == "PM"}
    pbo_by_pm = defaultdict(list)
    for b in boites.values():
        if (b.get("TYPE") or "").strip() == "PBO":
            pm = (b.get("REF_PM") or "").strip()
            if pm:
                pbo_by_pm[pm].append(b)
    cab_cap_by_pm = defaultdict(float)
    for k in cables.values():
        if (k.get("TYPE_CABLE") or "").strip() != "DISTRIBUTION":
            continue
        pm = (k.get("REF_PM") or "").strip()
        o = (k.get("ORIGINE") or "").strip()
        cap = _num(k.get("CAPACITE")) or 0
        # 规则: ORIGINE=PM 的缆计入该 PM 上游芯数
        if o and o in pm_sites:
            cab_cap_by_pm[o] += cap
        elif pm and pm in pm_sites:
            cab_cap_by_pm[pm] += cap
    violations = []
    for pm in pm_sites:
        pbo_sum = sum(_num(b.get("CAPACITE")) or 0 for b in pbo_by_pm.get(pm, []))
        cab_sum = cab_cap_by_pm.get(pm, 0.0)
        if pbo_sum > cab_sum:
            violations.append(f"{pm}:PBO端口={pbo_sum}>缆芯={cab_sum:.0f}")
    if not violations:
        r.status = "pass"
        r.detail = f"全部 {len(pm_sites)} 个 PM 端口供需平衡"
    else:
        r.status = "fail"
        r.detail = f"{len(violations)} 个 PM 上游配线缆芯数不足以覆盖 PBO 端口"
        r.samples = violations[:10]
        for s in violations:
            anomalies["SITE"].add(s.split(":", 1)[0].strip())
    rules.append(r)


# ============================================================================
# 主入口
# ============================================================================
def validate_project(project, shape_dir: str | None = None) -> dict:
    """对 project 运行全部可计算校验规则，返回结构化报告 dict。

    返回 dict 含:
      - summary / groups / rules (既有)
      - anomalies: {图层名: [异常要素 CODE 列表]} (新增，供画布高亮)
    """
    rules: list[Rule] = []
    anomalies: dict[str, set] = defaultdict(set)
    _check_files_and_naming(project, shape_dir, rules, anomalies)
    _check_fields(project, rules, anomalies)
    _check_isolation(project, rules, anomalies)
    _check_geometry(project, shape_dir, rules, anomalies)
    _check_capacity(project, rules, anomalies)

    passed = sum(1 for r in rules if r.status == "pass")
    failed = sum(1 for r in rules if r.status == "fail")
    skipped = sum(1 for r in rules if r.status == "skip")
    warned = sum(1 for r in rules if r.status == "warn")
    total = len(rules)

    # 自动修复建议: 仅对失败/警告规则填充
    for r in rules:
        if r.status in ("fail", "warn"):
            r.suggestion = _pick_suggestion(r.rid)

    # 分组汇总
    groups = defaultdict(lambda: {"pass": 0, "fail": 0, "skip": 0, "warn": 0})
    for r in rules:
        g = groups[r.category]
        g[r.status] += 1

    # anomalies: set -> 排序后的 list，去掉内部占位标记(仅在整层缺失/空时使用)
    anomalies_out = {}
    for layer, codes in anomalies.items():
        clean = sorted(c for c in codes if not c.startswith("__"))
        anomalies_out[layer] = clean

    return {
        "source": project.source,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warned": warned,
            "passed_rate": round(passed / total * 100, 1) if total else 0.0,
        },
        "groups": {k: v for k, v in groups.items()},
        "rules": [r.to_dict() for r in rules],
        "anomalies": anomalies_out,
    }


def export_validation(project, out_path: str, shape_dir: str | None = None) -> dict:
    """运行校验并写出 JSON 报告。"""
    report = validate_project(project, shape_dir)
    import json
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
