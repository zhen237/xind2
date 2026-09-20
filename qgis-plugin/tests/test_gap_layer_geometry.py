"""诊断图层几何回归测试 — layers/gap_layer.py

只读断言**几何/建面边长**纯函数，不 import ``qgis`` / ``PyQt5``：
``layers/gap_layer.py`` 顶层仅 import ``math`` / ``warnings`` / ``typing`` 与
``design_engine.gap_diagnosis``，QGIS 全部在函数内部导入，故本机无 QGIS 也能直接
import 该模块、调用纯函数。硬约束：本测试**不得**依赖 QGIS / PyQt。

覆盖用户真机截图暴露的"弱覆盖面放大 100 倍、漫出设计区域"缺陷：
    根因 —— 建面用了**聚类网格**尺寸 cell_m（2.6GHz→1000m），而非各弱格自带的
    **采样**边长（100m）。100m 采样格被画成 1000m 方块 = 单格面积 ×100、
    四周各外扩 ~450m，故必然溢出设计区域。
"""
import ast
import inspect
import math
import os
import sys

# 添加插件目录到路径（沿用 tests/test_gap_layer_style.py 的写法）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_engine.gap_diagnosis import WeakCell
from layers.gap_layer import (
    _M_PER_DEG_LAT,
    _M_PER_DEG_LON_EQ,
    _cell_side_m,
    _square_ring,
    build_rsrp_weak_layer,
)


class _BareSite:
    """一个**没有** cell_m 属性的最小对象（模拟缺字段的老数据）。"""


def _make_cell(cell_m):
    """造一个只关心 cell_m 的 WeakCell（其余字段给合规占位值）。"""
    return WeakCell(
        row=0, col=0, lon=116.0, lat=30.0, rsrp=-105.0, level="weak", cell_m=cell_m,
    )


def _ring_span_m(ring, lat):
    """把正方形环的经/纬向度数跨度换算回**米**（用模块自身常量 + cos 修正）。"""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    span_we_m = (max(xs) - min(xs)) * _M_PER_DEG_LON_EQ * math.cos(math.radians(lat))
    span_ns_m = (max(ys) - min(ys)) * _M_PER_DEG_LAT
    return span_we_m, span_ns_m


# ════════════════════ 1. 优先用格自带的 cell_m（采样边长） ════════════════════

def test_cell_side_prefers_own_cell_m():
    """WeakCell.cell_m=100 时，无论调用方传 1000（聚类网格）还是别的，都必须返回 100.0。"""
    cell = _make_cell(100.0)
    assert _cell_side_m(cell, 1000.0) == 100.0
    assert _cell_side_m(cell, 1000.0) != 1000.0


# ════════════════════ 2. 取不到时回退到调用方传入值 ════════════════════

def test_cell_side_fallback():
    """cell_m 为 0 / None / 缺失 / 负数 / 非数字串 → 一律回退传入值，且不抛异常。"""
    assert _cell_side_m(_make_cell(0.0), 1000.0) == 1000.0
    assert _cell_side_m(_make_cell(None), 1000.0) == 1000.0
    assert _cell_side_m(_BareSite(), 1000.0) == 1000.0
    assert _cell_side_m(_make_cell(-5), 1000.0) == 1000.0
    # 非数字字符串：不得抛异常，走回退。
    assert _cell_side_m(_make_cell("abc"), 1000.0) == 1000.0


# ════════════════════ 3. 正方形环边长与请求米数一致（几何后果入测） ════════════════════

def test_square_ring_side_matches_requested_meters():
    """_square_ring(_, _, 100) 的东西/南北跨度 ≈ 100m；1000 → ≈1000m；两者相差约 10 倍。"""
    lat = 30.0
    ring_100 = _square_ring(116.0, lat, 100)
    ring_1000 = _square_ring(116.0, lat, 1000)

    we_100, ns_100 = _ring_span_m(ring_100, lat)
    we_1000, ns_1000 = _ring_span_m(ring_1000, lat)

    # 100m 环：东西/南北跨度均在 100m ± 1m 内（换算误差容差）。
    assert abs(we_100 - 100.0) <= 1.0
    assert abs(ns_100 - 100.0) <= 1.0
    # 1000m 环：同样是请求边长。
    assert abs(we_1000 - 1000.0) <= 1.0
    assert abs(ns_1000 - 1000.0) <= 1.0
    # 把 bug 的几何后果写进测试：1000m 环边长 ≈ 100m 环的 10 倍。
    assert abs(we_1000 / we_100 - 10.0) <= 0.1
    assert abs(ns_1000 / ns_100 - 10.0) <= 0.1


# ════════════════════ 4. 建面边长只认采样分辨率，不受聚类网格影响 ════════════════════

def test_weak_layer_side_is_sampling_resolution_not_cluster_grid():
    """同一个 WeakCell，调用方传 1000 或 100 都应得到相同的 100.0。

    这正是根因修复要保证的不变量：调用方（历史 bug 曾传聚类网格尺寸 cell_m）传什么
    聚类尺寸都不再影响建面 —— 建面恒用格自带的采样边长。
    """
    cell = _make_cell(100.0)
    assert _cell_side_m(cell, 1000.0) == _cell_side_m(cell, 100.0) == 100.0


# ════════════════════ 5. 环路确实用 _cell_side_m 建面（接线回归防线） ════════════════════

def test_weak_layer_builds_side_via_cell_side_m():
    """`build_rsrp_weak_layer` 的建面必须来自 `_cell_side_m(cell, cell_m)`，而非 `float(cell_m)`。

    本机无 QGIS，跑不起真正的建面循环，故用 AST 静态锁定**接线**：直接把建面边长传
    `float(cell_m)`（聚类网格）就是本次"弱区放大 100 倍"的根因。用例 1/4 只测纯函数
    `_cell_side_m` 本身，**抓不住**"函数正确但没被调用"的回归，故补这一条。
    """
    tree = ast.parse(inspect.getsource(build_rsrp_weak_layer))
    square_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "_square_ring"
    ]
    assert len(square_calls) == 1, "应恰有一处 _square_ring 调用"
    call = square_calls[0]
    assert len(call.args) >= 3, "_square_ring 至少 3 个位置参数（lon, lat, side）"
    side_expr = call.args[2]  # 第 3 个位置参数 = 建面边长
    assert isinstance(side_expr, ast.Call), "建面边长应是函数调用，而非裸变量"
    assert getattr(side_expr.func, "id", None) == "_cell_side_m", \
        f"建面边长必须经 _cell_side_m 取值，实际为 {ast.dump(side_expr)}"
