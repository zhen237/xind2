# -*- coding: utf-8 -*-
"""导出隐藏诊断图层 · AST 接线保险 — ui/design_dock.py + design_engine/cad_export.py

``ui/design_dock.py`` 顶层 import ``qgis`` / ``PyQt5``，本机无 QGIS 时**无法 import**，
纯函数单测抓不到「过滤逻辑写对了但没接线」的回归（弱区放大 100 倍即此类）。
故本文件用 ``ast.parse`` 静态读源码，断言「PDF/CAD 导出确实排除诊断层」的接线成立，
不依赖 QGIS，也不 import qgis/PyQt。

覆盖（对应口径 A）：
  (a) ``_export_pdf`` 源码里调用 ``is_diagnosis_layer``，且**仍**排除「覆盖热力图」；
  (b) ``_export_cad`` 调用 ``_run_export_cad`` 时带关键字实参 ``layer_exclude``；
  (b') ``cad_export.export_cad`` 把 ``layer_exclude`` 透传给 ``export_dxf``；
  (c) ``cad_export.export_dxf`` 与 ``export_cad`` 签名里都有 ``layer_exclude`` 参数；
  (d) ``export_dxf`` 函数体里存在 ``layer_exclude`` 的过滤判断（含 continue 守卫）。
"""
import ast
import os
import sys

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_DIR)

DOCK_PATH = os.path.join(PLUGIN_DIR, "ui", "design_dock.py")
CAD_PATH = os.path.join(PLUGIN_DIR, "design_engine", "cad_export.py")


def _parse(path):
    with open(path, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _dotted(node) -> str:
    """把表达式节点还原为「点分名」，如 ``is_diagnosis_layer`` / ``self._run_export_cad``。"""
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
    raise AssertionError(f"未找到函数 {name}（{name} 所在文件结构变了？）")


def _call_names(fn):
    """函数体内所有被调用的「点分名」集合。"""
    return {_dotted(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}


def _arg_names(fn):
    """函数签名（含仅位置参数 / 关键字参数 / 默认值）里的形参名集合。"""
    a = fn.args
    names = {p.arg for p in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    if a.vararg:
        names.add(a.vararg.arg)
    if a.kwarg:
        names.add(a.kwarg.arg)
    return names


# ════════════════════════ (a) PDF 导出过滤接线 ════════════════════════

def test_export_pdf_calls_is_diagnosis_layer():
    """`_export_pdf` 图层收集循环须调用 ``is_diagnosis_layer``（排除「诊断·」层）。"""
    fn = _func(_parse(DOCK_PATH), "_export_pdf")
    assert "is_diagnosis_layer" in _call_names(fn), (
        "_export_pdf 未调用 is_diagnosis_layer —— "
        "诊断·弱覆盖区 / 诊断·建议补站 会被打进 PDF，橙色弱区块+三角形建议站与蓝点打架")


def test_export_pdf_still_excludes_heatmap():
    """`_export_pdf` **仍**排除「覆盖热力图」（既有行为，保持不变，别被顺手去掉）。"""
    fn = _func(_parse(DOCK_PATH), "_export_pdf")
    has_heatmap = any(
        isinstance(n, ast.Constant) and n.value == "覆盖热力图" for n in ast.walk(fn))
    assert has_heatmap, (
        "_export_pdf 未见「覆盖热力图」字面量 —— 既有「PDF 不显示热力图」行为被破坏")


# ════════════════════════ (b) CAD 导出接线 ════════════════════════

def _call_keywords(fn, callee_dotted):
    """取函数体内第一个 ``callee_dotted(...)`` 调用的关键字实参名集合（None=未找到）。"""
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and _dotted(n.func) == callee_dotted:
            return {kw.arg for kw in n.keywords}
    return None


def test_export_cad_passes_layer_exclude():
    """`_export_cad` 调 `_run_export_cad`（=export_cad）时须带关键字实参 ``layer_exclude``。"""
    fn = _func(_parse(DOCK_PATH), "_export_cad")
    kws = _call_keywords(fn, "_run_export_cad")
    assert kws is not None, "_export_cad 未找到 _run_export_cad(...) 调用"
    assert "layer_exclude" in kws, (
        "_export_cad 调用 _run_export_cad 时未传 layer_exclude —— CAD 里诊断层不会被排除")


def test_export_cad_helper_passes_layer_exclude_through():
    """`cad_export.export_cad` 须把 ``layer_exclude`` 透传给 ``export_dxf``。"""
    fn = _func(_parse(CAD_PATH), "export_cad")
    kws = _call_keywords(fn, "export_dxf")
    assert kws is not None, "export_cad 未找到 export_dxf(...) 调用"
    assert "layer_exclude" in kws, (
        "export_cad 调 export_dxf 时未透传 layer_exclude —— "
        "一键 CAD 导出会退化成「不排除诊断层」")


# ════════════════════════ (c) 签名含 layer_exclude ════════════════════════

def test_export_dxf_signature_has_layer_exclude():
    """`cad_export.export_dxf` 签名须含 ``layer_exclude`` 形参。"""
    fn = _func(_parse(CAD_PATH), "export_dxf")
    assert "layer_exclude" in _arg_names(fn), \
        "export_dxf 签名缺 layer_exclude 形参（调用方传参会 TypeError）"


def test_export_cad_signature_has_layer_exclude():
    """`cad_export.export_cad` 签名须含 ``layer_exclude`` 形参。"""
    fn = _func(_parse(CAD_PATH), "export_cad")
    assert "layer_exclude" in _arg_names(fn), \
        "export_cad 签名缺 layer_exclude 形参（一键导出无法透传）"


# ════════════════════════ (d) export_dxf 体内有过滤判断 ════════════════════════

def test_export_dxf_body_has_layer_exclude_guard():
    """`export_dxf` 函数体里须存在 ``if layer_exclude ...: continue`` 形式的过滤判断。"""
    fn = _func(_parse(CAD_PATH), "export_dxf")
    found = False
    for n in ast.walk(fn):
        if not isinstance(n, ast.If):
            continue
        if not any(_dotted(x) == "layer_exclude" for x in ast.walk(n.test)):
            continue
        if any(isinstance(s, ast.Continue) for s in ast.walk(n)):
            found = True
            break
    assert found, (
        "export_dxf 体内未见 `if layer_exclude ...: continue` 过滤判断 —— "
        "即使签名有 layer_exclude 也不会生效")


# ════════ (e) 独立 QA 盲区封堵 B-1/B-2/B-3（对抗变体 V1/V2/V5）════════

def _call_kw_value(fn, callee_dotted, kw_name):
    """取函数体内 ``callee_dotted(...)`` 调用的某关键字实参**值节点**（None=未找到）。"""
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and _dotted(n.func) == callee_dotted:
            for kw in n.keywords:
                if kw.arg == kw_name:
                    return kw.value
    return None


def test_export_cad_layer_exclude_references_constant_not_literal():
    """B-1（封 QA 变体 V1）：`_export_cad` 传的 ``layer_exclude`` 实参须是**引用常量
    ``DIAGNOSIS_LAYER_PREFIX`` 的列表**，不得硬编码字符串字面量。

    防回归：把 ``[DIAGNOSIS_LAYER_PREFIX]`` 改成 ``["诊断"]``（少中点）语义漂移 ——
    前面的断言照样全绿（仍是关键字实参），但 CAD 导出会漏排/误排诊断层。
    """
    fn = _func(_parse(DOCK_PATH), "_export_cad")
    val = _call_kw_value(fn, "_run_export_cad", "layer_exclude")
    assert val is not None, "_export_cad 调 _run_export_cad 未传 layer_exclude 关键字实参"
    assert isinstance(val, ast.List), \
        f"layer_exclude 实参应为列表，实际 {type(val).__name__}"
    assert val.elts, "layer_exclude 列表为空（不排除任何图层）"
    for e in val.elts:
        assert isinstance(e, ast.Name) and e.id == "DIAGNOSIS_LAYER_PREFIX", (
            "layer_exclude 列表元素须是常量引用 DIAGNOSIS_LAYER_PREFIX（禁硬编码字符串）："
            f" 实际 {ast.dump(e)}")


def _dxf_guard_and_append_lines(fn):
    """返回 ``(守卫If行号, layers.append行号, append实参是否为 layer)``（缺失项为 None/False）。"""
    guard_line = None
    for n in ast.walk(fn):
        if not isinstance(n, ast.If):
            continue
        if not any(_dotted(x) == "layer_exclude" for x in ast.walk(n.test)):
            continue
        if any(isinstance(s, ast.Continue) for s in ast.walk(n)):
            guard_line = n.lineno
    append_line = None
    append_arg_ok = False
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "append" and _dotted(n.func.value) == "layers"):
            append_line = n.lineno
            if n.args and _dotted(n.args[0]) == "layer":
                append_arg_ok = True
    return guard_line, append_line, append_arg_ok


def test_export_dxf_exclude_guard_precedes_append():
    """B-2（封 QA 变体 V2）：`export_dxf` 里 ``layer_exclude`` 守卫 If 的行号须 **小于**
    ``layers.append(layer)`` 的行号（先过滤再收集）。

    防回归：把排除判断挪到 ``layers.append(layer)`` 之后 → 层已进 ``layers``，排除等于不生效。
    """
    fn = _func(_parse(CAD_PATH), "export_dxf")
    guard_line, append_line, append_arg_ok = _dxf_guard_and_append_lines(fn)
    assert guard_line is not None, \
        "export_dxf 未找到 `if layer_exclude ...: continue` 守卫 If"
    assert append_line is not None, "export_dxf 未找到 layers.append(...) 调用"
    assert append_arg_ok, "layers.append 的实参不是 layer（收集对象变了）"
    assert guard_line < append_line, (
        "layer_exclude 守卫必须 **先于** layers.append(layer)："
        f" 实际守卫@L{guard_line} 不早于 append@L{append_line}（排除等于不生效）")


def test_export_pdf_is_diagnosis_layer_guarded_by_continue():
    """B-3（封 QA 变体 V5）：`_export_pdf` 对 ``is_diagnosis_layer`` 的调用须位于某个
    ``If`` 的 test 内，且该 If 的 body **含 Continue**（调用须真正生效，不能调了不用）。

    防回归：保留 is_diagnosis_layer 调用但把 ``continue`` 换成 ``pass`` →
    诊断层照样进 ``pdf_layers``。
    """
    fn = _func(_parse(DOCK_PATH), "_export_pdf")
    found = False
    for n in ast.walk(fn):
        if not isinstance(n, ast.If):
            continue
        if not any(isinstance(c, ast.Call) and _dotted(c.func) == "is_diagnosis_layer"
                   for c in ast.walk(n.test)):
            continue
        if any(isinstance(s, ast.Continue) for s in ast.walk(n)):
            found = True
            break
    assert found, (
        "_export_pdf 的 is_diagnosis_layer 调用未处于「If test + body 含 continue」结构中 "
        "—— 诊断层不会被真正排除（调了不用）")
