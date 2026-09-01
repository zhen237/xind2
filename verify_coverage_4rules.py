"""验证：EM-002/ST-001/ST-003/ST-004 字段补全后，4 条规则不再是 pending，且覆盖率=100%。

逻辑严格复刻 s3-review-engine/rules/app/routers/review.py 中的 B5_RULES / _eval_b5 /
_real_engine_check_b5 与 ReviewService.calculateCoverageRate，仅裁剪无关规则，便于离线验证。
"""
from copy import deepcopy


def _safe_float(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ---- 与 review.py B5_RULES 完全一致的 4 条规则配置（逐字复制）----
B5_RULES = {
    'ST-001': {'name': '基础承载力验算', 'gb': 'GB 50007-2011', 'kind': 'ge',
               'actual': 'bearingCapacity', 'base': 'designLoad', 'factor': 1.2,
               'unit': 'kPa', 'actual_label': '地基承载力', 'std_desc': '承载力应≥1.2倍设计荷载',
               'fix': '需加固基础或减小上部荷载'},
    'ST-003': {'name': '混凝土强度检测', 'gb': 'GB 50204-2015', 'kind': 'ge',
               'actual': 'concreteStrengthActual', 'base': 'concreteStrengthDesign', 'factor': 1.0,
               'unit': 'MPa', 'actual_label': '混凝土强度', 'std_desc': '强度应≥设计等级',
               'fix': '需加固或重建不合格构件'},
    'ST-004': {'name': '构件变形监测', 'gb': 'GB 50205-2020', 'kind': 'le',
               'actual': 'deformationActual', 'base': 'deformationLimit', 'factor': 1.0,
               'unit': 'mm', 'actual_label': '构件变形量', 'std_desc': '变形量应≤允许值',
               'fix': '需分析原因并加固'},
    'EM-002': {'name': '无线电干扰测试', 'gb': 'GB 7349-2002', 'kind': 'le',
               'actual': 'radioInterference', 'base': 'radioLimit', 'factor': 1.0,
               'unit': 'dBμV/m', 'actual_label': '无线电干扰', 'std_desc': '干扰值应≤允许限值',
               'fix': '需排查并消除干扰源'},
}


def _eval_b5(rule_code, params):
    """逐字复刻 review.py _eval_b5 的数值比较分支（ge/le）。"""
    cfg = B5_RULES[rule_code]
    kind = cfg['kind']
    if kind in ('ge', 'le'):
        actual = _safe_float(params.get(cfg['actual']))
        if actual is None:
            return None  # 缺参 → 上层标记 pending
        limit = cfg.get('limit_const')
        if limit is None:
            base = _safe_float(params.get(cfg['base']))
            if base is None:
                return None
            limit = base * cfg.get('factor', 1.0)
        passed = (actual >= limit) if kind == 'ge' else (actual <= limit)
        return passed, dict(actual=actual, limit=limit, passed=passed)
    return None


# 站点(铁塔) params：与 QGIS 插件导出值一致（合规设计值）
TOWER_PARAMS = {
    'bearingCapacity': 250.0, 'designLoad': 180.0,
    'concreteStrengthActual': 32.5, 'concreteStrengthDesign': 30.0,
    'deformationActual': 5.0, 'deformationLimit': 8.0,
    'radioInterference': 30.0, 'radioLimit': 40.0,
}

print("=== 1) 4 规则真实比对（合规值，应判定为「已覆盖/合规」，不再 pending）===")
for code in ('ST-001', 'ST-003', 'ST-004', 'EM-002'):
    res = _eval_b5(code, TOWER_PARAMS)
    assert res is not None, f"❌ {code} 缺参 → 仍会被标记 pending！"
    passed, d = res
    print(f"  {code}: 实测={d['actual']}{B5_RULES[code]['unit']} 阈值={d['limit']}"
          f" → {'合规(覆盖)' if passed else '违规(真实命中)'}")

print("\n=== 2) 反例：让 ST-001 不合规，证明是真实公式比对而非永久通过 ===")
bad = deepcopy(TOWER_PARAMS)
bad['bearingCapacity'] = 200.0  # 200 < 1.2×180 = 216
r = _eval_b5('ST-001', bad)
print(f"  ST-001(bearingCapacity=200 < 216): passed={r[1]['passed']} "
      f"→ {'❌仍为合规' if r[1]['passed'] else '✅ 真实违规命中（说明是真实比对）'}")
assert not r[1]['passed'], "反例未触发违规，比对逻辑有误"

print("\n=== 3) 覆盖率口径（与 Java calculateCoverageRate 完全一致，分母=9 项 S1 可审查规则）===")


def coverage(design_data):
    devs = design_data.get('devices', [])
    cCap = cDia = cGnd = cCur = cBury = cBear = cConc = cDef = cRadio = False
    for d in devs:
        if d.get('capacity') is not None and d.get('fibreUsed') is not None:
            cCap = True
        dia = d.get('cableDiameter')
        if isinstance(dia, (int, float)) and dia > 0:
            cDia = True
        if d.get('groundingResistance') is not None:
            cGnd = True
        if d.get('crossSection') is not None and d.get('actualCurrent') is not None:
            cCur = True
        p = d.get('params') or {}
        if p.get('bearingCapacity') is not None and p.get('designLoad') is not None:
            cBear = True
        if p.get('concreteStrengthActual') is not None and p.get('concreteStrengthDesign') is not None:
            cConc = True
        if p.get('deformationActual') is not None and p.get('deformationLimit') is not None:
            cDef = True
        if p.get('radioInterference') is not None and p.get('radioLimit') is not None:
            cRadio = True
    for p in (design_data.get('pipeline') or []):
        if (p.get('layingType') is not None and p.get('scenario') is not None
                and isinstance(p.get('burialDepth'), (int, float)) and p['burialDepth'] > 0):
            cBury = True
            break
    caps = [cCap, cDia, cGnd, cCur, cBury, cBear, cConc, cDef, cRadio]
    covered = sum(1 for b in caps if b)
    return covered, len(caps)


design_data = {
    "devices": [
        {"deviceType": "tower", "groundingResistance": 4.0, "params": TOWER_PARAMS},
        {"deviceType": "communication_room", "capacity": 50.0, "fibreUsed": 6.0, "params": {}},
        {"deviceType": "communication_cable", "cableDiameter": 25.0, "bendingRadius": 400.0,
         "crossSection": 50.0, "actualCurrent": 80.0, "material": "copper", "params": {}},
    ],
    "pipeline": [{"layingType": "direct", "scenario": "SUBURBAN", "burialDepth": 1.2}],
}
cov, total = coverage(design_data)
print(f"  covered={cov} / reviewable={total} → {round(cov / total * 100, 2)}%")
assert cov == total, f"❌ 覆盖率未达 100%（{cov}/{total}）"
print("✅ 覆盖率 = 100%")

print("\n=== 4) 对照组：补全前（无 4 字段）应只剩 5 项覆盖 ===")
old = deepcopy(design_data)
for d in old['devices']:
    d['params'] = {}
cov_old, _ = coverage(old)
print(f"  补全前 covered={cov_old} / 9 → {round(cov_old / 9 * 100, 2)}%（仅 5 项真实字段，4 条 pending）")
assert cov_old == 5, "对照组应为 5"

print("\n🎉 全部验证通过：4 字段补全后，4 条规则不再 pending，覆盖率 100%。")
