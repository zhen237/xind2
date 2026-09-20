"""补盲前后对比 · AST 接线保险 — ui/design_dock.py

``ui/design_dock.py`` 顶层 import ``qgis`` / ``PyQt5``，本机无 QGIS 时**无法 import**，
故用 ``ast.parse`` 静态读源码，断言第四批「补盲前后对比」的接线确实接上，不依赖 QGIS。

锁定的关键不变量：
- ``_generate_gap_diagnosis`` 把 ``_gap_params`` 赋成含 ``link_margin_db/resolution_m/bbox``
  的快照（影子诊断复用，绝不在采纳后重算），并记录 ``_gap_before_metrics``、调用
  ``_refresh_comparison``。
- 采纳单条/批量后必须触发 ``_refresh_comparison``（自动刷新对比表）；批量只刷一次；
  且 ``_adopt_suggested_site`` 仍**禁止**调用 ``_update_suggested_table``（m6 崩溃防护）。
- ``_refresh_comparison`` **只算不画**：绝不调用 ``remove_gap_layers`` /
  ``build_rsrp_weak_layer`` / ``build_suggested_sites_layer``，也不 import ``layers.gap_layer``。
"""
import ast
import os

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCK_PATH = os.path.join(PLUGIN_DIR, "ui", "design_dock.py")


def _load_tree():
    with open(DOCK_PATH, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=DOCK_PATH)


def _dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _dotted(node.func)
    return ""


def _func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"未找到函数 {name}（ui/design_dock.py 结构变了？）")


def _call_names(fn):
    return {_dotted(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}


def _assign_targets(fn):
    names = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                names.add(_dotted(t))
        elif isinstance(n, ast.AnnAssign) and n.target is not None:
            names.add(_dotted(n.target))
    return names


def _calls_of_name(fn, name):
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and _dotted(n.func) == name]


def _gap_params_dict_keys(fn):
    """返回 _generate_gap_diagnosis 里 `self._gap_params = {...}` 字面量的所有 key 字符串。"""
    for n in ast.walk(fn):
        if not isinstance(n, ast.Assign):
            continue
        if not any(_dotted(t) == "self._gap_params" for t in n.targets):
            continue
        if not isinstance(n.value, ast.Dict):
            continue
        keys = []
        for k in n.value.keys:
            if isinstance(k, ast.Constant):
                keys.append(k.value)
        return keys
    return []


# ────────────────────────────────────────────────

def test_generate_gap_diagnosis_wires_comparison():
    """诊断尾部要为对比功能接线：快照含 3 个新键 + 记录 before + 触发刷新。"""
    fn = _func(_load_tree(), "_generate_gap_diagnosis")
    assigns = _assign_targets(fn)
    calls = _call_names(fn)

    assert "self._gap_before_metrics" in assigns, \
        "_generate_gap_diagnosis 未记录 _gap_before_metrics（补盲前快照缺失）"
    assert "self._refresh_comparison" in calls, \
        "_generate_gap_diagnosis 未调用 self._refresh_comparison（对比表不会初始化）"

    keys = _gap_params_dict_keys(fn)
    for need in ("link_margin_db", "resolution_m", "bbox"):
        assert need in keys, \
            f"_gap_params 快照缺少 {need}（影子诊断拿不到历史口径，补盲后对比失真）"


def test_adopt_suggested_site_refreshes_comparison_and_keeps_m6():
    """采纳单条：触发对比刷新，且仍禁止重建建议站表格（Qt 崩溃防护）。"""
    fn = _func(_load_tree(), "_adopt_suggested_site")
    calls = _call_names(fn)
    assert "self._refresh_comparison" in calls, \
        "_adopt_suggested_site 未调用 self._refresh_comparison（采纳后对比表不刷新）"
    assert "self._update_suggested_table" not in calls, \
        "_adopt_suggested_site 里出现了 self._update_suggested_table 调用（违反 m6 崩溃防护）"


def test_adopt_all_refreshes_comparison_once_with_refresh_false():
    """批量采纳：循环传 refresh=False（避免逐行 O(n²) 重算），循环后只刷一次对比表。"""
    fn = _func(_load_tree(), "_adopt_all_suggested_sites")
    calls = _call_names(fn)
    assert "self._refresh_comparison" in calls, \
        "_adopt_all_suggested_site 收尾未调用 self._refresh_comparison（批量后对比表不刷新）"

    adopt_calls = _calls_of_name(fn, "self._adopt_suggested_site")
    assert adopt_calls, "_adopt_all_suggested_sites 未调用 _adopt_suggested_site"
    saw_refresh_false = False
    for c in adopt_calls:
        for kw in c.keywords:
            if kw.arg == "refresh" and isinstance(kw.value, ast.Constant) \
                    and kw.value.value is False:
                saw_refresh_false = True
    assert saw_refresh_false, \
        "_adopt_all_suggested_sites 循环内未传 refresh=False（会逐行 O(n²) 重算对比）"


def test_refresh_comparison_does_not_draw_layers():
    """_refresh_comparison 只算不画：禁止调用任何图层绘制函数，也不 import layers.gap_layer。"""
    fn = _func(_load_tree(), "_refresh_comparison")
    calls = _call_names(fn)
    for forbidden in ("remove_gap_layers", "build_rsrp_weak_layer",
                     "build_suggested_sites_layer"):
        assert forbidden not in calls, \
            f"_refresh_comparison 里出现了 {forbidden} 调用 —— 违反「只算不画」（会重画诊断图层）"

    for n in ast.walk(fn):
        if isinstance(n, ast.ImportFrom) and n.module == "layers.gap_layer":
            raise AssertionError(
                "_refresh_comparison import 了 layers.gap_layer（应只用纯函数影子诊断）")


def test_comparison_metrics_carry_tooltips():
    """数据层：8 个对比指标都必须有非空 tip，供 UI 悬停解释「这是什么」。"""
    from design_engine.gap_diagnosis import COMPARISON_METRICS
    assert len(COMPARISON_METRICS) == 8, \
        f"COMPARISON_METRICS 应有 8 个指标，实际 {len(COMPARISON_METRICS)}"
    for m in COMPARISON_METRICS:
        assert m.get("tip", "").strip(), \
            f"指标 {m['label']} 缺少 tip（悬停解释缺失）"


def test_refresh_comparison_attaches_tooltips_and_units():
    """UI 接线：_refresh_comparison 必须给单元格 setToolTip，且值后面带单位。"""
    fn = _func(_load_tree(), "_refresh_comparison")
    src = ast.get_source_segment(open(DOCK_PATH, encoding="utf-8").read(), fn) or ""
    assert ".setToolTip(" in src, \
        "_refresh_comparison 未调用 setToolTip（指标悬停解释缺失）"
    assert "r['unit']" in src, \
        "_refresh_comparison 的「补盲前/后/变化」值未拼接 r['unit']（屏幕表格不带单位）"
