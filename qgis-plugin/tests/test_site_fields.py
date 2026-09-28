# -*- coding: utf-8 -*-
"""site_fields.field() 兼容取值单测 + layout_export.py 源码扫描回归。

背景（本轮修复的靶心）
----------------------
图册引擎（``design_engine/layout_export.py``）原先用 ``getattr(site, "name", "")``
取字段，但 ``design_dock`` 传入的 ``self.generated_sites`` 是 **dict 列表**。
``getattr(dict_instance, "name", "")`` **不报错**、直接返回默认值 —— 于是真实
站名恒为"基站"、塔型恒为"MONOPOLE"、塔高恒为 35.0m，用户数据被静默丢弃。
``machine_rooms`` 是真正的 ``MachineRoom`` 对象列表，``getattr`` 恰好可用。

本文件两部分：
  1. ``field()`` 纯单元语义（dict / 对象 / None；含"键存在但值为 None"）；
  2. 对 ``layout_export.py`` 的源码/AST 扫描断言：
     - **不得**再出现 ``getattr(site,`` / ``getattr(room,``；
     - **必须** import ``site_fields``；
     - 且确实改用 ``field(site/room, ...)`` 取值。

不依赖 QGIS：``field()`` 零依赖；源码扫描只读文本与 AST。
运行：
    pytest tests/test_site_fields.py -q
    python tests/test_site_fields.py        # 无 pytest 时的等价自跑
"""
import ast
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_engine.site_fields import field  # noqa: E402

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAYOUT_EXPORT = os.path.join(_PLUGIN_ROOT, "design_engine", "layout_export.py")
_SITE_FIELDS = os.path.join(_PLUGIN_ROOT, "design_engine", "site_fields.py")


# --------------------------------------------------------------------------- #
#  测试数据
# --------------------------------------------------------------------------- #
def _generated_site_like() -> dict:
    """与 design_dock.generated_sites 元素**同构**的 dict（含 name/tower_*）。"""
    return {
        "site_id": "BTS-001",
        "name": "演示基站1",
        "site_type": "MACRO",
        "mount_type": "GROUND",
        "tower_type": "LATTICE",
        "tower_height": 45.0,
        "band": "3.5GHz",
        "tech_generation": "5G 独立组网(SA)",
        "longitude": 114.30,
        "latitude": 30.50,
    }


class _RoomLike:
    """与 models.machine_room.MachineRoom 同构的对象（用来验证 getattr 分支）。"""

    def __init__(self):
        self.name = "汇聚机房A"
        self.room_type = "汇聚机房"
        self.power_supply = "AC220V"
        self.capacity = 50.0


# --------------------------------------------------------------------------- #
#  1. field() 语义
# --------------------------------------------------------------------------- #
def test_dict_hit_returns_real_value():
    assert field({"name": "基站A"}, "name") == "基站A"


def test_dict_missing_key_returns_default():
    assert field({"name": "基站A"}, "missing", "默认") == "默认"
    assert field({"name": "基站A"}, "missing") is None


def test_dict_key_present_value_none_returns_none():
    """键存在但值为 None → 返回 None，不当缺失去取 default。"""
    assert field({"name": None}, "name", "默认") is None


def test_object_hit_returns_real_value():
    r = _RoomLike()
    assert field(r, "name") == "汇聚机房A"
    assert field(r, "capacity") == 50.0


def test_object_missing_attr_returns_default():
    r = _RoomLike()
    assert field(r, "nonexistent", "X") == "X"
    assert field(r, "nonexistent") is None


def test_object_attr_present_value_none_returns_none():
    """对象属性值为 None 时与 dict 语义保持一致：返回 None 而非 default。"""

    class _C:
        name = None

    assert field(_C(), "name", "默认") is None


def test_none_obj_returns_default_without_raising():
    assert field(None, "name", "D") == "D"
    assert field(None, "name") is None


def test_mapping_subclass_uses_get_branch():
    """dict 子类（OrderedDict）走 Mapping 分支。"""
    od = OrderedDict([("name", "基站X")])
    assert field(od, "name") == "基站X"
    assert field(od, "missing", "D") == "D"


# ---- 真实场景：修复的靶心（旧 getattr 会丢数据，field 必须保住） ----
def test_real_generated_site_name_not_lost():
    s = _generated_site_like()
    assert field(s, "name", "") == "演示基站1"


def test_real_generated_site_tower_height_not_lost():
    s = _generated_site_like()
    assert field(s, "tower_height", 35.0) == 45.0


def test_real_generated_site_tower_type_not_lost():
    s = _generated_site_like()
    assert field(s, "tower_type", "MONOPOLE") == "LATTICE"


def test_old_getattr_would_have_lost_dict_data():
    """反证对照：旧写法 getattr(dict,...) 确实取不到，field 能取到。"""
    s = _generated_site_like()
    assert getattr(s, "name", "") == ""          # 旧写法：丢数据
    assert field(s, "name", "") == "演示基站1"   # 新写法：保住


def test_dict_station_has_no_bill_of_materials():
    """dict 站点没有该方法 → field 取到 None（供 _bom_table_svg 判空）。"""
    s = _generated_site_like()
    assert field(s, "bill_of_materials") is None


def test_object_bill_of_materials_is_callable():
    class _S:
        def bill_of_materials(self):
            return {"items": [{"name": "单管塔"}]}

    m = field(_S(), "bill_of_materials")
    assert callable(m)
    assert m() == {"items": [{"name": "单管塔"}]}


# --------------------------------------------------------------------------- #
#  2. site_fields 零依赖守卫
# --------------------------------------------------------------------------- #
def _imported_roots(source: str) -> set:
    roots = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for n in node.names:
                roots.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_site_fields_has_no_qgis_or_pyqt_import():
    with open(_SITE_FIELDS, encoding="utf-8") as f:
        roots = _imported_roots(f.read())
    assert "qgis" not in roots, roots
    assert "PyQt5" not in roots, roots
    assert not any("PyQt" in r for r in roots), roots
    # __future__ / typing 属预期，其余不应出现
    assert roots <= {"__future__", "typing"}, roots


# --------------------------------------------------------------------------- #
#  3. layout_export.py 源码扫描断言
# --------------------------------------------------------------------------- #
_RE_GETATTR_SITE = re.compile(r"getattr\s*\(\s*site\b")
_RE_GETATTR_ROOM = re.compile(r"getattr\s*\(\s*room\b")
_RE_FIELD_IMPORT = re.compile(
    r"from\s+(?:\.|design_engine\.)site_fields\s+import\s+field")
_RE_FIELD_SITE = re.compile(r"\bfield\(\s*site\b")
_RE_FIELD_ROOM = re.compile(r"\bfield\(\s*room\b")


def _layout_source() -> str:
    with open(_LAYOUT_EXPORT, encoding="utf-8") as f:
        return f.read()


def _hits(pattern: re.Pattern, source: str):
    return [(i, ln.strip()) for i, ln in enumerate(source.splitlines(), 1)
            if pattern.search(ln)]


def test_layout_export_no_getattr_site():
    hits = _hits(_RE_GETATTR_SITE, _layout_source())
    assert not hits, "layout_export.py 仍存在 getattr(site,...) 取字段: %r" % hits


def test_layout_export_no_getattr_room():
    hits = _hits(_RE_GETATTR_ROOM, _layout_source())
    assert not hits, "layout_export.py 仍存在 getattr(room,...) 取字段: %r" % hits


def test_layout_export_ast_no_getattr_on_site_or_room():
    """AST 级复核（不受注释/字符串干扰）：不存在 getattr(site/room, ...) 调用。"""
    bad = []
    for node in ast.walk(ast.parse(_layout_source())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "getattr" and node.args:
            a0 = node.args[0]
            if isinstance(a0, ast.Name) and a0.id in ("site", "room"):
                bad.append((node.lineno, a0.id))
    assert not bad, "AST 发现 getattr(site/room, ...) 调用: %r" % bad


def test_layout_export_imports_site_fields():
    assert _RE_FIELD_IMPORT.search(_layout_source()), \
        "layout_export.py 未 import site_fields.field"


def test_layout_export_uses_field_for_site_and_room():
    src = _layout_source()
    n_site = len(_RE_FIELD_SITE.findall(src))
    n_room = len(_RE_FIELD_ROOM.findall(src))
    # 基线：site 11 处（bill_of_materials 1 + tower_type 2 + tower_height 2 + name 6）
    #       room  5 处（name 2 + room_type 1 + power_supply 1 + capacity 1）
    assert n_site >= 11, "field(site, ...) 仅 %d 处（应 >= 11）" % n_site
    assert n_room >= 5, "field(room, ...) 仅 %d 处（应 >= 5）" % n_room


# --------------------------------------------------------------------------- #
#  无 pytest 时的等价自跑
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    _fns = [(n, f) for n, f in sorted(globals().items())
            if n.startswith("test_") and callable(f)]
    _failed = 0
    for _name, _fn in _fns:
        try:
            _fn()
        except Exception as _exc:  # noqa: BLE001
            _failed += 1
            print("FAIL  %s\n      %s: %s"
                  % (_name, type(_exc).__name__, _exc))
        else:
            print("PASS  %s" % _name)
    print("\n%d/%d passed" % (len(_fns) - _failed, len(_fns)))
    sys.exit(1 if _failed else 0)
