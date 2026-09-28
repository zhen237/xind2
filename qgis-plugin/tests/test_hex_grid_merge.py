"""resolve_site_id_conflicts 单测 — design_engine/hex_grid.py

纯函数（无 QGIS 依赖），可真跑。覆盖：无冲突 / 单个冲突顺延 / 多个连续冲突 /
taken_ids 为空（含 None）/ 不改入参。
"""
import copy
import os
import sys

# 添加插件目录到路径（沿用 tests/test_gap_diagnosis.py 的写法）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_engine.hex_grid import resolve_site_id_conflicts


def _hs(site_id, **kw):
    d = {"site_id": site_id, "name": "n"}
    d.update(kw)
    return d


def test_no_conflict_ids_unchanged():
    """无冲突：所有 site_id 原样保留。"""
    hex_sites = [_hs("BTS-URBA-001"), _hs("BTS-URBA-002"), _hs("BTS-URBA-003")]
    out = resolve_site_id_conflicts(hex_sites, {"BTS-RURA-010"})
    assert [s["site_id"] for s in out] == ["BTS-URBA-001", "BTS-URBA-002", "BTS-URBA-003"]
    assert len(out) == len(hex_sites)


def test_single_conflict_shifts_to_global_max_plus_one():
    """单个冲突：撞号者顺延到「全局最大序号 + 1」，其余不动。"""
    hex_sites = [_hs("BTS-URBA-001"), _hs("BTS-URBA-002"), _hs("BTS-URBA-003")]
    out = resolve_site_id_conflicts(hex_sites, {"BTS-URBA-002"})
    ids = [s["site_id"] for s in out]
    assert ids[0] == "BTS-URBA-001"
    assert ids[2] == "BTS-URBA-003"
    # 002 撞号 → 全局最大(3) + 1 = 004
    assert ids[1] == "BTS-URBA-004"
    # 全局唯一（含 taken_ids）
    assert len(set(ids) | {"BTS-URBA-002"}) == len(ids) + 1


def test_multiple_consecutive_conflicts_shift_incrementally():
    """多个连续冲突：逐条顺延（004/005/006），互不相同。"""
    hex_sites = [_hs("BTS-URBA-001"), _hs("BTS-URBA-002"), _hs("BTS-URBA-003")]
    taken = {"BTS-URBA-001", "BTS-URBA-002", "BTS-URBA-003"}
    out = resolve_site_id_conflicts(hex_sites, taken)
    ids = [s["site_id"] for s in out]
    assert ids == ["BTS-URBA-004", "BTS-URBA-005", "BTS-URBA-006"]
    assert len(set(ids)) == 3
    # 与 taken 也两两不撞
    assert set(ids).isdisjoint(taken)


def test_empty_taken_ids():
    """taken_ids 为空 / None：全部原样保留。"""
    hex_sites = [_hs("BTS-URBA-001"), _hs("BTS-URBA-002")]
    assert [s["site_id"] for s in resolve_site_id_conflicts(hex_sites, set())] \
        == ["BTS-URBA-001", "BTS-URBA-002"]
    assert [s["site_id"] for s in resolve_site_id_conflicts(hex_sites, None)] \
        == ["BTS-URBA-001", "BTS-URBA-002"]


def test_does_not_mutate_inputs():
    """不改入参：hex_sites 的 dict 与 taken_ids 均保持原状。"""
    hex_sites = [_hs("BTS-URBA-001"), _hs("BTS-URBA-002")]
    taken = {"BTS-URBA-002"}
    snapshot_hex = copy.deepcopy(hex_sites)
    snapshot_taken = set(taken)
    _ = resolve_site_id_conflicts(hex_sites, taken)
    assert hex_sites == snapshot_hex, "入参 hex_sites 被修改（不得原地改）"
    assert taken == snapshot_taken, "入参 taken_ids 被修改（不得原地改）"
