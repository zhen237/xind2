"""链路余量 · 通俗解释落点保险 — ui/design_dock.py

``ui/design_dock.py`` 顶层 import ``qgis`` / ``PyQt5``，本机无 QGIS 时**无法 import**，
故用 ``ast.parse`` 静态读源码，锁死三处「链路余量通俗解释」落点：

  1. ``GLOSSARY`` 字典里有 ``链路余量`` 词条（hover 到「链路余量(dB)」标签即弹出）；
  2. 面板里有一条**常驻可见**的「大白话」helper 标签（不靠悬停就能看到）；
  3. ``self.link_margin_spin`` 的 tooltip 自身也改成通俗版（含关键词「安全垫」）。

含三条 in-memory 反证：故意删/改源码后，对应断言必须变红，证明锁不是空转。
"""
import ast
import os

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCK_PATH = os.path.join(PLUGIN_DIR, "ui", "design_dock.py")


def _load_source(path=DOCK_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ── 纯检查函数（吃源码字符串，便于反证复用）─────────────────

def check_glossary_entry(src):
    """GLOSSARY 必须含 '链路余量' 词条，且解释里点出「安全垫」与「覆盖诊断」口径。"""
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "GLOSSARY" and isinstance(n.value, ast.Dict):
                    for k, v in zip(n.value.keys, n.value.values):
                        if isinstance(k, ast.Constant) and k.value == "链路余量":
                            assert isinstance(v, ast.Constant) and isinstance(v.value, str), \
                                "GLOSSARY['链路余量'] 必须是字符串"
                            val = v.value
                            assert "安全垫" in val, "词条必须含通俗关键词「安全垫」"
                            assert "覆盖诊断" in val, "词条必须说明「覆盖诊断」口径才减"
                            return
    raise AssertionError("GLOSSARY 缺少 '链路余量' 词条")


def check_inline_helper(src):
    """面板里必须有一条常驻可见的「大白话」helper 标签。"""
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and "大白话" in n.value:
            return
    raise AssertionError("未找到常驻可见的「大白话」helper 标签")


def check_spinbox_tooltip(src):
    """self.link_margin_spin.setToolTip(...) 必须含通俗关键词「安全垫」。"""
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "setToolTip":
            recv = n.func.value
            if (isinstance(recv, ast.Attribute) and recv.attr == "link_margin_spin"
                    and isinstance(recv.value, ast.Name) and recv.value.id == "self"):
                texts = []
                for a in n.args:
                    for c in ast.walk(a):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str):
                            texts.append(c.value)
                blob = "".join(texts)
                assert "安全垫" in blob, \
                    "link_margin_spin 的 tooltip 必须改成通俗版（含「安全垫」）"
                return
    raise AssertionError("未找到 self.link_margin_spin.setToolTip(...)")


# ── pytest 入口（对真实文件）──────────────────────────────

def test_link_margin_in_glossary():
    check_glossary_entry(_load_source())


def test_link_margin_inline_helper():
    check_inline_helper(_load_source())


def test_link_margin_spinbox_tooltip():
    check_spinbox_tooltip(_load_source())


# ── in-memory 反证（故意破坏必须变红）────────────────────

def test_refutation_glossary_lock():
    src = _load_source()
    mutated = "\n".join(ln for ln in src.splitlines() if '"链路余量":' not in ln)
    try:
        check_glossary_entry(mutated)
    except AssertionError:
        return
    raise AssertionError("反证失败：删掉 GLOSSARY 词条后检查居然通过")


def test_refutation_inline_helper_lock():
    src = _load_source()
    mutated = "\n".join(ln for ln in src.splitlines() if "大白话" not in ln)
    try:
        check_inline_helper(mutated)
    except AssertionError:
        return
    raise AssertionError("反证失败：删掉「大白话」helper 后检查居然通过")


def test_refutation_spinbox_tooltip_lock():
    src = _load_source()
    mutated = src.replace("安全垫", "安全余量")  # 把通俗关键词从全局抹掉
    try:
        check_spinbox_tooltip(mutated)
    except AssertionError:
        return
    raise AssertionError("反证失败：抹掉 tooltip 里的「安全垫」后检查居然通过")
