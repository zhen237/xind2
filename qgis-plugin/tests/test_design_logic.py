"""design_logic 纯逻辑单元测试（不依赖 QGIS 环境）。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.design_logic import (
    resolve_report_target,
    drawing_type_for_index,
    should_fallback_local,
    CSV, TXT, DRAWING_PDF, DRAWING_FTTH,
)


# ── resolve_report_target ──
def test_report_cancel_returns_none():
    assert resolve_report_target("", "CSV 表格 (*.csv)") == ("", None)


def test_report_csv_filter_appends_extension():
    fpath, fmt = resolve_report_target("方案A", "CSV 表格 (*.csv)")
    assert fpath == "方案A.csv"
    assert fmt == CSV


def test_report_txt_filter_appends_extension():
    fpath, fmt = resolve_report_target("方案A", "文本文件 (*.txt)")
    assert fpath == "方案A.txt"
    assert fmt == TXT


def test_report_keeps_existing_csv_extension():
    fpath, fmt = resolve_report_target("方案A.csv", "文本文件 (*.txt)")
    assert fpath == "方案A.csv"
    assert fmt == CSV


def test_report_keeps_existing_txt_extension():
    fpath, fmt = resolve_report_target("方案A.txt", "CSV 表格 (*.csv)")
    assert fpath == "方案A.txt"
    assert fmt == TXT


# ── drawing_type_for_index ──
def test_drawing_index_ftth():
    assert drawing_type_for_index(1) == DRAWING_FTTH


def test_drawing_index_pdf_default():
    assert drawing_type_for_index(0) == DRAWING_PDF
    assert drawing_type_for_index(2) == DRAWING_PDF


# ── should_fallback_local ──
def test_fallback_on_engine_error():
    assert should_fallback_local(0, 0, False, True) is True


def test_fallback_when_no_new_site_and_no_device():
    # 引擎未抛异常，但站点数不变且无设备清单 -> 兜底
    assert should_fallback_local(0, 0, False, False) is True


def test_no_fallback_when_site_added():
    assert should_fallback_local(0, 3, False, False) is False


def test_no_fallback_when_device_layout_present():
    # 站点数未变但引擎产出了设备清单 -> 视为有效，不兜底
    assert should_fallback_local(0, 0, True, False) is False
