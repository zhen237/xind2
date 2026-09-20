"""建议站采纳闭环 · AST 接线保险 — ui/design_dock.py

``ui/design_dock.py`` 顶层 import ``qgis`` / ``PyQt5``，本机无 QGIS 时**无法 import**，
纯函数单测也就抓不到「函数写对了但没接线」的回归（弱区放大 100 倍即此类）。
故本文件用 ``ast.parse`` 静态读取源码，断言采纳闭环的**调用/赋值/顺序/闭包绑定/幂等语义**
确实接在一起，不依赖 QGIS，也不 import qgis/PyQt。

⚠️ 本文件经历过一轮独立攻击性验证：旧的 4 条用例对「删幂等守卫 / 删 add(row) /
闭包改坏成不绑行号 / 删 _gap_params 快照 / 调换尾链顺序」**全部没捕到**（作为对照，
删 `_append_adopted_site(rec["ui"])`、删 `_update_suggested_table()` 能捕到 —— 证明用例非空转）。
故新增 m1~m6 顺序/语义敏感断言，逐条对应上述盲区。
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCK_PATH = os.path.join(PLUGIN_DIR, "ui", "design_dock.py")


def _load_tree():
    with open(DOCK_PATH, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=DOCK_PATH)


def _dotted(node) -> str:
    """把一个表达式节点还原为「点分名」，如 ``self._add_marker`` / ``gd.next_site_seq``。"""
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
    """函数体内所有被调用的「点分名」集合。"""
    return {_dotted(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}


def _assign_targets(fn):
    """函数体内所有赋值目标的「点分名」集合。"""
    names = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                names.add(_dotted(t))
        elif isinstance(n, ast.AnnAssign) and n.target is not None:
            names.add(_dotted(n.target))
    return names


def _top_level_call_sequence(fn):
    """函数体内**顶层语句**（非嵌套）上、按源码顺序排列的调用「点分名」列表。"""
    seq = []
    for stmt in fn.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            seq.append(_dotted(stmt.value.func))
    return seq


# ════════════════════ 一、既有 4 条（保留）════════════════════

def test_generate_gap_diagnosis_wires_snapshot_and_table():
    """诊断尾部要刷新建议站表格，并给 self._suggested_sites 赋值（采纳的数据来源）。"""
    fn = _func(_load_tree(), "_generate_gap_diagnosis")
    calls = _call_names(fn)
    assigns = _assign_targets(fn)
    assert "self._update_suggested_table" in calls, \
        "_generate_gap_diagnosis 未调用 self._update_suggested_table（建议站表格不会刷新）"
    assert "self._suggested_sites" in assigns, \
        "_generate_gap_diagnosis 未给 self._suggested_sites 赋值（采纳无数据来源）"


def test_adopt_suggested_site_wires_bridge_and_tail():
    """采纳单条：必须经 suggested_site_to_records 映射，再走 _append_adopted_site。"""
    fn = _func(_load_tree(), "_adopt_suggested_site")
    calls = _call_names(fn)
    assert "gd.suggested_site_to_records" in calls, \
        "_adopt_suggested_site 未调用 suggested_site_to_records（建议站未映射为站点 schema）"
    assert "self._append_adopted_site" in calls, \
        "_adopt_suggested_site 未调用 _append_adopted_site（站点不会进站点池）"


def test_append_adopted_site_has_full_tail_chain():
    """采纳尾链须与 _on_station_clicked 完全一致：写矢量图层 / 机房 / 站点表 / 持久化。"""
    fn = _func(_load_tree(), "_append_adopted_site")
    calls = _call_names(fn)
    for need in ("self._append_site_to_layer", "self._ensure_room_under_site",
                 "self._update_site_table", "self._save_design_state"):
        assert need in calls, \
            f"_append_adopted_site 缺少 {need} 调用（尾链与 _on_station_clicked 不一致）"


def test_adopt_suggested_site_does_not_rename_layers():
    """禁止在采纳流程里用 .setName(...) 表示「过期」——会破坏诊断图层精确名删除。"""
    fn = _func(_load_tree(), "_adopt_suggested_site")
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "setName":
            raise AssertionError(
                "_adopt_suggested_site 里出现 .setName(...)：禁止用它表示「过期」。"
                "改名会破坏 remove_gap_layers 的精确名删除 → 旧诊断图层永久残留叠图。")


# ════════════════════ 二、m1~m6：补强（顺序/语义敏感）════════════════════

def test_m1_adopt_suggested_site_has_idempotent_guard():
    """m1：`_adopt_suggested_site` 须有 `if row in self._adopted_suggest_idx: ... return` 幂等守卫。

    防回归：删掉整块幂等守卫 → 同一建议站可被重复采纳（重复站 + 重复机房）。
    """
    fn = _func(_load_tree(), "_adopt_suggested_site")
    found = False
    for n in ast.walk(fn):
        if not isinstance(n, ast.If) or not isinstance(n.test, ast.Compare):
            continue
        if not any(isinstance(op, ast.In) for op in n.test.ops):
            continue
        left = n.test.left
        if not (isinstance(left, ast.Name) and left.id == "row"):
            continue
        if not any(_dotted(c) == "self._adopted_suggest_idx" for c in n.test.comparators):
            continue
        if any(isinstance(stmt, ast.Return) for stmt in n.body):
            found = True
            break
    assert found, (
        "_adopt_suggested_site 缺少 `if row in self._adopted_suggest_idx: ... return` 幂等守卫"
        "（删掉会导致同一建议站重复采纳）")


def test_m2_adopt_suggested_site_registers_adoption():
    """m2：`_adopt_suggested_site` 必须调用 `self._adopted_suggest_idx.add(...)` 登记。"""
    fn = _func(_load_tree(), "_adopt_suggested_site")
    calls = _call_names(fn)
    assert "self._adopted_suggest_idx.add" in calls, \
        "_adopt_suggested_site 未调用 self._adopted_suggest_idx.add(row)（采纳状态未登记）"


def test_m3_update_suggested_table_binds_row_via_lambda_default():
    """m3：第 6 列按钮的闭包须把行号 `i` 作为 **lambda 默认参数**绑定。

    防回归：写成 `lambda _=False: self._adopt_suggested_site(i)` 时闭包捕获循环变量本身，
    所有按钮都指向最后一行（点第 1 行却采纳最后一行）。
    """
    fn = _func(_load_tree(), "_update_suggested_table")
    lam = None
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "connect" and n.args and isinstance(n.args[0], ast.Lambda):
            lam = n.args[0]
            break
    assert lam is not None, \
        "_update_suggested_table 未找到 clicked.connect(lambda ...)（行内按钮未绑定采纳回调）"
    assert lam.args.defaults, \
        "该 lambda 无默认参数：行号 i 未被默认参数绑定（闭包会全指最后一行）"
    assert any(isinstance(d, ast.Name) and d.id == "i" for d in lam.args.defaults), \
        "该 lambda 默认参数中未见 `i`（应为 `lambda _=False, r=i: ...` 形式）"


def test_m4_generate_gap_diagnosis_assigns_gap_params_snapshot():
    """m4：`_generate_gap_diagnosis` 必须把 `self._gap_params` 赋成 **dict 字面量**（参数快照）。

    注意：函数体里另有一处 `self._gap_params = None`（开跑前重置，改动 2）。若只断言
    「存在对 self._gap_params 的赋值」，那条 `= None` 就会顶替快照、抓不到「删掉快照」的回归，
    故这里要求赋值**值是 dict 字面量**。
    """
    fn = _func(_load_tree(), "_generate_gap_diagnosis")
    found = False
    for n in ast.walk(fn):
        if not isinstance(n, ast.Assign):
            continue
        if not any(_dotted(t) == "self._gap_params" for t in n.targets):
            continue
        if isinstance(n.value, ast.Dict):
            found = True
            break
    assert found, (
        "_generate_gap_diagnosis 未把 self._gap_params 赋成 dict 快照"
        "（`= None` 只是重置，不算快照；采纳时无参数可复用）")


def test_m5_append_adopted_site_tail_chain_order():
    """m5：`_append_adopted_site` 顶层尾链顺序：_append_site_to_layer → _ensure_room_under_site → _update_site_table。

    防回归：调换顺序（如先建机房再写图层）会破坏与 `_on_station_clicked` 的一致性。
    """
    seq = _top_level_call_sequence(_func(_load_tree(), "_append_adopted_site"))
    for name in ("self._append_site_to_layer", "self._ensure_room_under_site", "self._update_site_table"):
        assert name in seq, f"_append_adopted_site 顶层语句缺 {name} 调用"
    i_marker = seq.index("self._append_site_to_layer")
    i_room = seq.index("self._ensure_room_under_site")
    i_table = seq.index("self._update_site_table")
    assert i_marker < i_room < i_table, (
        "_append_adopted_site 尾链顺序错：应 _append_site_to_layer < _ensure_room_under_site < "
        f"_update_site_table，实际 {seq}")


def test_m6_adopt_suggested_site_does_not_rebuild_table():
    """m6：`_adopt_suggested_site` **禁止**调用 `self._update_suggested_table`（崩溃防护）。

    本函数的调用者就是第 row 行那个按钮；重建表格会在 Qt 里立即析构正在发信号的 sender
    （「信号发射中删除 sender」崩溃模式）。应改为就地改该按钮文本/可用性。
    """
    fn = _func(_load_tree(), "_adopt_suggested_site")
    calls = _call_names(fn)
    assert "self._update_suggested_table" not in calls, (
        "_adopt_suggested_site 里出现了 self._update_suggested_table 调用 —— "
        "重建表格会析构正在发信号的 sender（Qt 崩溃）。单行采纳应就地改按钮。")


# ════════════════════ 三、矢量图层 / 防覆盖（修复 1~3 的接线保险）════════════════════

def test_append_adopted_site_writes_vector_layer():
    """修复 1：采纳站必须写进「基站设计」矢量图层，并保留机房 1:1 调用。"""
    fn = _func(_load_tree(), "_append_adopted_site")
    calls = _call_names(fn)
    assert "self._append_site_to_layer" in calls, (
        "_append_adopted_site 未调用 self._append_site_to_layer —— "
        "采纳站只画在画布 RubberBand 上，图层树看不到、按图层导出 PDF/CAD 拿不到")
    assert "self._ensure_room_under_site" in calls, \
        "_append_adopted_site 缺少 self._ensure_room_under_site（机房 1:1 建/绑定的回归保护）"


def test_generate_hex_grid_preserves_adopted_sites():
    """修复 2：重生成布局必须保留已采纳补盲站，且不得裸赋值 `self.generated_sites = sites`。"""
    fn = _func(_load_tree(), "_generate_hex_grid")
    has_literal = any(isinstance(n, ast.Constant) and n.value == "gap_adopt"
                      for n in ast.walk(fn))
    assert has_literal, \
        "_generate_hex_grid 未引用字面量 'gap_adopt'（无法区分/保留已采纳补盲站 → 重生成即抹掉）"
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and _dotted(n.targets[0]) == "self.generated_sites" \
                and isinstance(n.value, ast.Name) and n.value.id == "sites":
            raise AssertionError(
                "_generate_hex_grid 里出现裸赋值 `self.generated_sites = sites`："
                "会把已采纳补盲站整体抹掉（应合并 sites + adopted）")


def test_add_room_marker_wgs84_writes_room_layer():
    """修复 3：机房必须写进「机房」矢量图层（否则导出里看不到机房点位）。

    重构（补 2）后写图层的动作被抽取到 :meth:`_append_room_to_layer`，
    ``_add_room_marker_wgs84`` 改为委托它完成，故此处断言「委托」，
    并把「确会建图层」的最终保证压到 `_append_room_to_layer` 上。
    """
    fn = _func(_load_tree(), "_add_room_marker_wgs84")
    calls = _call_names(fn)
    assert "self._append_room_to_layer" in calls, (
        "_add_room_marker_wgs84 未委托 self._append_room_to_layer —— "
        "机房只画 RubberBand、没有点图层，PDF/CAD 导出无机房点位")
    assert "self._ensure_room_layer" in _call_names(
        _func(_load_tree(), "_append_room_to_layer")), (
        "_append_room_to_layer 未调用 self._ensure_room_layer（不建「机房」矢量图层）")


# ════════════════════ 四、补 1/补 2/图册选站（任务 #68 接线保险）════════════════════

def _log_call_uses_len_generated_sites(fn) -> bool:
    """函数体内是否存在 ``self._log(...)``，且其参数里出现 ``len(self.generated_sites)``。"""
    for n in ast.walk(fn):
        if not (isinstance(n, ast.Call) and _dotted(n.func) == "self._log"):
            continue
        args = list(n.args) + [kw.value for kw in n.keywords]
        for arg in args:
            for sub in ast.walk(arg):
                if (isinstance(sub, ast.Call) and _dotted(sub.func) == "len"
                        and len(sub.args) == 1
                        and _dotted(sub.args[0]) == "self.generated_sites"):
                    return True
    return False


def test_generate_hex_grid_log_counts_merged_pool():
    """补 1：`_generate_hex_grid` 的日志须用合并池 ``len(self.generated_sites)`` 计数。

    防回归：日志写 ``len(sites)``（只数六边形站）→ 本轮采纳的补盲站在日志里凭空消失，
    用户看到的数字比地图/表格里的站点少。
    """
    fn = _func(_load_tree(), "_generate_hex_grid")
    assert _log_call_uses_len_generated_sites(fn), (
        "_generate_hex_grid 的 self._log(...) 未使用 len(self.generated_sites) 计数 —— "
        "日志口径漏掉已采纳补盲站")


def test_generate_hex_grid_emits_merged_pool():
    """补 1：`design_completed` 应与日志口径一致，发合并后的全池（含采纳站）。

    依据 `docs/实施计划.md` 约定 ``emit(self.generated_sites)``；全仓 grep 无任何
    ``.connect`` 接收方，故该口径改动对运行期零影响。
    """
    fn = _func(_load_tree(), "_generate_hex_grid")
    found = False
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and _dotted(n.func) == "self.design_completed.emit":
            if n.args and _dotted(n.args[0]) == "self.generated_sites":
                found = True
    assert found, (
        "_generate_hex_grid 的 self.design_completed.emit(...) 未发 self.generated_sites —— "
        "信号口径漏掉已采纳补盲站")


def test_append_room_to_layer_is_idempotent():
    """补 2：`_append_room_to_layer` 须建「机房」图层，且对同一 ``room_id`` 幂等早退。"""
    fn = _func(_load_tree(), "_append_room_to_layer")
    assert "self._ensure_room_layer" in _call_names(fn), \
        "_append_room_to_layer 未调用 self._ensure_room_layer（不建「机房」矢量图层）"
    found = False
    for n in ast.walk(fn):
        if isinstance(n, ast.If) and any(isinstance(s, ast.Return) for s in n.body):
            for sub in ast.walk(n.test):
                if isinstance(sub, ast.Call) and _dotted(sub.func) == "any":
                    found = True
    assert found, (
        "_append_room_to_layer 缺少同一 room_id 的幂等守卫 `if any(...): return`"
        "（重复写会产生重复机房要素）")


def test_manual_room_paths_write_vector_layer():
    """补 2：两条**手工机房**路径（地图点击 / 坐标输入）也必须写「机房」矢量图层。

    防回归：`_on_room_clicked` / `_add_room_by_coord` 只调 `_add_room_marker`
    （画布 RubberBand），手工机房不进图层 → 图层树看不到、按图层导出 PDF/CAD 缺机房。
    """
    tree = _load_tree()
    for method in ("_on_room_clicked", "_add_room_by_coord"):
        calls = _call_names(_func(tree, method))
        assert "self._append_room_to_layer" in calls, (
            f"{method} 未调用 self._append_room_to_layer —— "
            "手工机房门只画 RubberBand，图层树/导出看不到")


def test_export_standard_drawset_has_station_selection():
    """图册选站：导出前用 QInputDialog.getItem 选站，且机房按 served_room_id 匹配。"""
    fn = _func(_load_tree(), "_export_standard_drawset")
    calls = _call_names(fn)
    assert "QInputDialog.getItem" in calls, \
        "_export_standard_drawset 未调用 QInputDialog.getItem（导出前无法选站）"
    has_all_label = any(isinstance(n, ast.Constant) and isinstance(n.value, str)
                        and "全部站点" in n.value for n in ast.walk(fn))
    assert has_all_label, "未找到「全部站点（每站一份 PDF）」批量选项文案"
    has_served = any(isinstance(n, ast.Constant) and n.value == "served_room_id"
                     for n in ast.walk(fn))
    assert has_served, \
        "_export_standard_drawset 未引用 served_room_id（单站机房无法按归属匹配）"


def test_export_standard_drawset_has_batch_branch():
    """图册批量：用 getExistingDirectory 选目录 + 逐站循环 + 文件名带 site_id + output_path。

    防回归：回退成「一次调用传 self.generated_sites」→ 引擎只画 sites[0]，
    多站/采纳站永远只出第一站。
    """
    fn = _func(_load_tree(), "_export_standard_drawset")
    calls = _call_names(fn)
    assert "QFileDialog.getExistingDirectory" in calls, \
        "_export_standard_drawset 无 QFileDialog.getExistingDirectory（批量导出无法选目录）"
    assert any(isinstance(n, ast.For) for n in ast.walk(fn)), \
        "_export_standard_drawset 无逐站导出循环（批量只出一份）"
    assert any(isinstance(n, ast.Constant) and isinstance(n.value, str)
               and "工程图册_" in n.value for n in ast.walk(fn)), \
        "_export_standard_drawset 未见 `工程图册_{site_id}.pdf` 文件名规则"
    has_output_path = any(
        isinstance(kw, ast.keyword) and kw.arg == "output_path"
        for n in ast.walk(fn) if isinstance(n, ast.Call) for kw in n.keywords)
    assert has_output_path, \
        "_export_standard_drawset 的引擎调用无 output_path 实参（批量会互相覆盖）"
    # 引擎调用必须 sites=[site]（单站），不得整池透传
    passes_single_site = any(
        isinstance(kw, ast.keyword) and kw.arg == "sites"
        and isinstance(kw.value, ast.List) and len(kw.value.elts) == 1
        for n in ast.walk(fn) if isinstance(n, ast.Call) for kw in n.keywords)
    assert passes_single_site, (
        "_export_standard_drawset 的引擎调用未传 sites=[site]（单站列表）—— "
        "整池透传会被引擎截成 sites[0]，只出一站")


# ════════════════════ 五、手工加站写图层（工单 ⑥-B 接线保险）════════════════════

def test_on_station_clicked_writes_vector_layer():
    """⑥-B：`_on_station_clicked`（手工加站）必须把站写进「基站设计」矢量图层。

    防回归：只画 RubberBand（无矢量图层）→ 手工加的站在会话内不进图层，
    图层树看不到、按图层导出 PDF/CAD/图册都缺这个站（与「手工机房不进图层」同族缺陷）。
    """
    fn = _func(_load_tree(), "_on_station_clicked")
    calls = _call_names(fn)
    assert "self._append_site_to_layer" in calls, (
        "_on_station_clicked 未调用 self._append_site_to_layer —— "
        "手工加站只画 RubberBand，图层树/导出看不到")


# ════════════════ 七、观感口径 B：去除随站 RubberBand（防死代码回归）════════════════════

def _has_method(tree, name) -> bool:
    """整棵 AST 里是否存在名为 ``name`` 的方法/函数定义。"""
    return any(isinstance(n, ast.FunctionDef) and n.name == name for n in ast.walk(tree))


def test_adopt_and_click_paths_do_not_draw_rubberband_marker():
    """观感口径 B：采纳站 / 手工加站**只**走「基站设计」矢量图层，不再画随站 RubberBand。

    防回归：重新给 `_append_adopted_site` / `_on_station_clicked` 加回 `self._add_marker(...)`
    → 会话内出现「矢量蓝点 + RubberBand 白圈/蓝圈」双标记，比六边形站显眼，观感不一致。
    """
    tree = _load_tree()
    for method in ("_append_adopted_site", "_on_station_clicked"):
        calls = _call_names(_func(tree, method))
        assert "self._add_marker" not in calls, (
            f"{method} 仍调用 self._add_marker —— 会话内会与「基站设计」矢量图层蓝点"
            "叠加成双标记（口径 B：只走矢量图层，不画随站 RubberBand）")


def test_add_marker_method_is_gone():
    """观感口径 B：`_add_marker` 方法（白圈 16 + 蓝圈 10 的画布临时标记）应已从类里删除。

    防回归：方法死灰复燃（未被调用的死代码）→ 后续可能被误接回，双标记再出现。
    """
    tree = _load_tree()
    assert not _has_method(tree, "_add_marker"), (
        "ui/design_dock.py 仍存在 _add_marker 方法定义 —— "
        "口径 B 已废弃该方法（统一走「基站设计」矢量图层），应彻底删除")


# ════════════════ 六、顺序 / 实参顺序敏感断言（堵独立 QA 的盲区 a/b/f）════════════════

def _subscript_str_key(node):
    """若 ``node`` 是 ``x['key']`` 形式且下标为常量字符串，返回 ``'key'``；否则 None。"""
    if not isinstance(node, ast.Subscript):
        return None
    sl = node.slice
    # Python < 3.9 的 `x['k']` 下标包着 ast.Index
    idx_t = getattr(ast, "Index", None)
    if idx_t is not None and isinstance(sl, idx_t):
        sl = sl.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
        return sl.value
    return None


def _attr_token(node) -> str:
    """把 ``setAttributes([...])`` 的一个实参元素规约成「字段名」token。

    - ``site_dict['site_id']`` / ``s['site_id']``（Subscript+常量键） → ``'site_id'``
    - ``room_id``（Name）                                            → ``'room_id'``
    - ``room_type or ""``（BoolOp）                                  → ``'room_type'``
    - 常量                                                           → 其字符串值
    """
    if isinstance(node, ast.Constant):
        return str(node.value)
    key = _subscript_str_key(node)
    if key is not None:
        return key
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.BoolOp):
        for v in node.values:
            tok = _attr_token(v)
            if tok:
                return tok
    if isinstance(node, ast.Attribute):
        return node.attr
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - 兜底
        return "<unknown>"


def _setattributes_tokens(fn):
    """取函数体内首个 ``<obj>.setAttributes([...])`` 的实参元素 token 列表。"""
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "setAttributes" and n.args
                and isinstance(n.args[0], ast.List)):
            return [_attr_token(e) for e in n.args[0].elts]
    return None


def _append_room_to_layer_lineno(fn):
    """函数体内 ``self._append_room_to_layer(...)`` 调用所在行号（None=未找到）。"""
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and _dotted(n.func) == "self._append_room_to_layer":
            return n.lineno
    return None


def _first_coord_rebind_lineno(fn):
    """函数体内**第一个「坐标重绑定」**行号（动态定位，不硬编码行号）。

    命中两类节点并取最小行号：
      • ``lon, lat = ...`` 这类多目标赋值（Tuple/List 目标同时含 lon、lat）；
      • 含 ``transform(`` 的调用表达式（坐标变换本身）。
    """
    lines = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, (ast.Tuple, ast.List)):
                    names = {e.id for e in t.elts if isinstance(e, ast.Name)}
                    if {"lon", "lat"} <= names:
                        lines.append(n.lineno)
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "transform"):
            lines.append(n.lineno)
    return min(lines) if lines else None


def test_m7_add_room_marker_wgs84_writes_before_coord_transform():
    """盲区 a（最高危）：`_add_room_marker_wgs84` 必须**在坐标变换之前**写「机房」图层。

    行号**动态**取自 AST：`self._append_room_to_layer(...)` 的调用行 必须 **严格早于**
    该函数体内第一个「坐标重绑定」行（`lon, lat = ...` / `transform(...)`）。
    后果：图层 feature 必须用原始 WGS84 经纬度写入；若在坐标变换之后写，点位会偏移到
    画布 CRS 数值处（错到天边）且静默无报错。
    """
    fn = _func(_load_tree(), "_add_room_marker_wgs84")
    append_line = _append_room_to_layer_lineno(fn)
    rebind_line = _first_coord_rebind_lineno(fn)
    assert append_line is not None, \
        "_add_room_marker_wgs84 内未找到 self._append_room_to_layer 调用"
    assert rebind_line is not None, (
        "_add_room_marker_wgs84 内未找到「坐标重绑定」（lon, lat = ... 或 transform(...)）—— "
        "断言 1 无法动态定位，需人工复核函数结构（不采用硬编码行号）")
    assert append_line < rebind_line, (
        "图层 feature 必须用原始 WGS84 经纬度写入；若在坐标变换之后写，"
        "点位会偏移到画布 CRS 数值处（错到天边）且静默无报错。"
        f" 实际 _append_room_to_layer@L{append_line} 不早于 坐标重绑定@L{rebind_line}")


def test_m8_site_setattributes_order_consistent():
    """盲区 b：`_append_site_to_layer` 与 `_add_sites_to_map` 的 setAttributes 字段顺序须一致，
    且等于 ``['site_id','name','site_type','tower_height']``（防 name/site_type 互换）。

    互换后站名会写进 site_type 字段 → 分类渲染与属性表全错。
    """
    tree = _load_tree()
    a = _setattributes_tokens(_func(tree, "_append_site_to_layer"))
    b = _setattributes_tokens(_func(tree, "_add_sites_to_map"))
    expected = ["site_id", "name", "site_type", "tower_height"]
    assert a == expected, \
        f"_append_site_to_layer setAttributes 字段顺序应为 {expected}，实际 {a}"
    assert b == expected, \
        f"_add_sites_to_map setAttributes 字段顺序应为 {expected}，实际 {b}"
    assert a == b, (
        "两函数 setAttributes 字段顺序不一致："
        f"_append_site_to_layer={a} vs _add_sites_to_map={b}")


def test_m9_room_setattributes_order():
    """盲区 f：`_append_room_to_layer` 的 setAttributes 字段顺序须等于
    ``['room_id','name','room_type']``（防 name/room_type 互换）。"""
    tokens = _setattributes_tokens(_func(_load_tree(), "_append_room_to_layer"))
    expected = ["room_id", "name", "room_type"]
    assert tokens == expected, \
        f"_append_room_to_layer setAttributes 字段顺序应为 {expected}，实际 {tokens}"
