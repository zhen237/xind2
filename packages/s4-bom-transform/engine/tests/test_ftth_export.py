"""
[S4-S1-迁移 §5.2 2026-09-22] FTTH 交付物上传式服务测试。

测试覆盖：
1. EXPECTED_DBF_LAYERS 完整性（8 层齐全）
2. 缺失 .dbf 时抛 FileNotFoundError
3. 复用 qgis-plugin/ftth.export_runner.export_from_dbf_single_workbook
4. 上传 8 个示例 .dbf → 生成合并 xlsx（使用仓库 docs/真实数据/Plan_de_récolement/Shape/）
5. 内存索引可查 → 触发下载路径
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from app.services import ftth_export
from app.services.ftth_export import (
    EXPECTED_DBF_LAYERS,
    _TASKS,
    export_ftth_deliverables,
    get_task,
)


# ── 8 层完整 .dbf 测试数据集 ─────────────────────────────────────
JAD_SHAPE_DIR = Path(
    r"C:\Users\RENXIN\Desktop\t1\xind2\docs\真实数据\Plan_de_récolement\Shape"
)
HAS_JAD_DATASET = JAD_SHAPE_DIR.is_dir() and all(
    (JAD_SHAPE_DIR / f"{layer}.dbf").exists() for layer in EXPECTED_DBF_LAYERS
)


# ── 1. 8 层清单契约 ────────────────────────────────────────────
def test_expected_dbf_layers_complete():
    """8 层清单必须齐全且顺序固定（与 qgis-plugin/ftth/field_map.LAYER_FILE_PREFIX 对齐）。"""
    assert EXPECTED_DBF_LAYERS == [
        "IMB", "SITE", "BOITE", "CABLE",
        "PTECH", "INFRASTRUCTURE", "ZNRO", "ZPM",
    ]


# ── 2. 缺失文件时报错 ────────────────────────────────────────────
def test_missing_dbf_raises_file_not_found(tmp_path):
    """只放 2 个 .dbf（IMB/SITE），其它缺失 → 抛 FileNotFoundError，列出缺失项。"""
    (tmp_path / "IMB.dbf").write_bytes(b"")
    (tmp_path / "SITE.dbf").write_bytes(b"")
    with pytest.raises(FileNotFoundError) as exc_info:
        export_ftth_deliverables(str(tmp_path), prefix="missing")
    msg = str(exc_info.value)
    assert "BOITE.dbf" in msg
    assert "CABLE.dbf" in msg
    assert "ZPM.dbf" in msg
    # 完整 8 层名称应在消息里
    for layer in EXPECTED_DBF_LAYERS:
        assert layer in msg


# ── 3. qgis-plugin/ftth 模块路径解析 ────────────────────────────
def test_qgis_plugin_path_resolves():
    """默认 S4_QGIS_PLUGIN_PATH 应推到仓库根/qgis-plugin，且存在 ftth/ 子目录。"""
    path = Path(ftth_export._QGIS_PLUGIN_PATH)
    assert path.exists(), f"QGIS plugin path not found: {path}"
    assert (path / "ftth").is_dir(), f"qgis-plugin/ftth missing under: {path}"
    assert (path / "ftth" / "export_runner.py").is_file()


# ── 4. 端到端：导出合并工作簿（用真实数据集） ─────────────────────
@pytest.mark.skipif(not HAS_JAD_DATASET, reason="JAD-MARJANE 真实数据集不可用，跳过")
def test_export_ftth_end_to_end_with_jad_dataset():
    """上传 JAD 完整 8 层 .dbf → 复用 ftth.export_runner 生成合并 xlsx。"""
    result = export_ftth_deliverables(str(JAD_SHAPE_DIR), prefix="pytest_jad")
    try:
        # 元数据
        assert result.task_id
        assert result.workbook_filename.startswith("pytest_jad_")
        assert result.workbook_filename.endswith("_FTTH_Deliverables.xlsx")
        assert os.path.exists(result.workbook_path), f"workbook 文件未生成：{result.workbook_path}"

        # 8 层记录数（与 EXPECTED_COUNTS_JAD 对齐）
        # qgis-plugin/ftth/field_map.py:125 EXPECTED_COUNTS_JAD
        assert result.layer_counts == {
            "IMB": 51, "SITE": 3, "BOITE": 118, "CABLE": 120,
            "PTECH": 141, "INFRASTRUCTURE": 193, "ZNRO": 1, "ZPM": 2,
        }

        # sheet 总数（每个 PM 一个熔接盘图 + 一个系统图 + 全局 2 个）
        # JAD 数据集 1 个 PM → 1×2 + 2 = 4 之外还有每 BPE/PBO 一个熔接盘图
        assert result.sheet_count >= 4, f"sheet_count 异常小：{result.sheet_count}"
        assert "光路由表" in result.sheet_names
        assert "光交箱汇总" in result.sheet_names

        # 内存索引可查
        cached = get_task(result.task_id)
        assert cached is not None
        assert cached.task_id == result.task_id
        assert cached.workbook_path == result.workbook_path
    finally:
        # 清理：避免 tmp 残留
        for attr in ("workbook_path", "ftth_json_path", "validation_path", "plan_path"):
            p = getattr(result, attr, None)
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        # 清索引
        _TASKS.pop(result.task_id, None)


# ── 5. 端到端：缺 1 层 → 不应成功（与 #2 不同：这里用真实数据集复制后删 1 层） ──
@pytest.mark.skipif(not HAS_JAD_DATASET, reason="JAD-MARJANE 真实数据集不可用，跳过")
def test_export_ftth_missing_one_layer_raises(tmp_path):
    """复制 7 层 .dbf 到临时目录，缺 ZPM → 抛 FileNotFoundError。"""
    for layer in EXPECTED_DBF_LAYERS:
        if layer == "ZPM":
            continue
        src = JAD_SHAPE_DIR / f"{layer}.dbf"
        dst = tmp_path / f"{layer}.dbf"
        shutil.copy(src, dst)
    with pytest.raises(FileNotFoundError) as exc_info:
        export_ftth_deliverables(str(tmp_path), prefix="missing_zpm")
    assert "ZPM.dbf" in str(exc_info.value)


# ── 6. 索引隔离：不同 task_id 互不干扰 ─────────────────────────
@pytest.mark.skipif(not HAS_JAD_DATASET, reason="JAD-MARJANE 真实数据集不可用，跳过")
def test_task_index_isolates_results():
    """两次导出应生成不同 task_id，互不覆盖。"""
    r1 = export_ftth_deliverables(str(JAD_SHAPE_DIR), prefix="iso1")
    r2 = export_ftth_deliverables(str(JAD_SHAPE_DIR), prefix="iso2")
    try:
        assert r1.task_id != r2.task_id
        assert r1.workbook_path != r2.workbook_path
        assert get_task(r1.task_id).task_id == r1.task_id
        assert get_task(r2.task_id).task_id == r2.task_id
    finally:
        for r in (r1, r2):
            for attr in ("workbook_path", "ftth_json_path", "validation_path", "plan_path"):
                p = getattr(r, attr, None)
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            _TASKS.pop(r.task_id, None)


# ── 7. 不存在的 task_id 查询返回 None ─────────────────────────
def test_get_unknown_task_returns_none():
    assert get_task("nonexistent_task_id_xxx") is None
