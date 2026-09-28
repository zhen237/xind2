"""诊断图层样式回归测试 — layers/gap_layer.py

只读断言模块级**样式常量**，不 import ``qgis`` / ``PyQt5``：
``layers/gap_layer.py`` 顶层仅 import ``math`` / ``warnings`` / ``typing`` 与
``design_engine.gap_diagnosis``，QGIS 全部在函数内部导入，故本机无 QGIS 也能直接
import 该模块、读取常量。硬约束：本测试**不得**依赖 QGIS / PyQt。

覆盖用户真机验收暴露的两类"看得见"缺陷：
    1. 建议站 demand_score 恰好 100.0 时分级区间 [下界, 上界) 落空 → 站点凭空消失；
    2. 建议站与现有基站同为白描边圆点，压在橙色弱区上无法区分。
"""
import os
import re
import sys

# 添加插件目录到路径（沿用 tests/test_gap_diagnosis.py 的写法）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layers.gap_layer import (
    _SCORE_GRADES,
    _SUGGESTED_MARKER_SHAPE,
    _SUGGESTED_OUTLINE,
)


def _relative_luminance(hex_color: str) -> float:
    """WCAG 相对亮度（sRGB 线性化后加权）。返回 [0, 1]，黑→0，白→1。"""
    h = hex_color.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ════════════════════ 1. 分级区间无缝、无重叠、覆盖 [0, 100] ════════════════════

def test_score_grades_cover_full_range_without_gap():
    """分级区间必须首尾覆盖 [0, 100]、相邻档上界 == 下界（无缝隙无重叠）。

    这是抓住「demand_score 恰好 100.0 落空 → 站点无符号、地图上消失」的断言：
    QGIS 分级区间为 [下界, 上界)，若最后一档上界写成 100.0，则 100.0 落在所有
    区间之外。此处要求最后一档上界**严格大于** 100.0。
    """
    assert _SCORE_GRADES, "分级表不能为空"
    # 第一档下界须覆盖到 0.0 及以下。
    assert _SCORE_GRADES[0][0] <= 0.0
    # 相邻档：上一档上界 == 下一档下界（无缝隙、无重叠）。
    for (_, upper, _, _), (lower_next, _, _, _) in zip(_SCORE_GRADES, _SCORE_GRADES[1:]):
        assert upper == lower_next, f"区间断裂/重叠：{upper} != {lower_next}"
    # 最后一档上界须覆盖到 100.0。注意：QGIS 分级区间为 [下界, 上界)（左闭右开），
    # 而上界写成恰好 100.0 时，可达最高分 100.0 会落在**所有**区间之外 → 该站点无符号、
    # 在地图上消失。故上界必须**严格大于** 100.0（写成 >= 100.0 抓不住这个洞）。
    assert _SCORE_GRADES[-1][1] > 100.0, \
        f"最后一档上界={_SCORE_GRADES[-1][1]} 未严格覆盖 100.0（[下界,上界) 会落空）"


# ════════════════════ 2. 每档颜色为合法 6 位十六进制 ════════════════════

def test_score_grades_colors_are_valid_hex():
    """每档颜色必须匹配 ^#[0-9A-Fa-f]{6}$（防手滑写成 3 位/缺 #/非法字符）。"""
    pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
    for _, _, color, _ in _SCORE_GRADES:
        assert pattern.match(color), f"非法颜色：{color!r}"


# ════════════════════ 3. 描边为深色（压在橙色弱区上可辨） ════════════════════

def test_suggested_outline_is_dark():
    """描边相对亮度 < 0.5（防有人改回 #FFFFFF 这类浅色描边，压在 #FFA500 上等于没描边）。"""
    assert re.match(r"^#[0-9A-Fa-f]{6}$", _SUGGESTED_OUTLINE), \
        f"描边非合法 hex：{_SUGGESTED_OUTLINE!r}"
    assert _relative_luminance(_SUGGESTED_OUTLINE) < 0.5, \
        f"描边过亮（相对亮度={_relative_luminance(_SUGGESTED_OUTLINE):.3f}）：{_SUGGESTED_OUTLINE}"


# ════════════════════ 4. 符号形状非圆形（区别于现有基站圆点） ════════════════════

def test_suggested_marker_shape_is_not_circle():
    """符号形状必须属于非圆形集合（现有基站是圆点，同形状不可区分）。"""
    non_circle = {
        "triangle", "star", "diamond", "square",
        "pentagon", "hexagon", "regular_star",
    }
    assert _SUGGESTED_MARKER_SHAPE in non_circle, \
        f"形状 {_SUGGESTED_MARKER_SHAPE!r} 非可区分非圆形：{sorted(non_circle)}"
    assert _SUGGESTED_MARKER_SHAPE != "circle"
