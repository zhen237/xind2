# -*- coding: utf-8 -*-
"""``design_engine.export_filter`` 纯函数单测。

靶心：``is_diagnosis_layer`` 是「导出 PDF/CAD 需排除诊断图层」的单一事实来源。
它必须**只**对「诊断·」前缀（含中点）的图层名返回 True，不能在其它名字上误判，
否则要么诊断层漏进交付图纸（橙区块 + 三角站与蓝点打架），要么误伤真实图层。

本模块零 QGIS 依赖，故可直接 import 断言，无需 ast 扫描。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_engine.export_filter import (  # noqa: E402
    DIAGNOSIS_LAYER_PREFIX,
    is_diagnosis_layer,
)


# ════════════════════════ 前缀常量语义 ════════════════════════

def test_prefix_is_diagnosis_with_middle_dot():
    """前缀须为带中点「·」的「诊断·」，诊断层名字以此开头。"""
    assert DIAGNOSIS_LAYER_PREFIX == "诊断·"


# ════════════════════════ True：诊断层 ════════════════════════

def test_true_for_weak_coverage_layer():
    """实际诊断图层「诊断·弱覆盖区」→ True。"""
    assert is_diagnosis_layer("诊断·弱覆盖区") is True


def test_true_for_suggested_site_layer():
    """实际诊断图层「诊断·建议补站」→ True。"""
    assert is_diagnosis_layer("诊断·建议补站") is True


def test_true_for_bare_prefix():
    """只有前缀「诊断·」也算诊断层（前缀本身即以它开头）。"""
    assert is_diagnosis_layer("诊断·") is True


# ════════════════════════ False：非诊断层 / 边界 ════════════════════════

def test_false_for_station_design_layer():
    """真实成果图层「基站设计」→ False（不被误排除）。"""
    assert is_diagnosis_layer("基站设计") is False


def test_false_for_heatmap_layer():
    """「覆盖热力图」→ False（热力图口径不归本模块，PDF/CAD 各自既有行为不变）。"""
    assert is_diagnosis_layer("覆盖热力图") is False


def test_false_for_empty_string():
    """空字符串 → False。"""
    assert is_diagnosis_layer("") is False


def test_false_for_none():
    """None → False（不抛错）。"""
    assert is_diagnosis_layer(None) is False


def test_false_when_missing_middle_dot():
    """「诊断弱覆盖区」缺中点 → False（避免把「诊断」开头的真实图层误排除）。"""
    assert is_diagnosis_layer("诊断弱覆盖区") is False


def test_false_for_room_layer():
    """「机房」→ False。"""
    assert is_diagnosis_layer("机房") is False


# ════════════ 非字符串输入（实现须兑现 docstring 的「全域」承诺）════════════

def test_false_for_int_without_raising():
    """整数（非字符串）→ False，不抛 AttributeError。"""
    assert is_diagnosis_layer(123) is False


def test_false_for_bytes_without_raising():
    """bytes → False（不做隐式解码、不抛 TypeError）。"""
    assert is_diagnosis_layer("诊断·弱覆盖区".encode("utf-8")) is False


def test_false_for_bool_without_raising():
    """布尔 True → False（bool 不是 str）。"""
    assert is_diagnosis_layer(True) is False


def test_false_for_list_without_raising():
    """列表 → False，不抛 AttributeError。"""
    assert is_diagnosis_layer(["诊断·弱覆盖区"]) is False
