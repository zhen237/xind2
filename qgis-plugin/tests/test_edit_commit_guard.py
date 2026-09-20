# -*- coding: utf-8 -*-
"""编辑事务返回值校验 · AST 接线保险 — ui/design_dock.py

背景（QA 复核 + QGIS 源码核证）
------------------------------
口径 B 删掉站点 RubberBand 后，「写矢量图层」成为站点/机房**唯一**的渲染路径。
``addFeatures()`` / ``commitChanges()`` 返回 False 时**不抛异常**：
- 站点已进 ``generated_sites``、日志已打「已添加」，图层树/地图/导出里却什么都没有；
- 采纳路径的 try/except 只捕异常、捕不到 False 返回值；``_on_station_clicked`` 无 try/except。

⚠️ 但**不能**用 ``startEditing()`` 的返回值当失败判据：QGIS（``qgsvectorlayer.cpp``）在
「图层已处于编辑态」时 ``startEditing()`` 返回 **false**（``if ( mEditBuffer ) return false;``），
而 ``commitChanges()`` 失败会把图层留在编辑态 —— 一旦 ``if not startEditing(): return``，
就是「一次偶发失败 → 之后每次写入都被跳过」的**持久静默失败**（比忽略返回值更糟）。
真正决定成败的是 ``addFeatures()`` 与 ``commitChanges()``。

故本文件用 ``ast`` 断言三处写图层方法都：
  1. **不**存在 ``if not layer.startEditing(): … return`` 这种错误守卫；
  2. ``addFeatures(...)`` 的返回值**被** ``if not …: … return`` 守卫；
  3. ``commitChanges()`` 的返回值**被** ``if not …: … return`` 守卫；
  4. 整表重建失败时不落盘。
零 QGIS 依赖。
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCK_PATH = os.path.join(PLUGIN_DIR, "ui", "design_dock.py")

WRITE_METHODS = ("_append_site_to_layer", "_append_room_to_layer", "_add_sites_to_map")


def _parse():
    with open(DOCK_PATH, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=DOCK_PATH)


def _parent_map(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"未找到函数 {name}（ui/design_dock.py 结构变了？）")


def _calls_with_attr(fn, attr):
    """函数体内所有 ``X.<attr>(...)`` 调用节点。"""
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == attr]


def _is_not_guard_call(call_node, parents):
    """``call_node`` 是否为 ``if not <call>: … return`` 结构里的那个调用。"""
    p = parents.get(id(call_node))
    if not (isinstance(p, ast.UnaryOp) and isinstance(p.op, ast.Not)):
        return False
    g = parents.get(id(p))
    if not isinstance(g, ast.If):
        return False
    return any(isinstance(s, ast.Return) for s in ast.walk(g))


def _assert_method_shape(tree, parents, method):
    fn = _func(tree, method)
    # 1. startEditing 必须被调用，但**不得**被当成失败判据
    starts = _calls_with_attr(fn, "startEditing")
    assert starts, f"{method} 未调用 layer.startEditing()"
    for c in starts:
        assert not _is_not_guard_call(c, parents), (
            f"{method} 把 startEditing() 返回值当成失败判据"
            "（`if not layer.startEditing(): … return`）—— 图层已处于编辑态时 startEditing"
            "返回 false（qgsvectorlayer.cpp），会把一次偶发失败放大成持久静默失败")
    # 2/3. addFeatures / commitChanges 必须被校验
    for attr in ("addFeatures", "commitChanges"):
        assert _calls_with_attr(fn, attr), f"{method} 未调用 layer.{attr}(...)"
        guarded = [c for c in _calls_with_attr(fn, attr)
                   if _is_not_guard_call(c, parents)]
        assert guarded, (
            f"{method} 未校验 layer.{attr}() 的返回值"
            f"（`if not layer.{attr}(...): … return`）—— 失败不抛异常，忽略会静默丢点")


def test_append_site_to_layer_guards_addfeatures_and_commit():
    """`_append_site_to_layer`：addFeatures/commitChanges 被校验，startEditing 不被当判据。"""
    tree = _parse()
    _assert_method_shape(tree, _parent_map(tree), "_append_site_to_layer")


def test_append_room_to_layer_guards_addfeatures_and_commit():
    """`_append_room_to_layer`：addFeatures/commitChanges 被校验，startEditing 不被当判据。"""
    tree = _parse()
    _assert_method_shape(tree, _parent_map(tree), "_append_room_to_layer")


def test_add_sites_to_map_guards_addfeatures_and_commit():
    """`_add_sites_to_map`：addFeatures/commitChanges 被校验，startEditing 不被当判据
    （整表失败 = 地图上一个站点都没有，比单点更严重）。"""
    tree = _parse()
    _assert_method_shape(tree, _parent_map(tree), "_add_sites_to_map")


def test_add_sites_to_map_does_not_save_on_commit_failure():
    """`_add_sites_to_map` 提交失败分支内**不得**调用 ``self._save_design_state()``。

    防回归：失败时仍持久化 → 把「没有站点的坏状态」写进工程，重开工程也看不到站点。
    """
    tree = _parse()
    parents = _parent_map(tree)
    fn = _func(tree, "_add_sites_to_map")
    saves = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "_save_design_state"]
    assert saves, "_add_sites_to_map 未调用 self._save_design_state（成功路径应落盘）"
    commit_calls = _calls_with_attr(fn, "commitChanges")
    guarded = [c for c in commit_calls if _is_not_guard_call(c, parents)]
    assert guarded, "_add_sites_to_map 未见 commitChanges 返回值守卫"
    for c in guarded:
        guard_if = parents.get(id(parents.get(id(c))))
        inner = {id(x) for x in ast.walk(guard_if)}
        for s in saves:
            assert id(s) not in inner, (
                "_add_sites_to_map 提交失败分支里仍调用了 self._save_design_state —— "
                "失败时不应持久化坏状态")
