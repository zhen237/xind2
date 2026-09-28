"""
[S4-S1-迁移 §5.2 2026-09-22] FTTH 交付物上传式导出服务。
复用仓库 `qgis-plugin/ftth/export_runner.export_from_dbf_single_workbook`：
- 接收 8 个 .dbf（IMB/SITE/BOITE/CABLE/PTECH/INFRASTRUCTURE/ZNRO/ZPM）
- 调 dbfread 离线装载（不依赖 PyQGIS；load_qgis 才依赖，本服务不调）
- 产出合并 Excel 工作簿（光路由表 + 光交箱汇总 + 每个 PM 的机柜熔接盘图 + 系统图）+ JSON + 自检报告

参考：
  qgis-plugin/ftth/field_map.py:131 LAYER_FILE_PREFIX = { "IMB": "IMB", ..., "ZPM": "ZPM" }
  qgis-plugin/ftth/export_runner.py:129 export_from_dbf_single_workbook(...)
  qgis-plugin/ftth/loader.py:38 load_dbf(shape_dir, pm_filter) → FtthProject
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ── 关键：把 qgis-plugin 加入 sys.path，复用其 ftth 模块 ─────────
# qgis-plugin/ftth 模块除 load_qgis 外不依赖 PyQGIS（load_dbf 用 dbfread）
# 见 qgis-plugin/ftth/__init__.py 与 loader.py:22-25 dbfread 是 try/except 软依赖
_QGIS_PLUGIN_PATH = os.environ.get(
    "S4_QGIS_PLUGIN_PATH",
    # 默认推导：s4-bom-transform/engine/app/services/ftth_export.py
    # → 上溯 5 层到仓库根 → 拼 qgis-plugin
    #   parents[0]=services, [1]=app, [2]=engine, [3]=s4-bom-transform, [4]=packages, [5]=xind2
    str(Path(__file__).resolve().parents[5] / "qgis-plugin"),
)
if _QGIS_PLUGIN_PATH and _QGIS_PLUGIN_PATH not in sys.path:
    sys.path.insert(0, _QGIS_PLUGIN_PATH)


# ── 8 个 dbf 表的期望前缀（与 field_map.LAYER_FILE_PREFIX 对齐） ──
EXPECTED_DBF_LAYERS: List[str] = [
    "IMB", "SITE", "BOITE", "CABLE",
    "PTECH", "INFRASTRUCTURE", "ZNRO", "ZPM",
]


@dataclass
class FtthExportResult:
    """FTTH 导出结果（在内存中保留文件路径供下载）。"""
    task_id: str
    workbook_path: str             # 合并 xlsx 文件路径
    workbook_filename: str         # 下载时的文件名
    sheet_count: int
    sheet_names: List[str]
    ftth_json_path: Optional[str]
    validation_path: Optional[str]
    plan_path: Optional[str]
    summary: Dict[str, object]
    layer_counts: Dict[str, int] = field(default_factory=dict)
    elapsed_ms: int = 0
    error: Optional[str] = None


# ── 内存中的 task 索引（task_id → 导出结果，含文件路径） ──────
# 设计：单进程 FastAPI 用内存索引；重启或 24h 后自动清理
_TASKS: Dict[str, FtthExportResult] = {}
_TASKS_LOCK = threading.Lock()
_TASKS_MAX_AGE_SEC = 24 * 3600


def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (s or "ftth"))


def _cleanup_stale_tasks() -> None:
    """清理过期任务（>24h）及其临时目录。"""
    now = time.time()
    with _TASKS_LOCK:
        stale = [
            tid for tid, r in _TASKS.items()
            if not os.path.exists(r.workbook_path)
            or now - os.path.getmtime(r.workbook_path) > _TASKS_MAX_AGE_SEC
        ]
    for tid in stale:
        _remove_task(tid)


def _remove_task(task_id: str) -> None:
    """移除任务索引并清理其临时目录。"""
    with _TASKS_LOCK:
        r = _TASKS.pop(task_id, None)
    if r is None:
        return
    for p in (r.workbook_path, r.ftth_json_path, r.validation_path, r.plan_path):
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    # 尝试清理父目录（每个 task 一个独立目录）
    parent = os.path.dirname(r.workbook_path)
    if parent and os.path.isdir(parent) and not os.listdir(parent):
        try:
            os.rmdir(parent)
        except OSError:
            pass


def get_task(task_id: str) -> Optional[FtthExportResult]:
    """查询任务结果（前端下载时用）。"""
    _cleanup_stale_tasks()
    return _TASKS.get(task_id)


def export_ftth_deliverables(
    uploaded_dbf_dir: str,
    prefix: str = "ftth",
    pm_filter: Optional[List[str]] = None,
) -> FtthExportResult:
    """从 8 个 .dbf 目录装载并生成合并工作簿。

    :param uploaded_dbf_dir: 已保存的 .dbf 文件目录（每个 layer 一个 .dbf，文件名 = LAYER_FILE_PREFIX + ".dbf"）
    :param prefix: 输出文件名前缀
    :param pm_filter: 可选 PM 编码列表（None=全部）
    :raises RuntimeError: qgis-plugin/ftth 不可用或 dbfread 未装
    :raises FileNotFoundError: 8 个 .dbf 不齐全
    """
    start = time.time()
    task_id = uuid.uuid4().hex[:12]

    # 校验 8 个 .dbf 齐全
    missing = [l for l in EXPECTED_DBF_LAYERS if not os.path.exists(os.path.join(uploaded_dbf_dir, l + ".dbf"))]
    if missing:
        raise FileNotFoundError(
            f"缺少 .dbf 文件：{', '.join(m + '.dbf' for m in missing)}。"
            f"需要完整 8 层：{', '.join(EXPECTED_DBF_LAYERS)}"
        )

    # 调 qgis-plugin/ftth 出口（动态 import，确保 S4_QGIS_PLUGIN_PATH 可配）
    try:
        from ftth.export_runner import export_from_dbf_single_workbook
    except ImportError as e:
        raise RuntimeError(
            f"无法 import qgis-plugin/ftth.export_runner：{e}。"
            f"已设置 sys.path[0]={_QGIS_PLUGIN_PATH}。请检查 S4_QGIS_PLUGIN_PATH 环境变量。"
        )

    # 输出目录：每个 task 一个独立临时目录（避免并发冲突）
    out_dir = os.path.join(tempfile.gettempdir(), f"s4_ftth_{task_id}")
    os.makedirs(out_dir, exist_ok=True)
    tag = _safe_name(prefix)
    if pm_filter:
        tag += "_" + "_".join(_safe_name(p) for p in sorted(pm_filter))

    # 核心调用：复用 QGIS 插件的 export_runner
    raw_result = export_from_dbf_single_workbook(uploaded_dbf_dir, out_dir, prefix=tag, pm_filter=pm_filter)

    # summary 是 FtthProject.summary() 的输出（dict），含 8 层记录数 + pm_code
    summary = raw_result.get("summary", {}) or {}
    sheet_names = raw_result.get("sheet_names", []) or []

    result = FtthExportResult(
        task_id=task_id,
        workbook_path=raw_result["workbook"],
        workbook_filename=os.path.basename(raw_result["workbook"]),
        sheet_count=raw_result["sheet_count"],
        sheet_names=sheet_names,
        ftth_json_path=raw_result.get("ftth_json"),
        validation_path=raw_result.get("validation"),
        plan_path=raw_result.get("plan"),
        summary=summary,
        layer_counts={
            "IMB": int(summary.get("IMB", 0)),
            "SITE": int(summary.get("SITE", 0)),
            "BOITE": int(summary.get("BOITE", 0)),
            "CABLE": int(summary.get("CABLE", 0)),
            "PTECH": int(summary.get("PTECH", 0)),
            "INFRASTRUCTURE": int(summary.get("INFRASTRUCTURE", 0)),
            "ZNRO": int(summary.get("ZNRO", 0)),
            "ZPM": int(summary.get("ZPM", 0)),
        },
        elapsed_ms=int((time.time() - start) * 1000),
    )

    with _TASKS_LOCK:
        _TASKS[task_id] = result
    return result
