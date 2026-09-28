"""
[S4-S1-迁移 §5.2 2026-09-22] FTTH 交付物上传式 FastAPI 路由。
- POST /api/v1/ftth/upload  接收 8 个 .dbf multipart 文件 → 导出合并 xlsx + JSON + 自检报告
- GET  /api/v1/ftth/{task_id}    查询任务结果（sheet 列表 + 各层记录数）
- GET  /api/v1/ftth/{task_id}/download  下载合并 xlsx
- GET  /api/v1/ftth/{task_id}/validation  下载自检报告 JSON

参考交接说明：
  qgis-plugin/ftth/loader.py:38 load_dbf(shape_dir, pm_filter)
  qgis-plugin/ftth/export_runner.py:129 export_from_dbf_single_workbook(...)
"""
from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from app.services import ftth_export
from app.services.ftth_export import (
    EXPECTED_DBF_LAYERS,
    FtthExportResult,
    export_ftth_deliverables,
    get_task,
)

logger = logging.getLogger("s4-engine.ftth")

router = APIRouter(prefix="/api/v1/ftth", tags=["ftth"])


@router.post("/upload", summary="上传 8 个 .dbf 生成 FTTH 交付物合并工作簿")
async def upload_dbf_and_export(
    files: List[UploadFile] = File(..., description="8 个 .dbf 文件，文件名需匹配 IMB/SITE/BOITE/CABLE/PTECH/INFRASTRUCTURE/ZNRO/ZPM"),
    prefix: Optional[str] = "ftth",
):
    """上传完整 8 层 .dbf（IMB/SITE/BOITE/CABLE/PTECH/INFRASTRUCTURE/ZNRO/ZPM）→
    复用 qgis-plugin/ftth.export_runner.export_from_dbf_single_workbook 生成合并工作簿。
    """
    # ── 1. 校验文件齐全性 ─────────────────────────────────────────
    provided = {f.filename: f for f in files if f.filename}
    provided_stems = {os.path.splitext(name)[0].upper() for name in provided.keys()}
    missing = [l for l in EXPECTED_DBF_LAYERS if l not in provided_stems]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"缺少 .dbf 文件：{', '.join(m + '.dbf' for m in missing)}。"
                   f"需要完整 8 层：{', '.join(EXPECTED_DBF_LAYERS)}。当前上传：{sorted(provided.keys())}",
        )

    # ── 2. 保存到临时目录（文件名 = LAYER_FILE_PREFIX + ".dbf"） ──
    task_id = uuid.uuid4().hex[:12]
    tmp_dir = os.path.join(tempfile.gettempdir(), f"s4_ftth_upload_{task_id}")
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        for filename, upload in provided.items():
            stem = os.path.splitext(filename)[0].upper()
            # 归一化文件名（大写 + .dbf 后缀）
            target_name = stem + ".dbf"
            target_path = os.path.join(tmp_dir, target_name)
            content = await upload.read()
            with open(target_path, "wb") as fp:
                fp.write(content)
            logger.info("[ftth] saved %s (%d bytes) → %s", filename, len(content), target_path)

        # ── 3. 调 ftth_export 核心逻辑 ─────────────────────────────
        result = export_ftth_deliverables(tmp_dir, prefix=prefix or "ftth")
        logger.info(
            "[ftth] task %s done: sheet_count=%d layer_counts=%s elapsed_ms=%d",
            result.task_id, result.sheet_count, result.layer_counts, result.elapsed_ms,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("[ftth] export failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FTTH 导出失败：{type(e).__name__}: {e}",
        )

    # ── 4. 返回任务元数据（前端用于显示 sheet 列表 + 触发下载） ──
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "taskId": result.task_id,
            "workbookFilename": result.workbook_filename,
            "sheetCount": result.sheet_count,
            "sheetNames": result.sheet_names,
            "summary": result.summary,
            "layerCounts": result.layer_counts,
            "elapsedMs": result.elapsed_ms,
            "downloadUrl": f"/api/v1/ftth/{result.task_id}/download",
            "validationUrl": f"/api/v1/ftth/{result.task_id}/validation",
            "jsonUrl": f"/api/v1/ftth/{result.task_id}/json",
            "warning": "本产物由 S4 FTTH 上传式生成，数据口径源自 QGIS 插件 ftth.export_runner；"
                       "上传的 Shapefile 数据归用户所有。",
        },
    )


@router.get("/{task_id}", summary="查询 FTTH 导出任务结果")
async def get_ftth_task(task_id: str):
    result = get_task(task_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"task {task_id} 不存在或已过期")
    return {
        "taskId": result.task_id,
        "workbookFilename": result.workbook_filename,
        "sheetCount": result.sheet_count,
        "sheetNames": result.sheet_names,
        "layerCounts": result.layer_counts,
        "summary": result.summary,
        "elapsedMs": result.elapsed_ms,
        "downloadUrl": f"/api/v1/ftth/{result.task_id}/download",
        "validationUrl": f"/api/v1/ftth/{result.task_id}/validation",
        "jsonUrl": f"/api/v1/ftth/{result.task_id}/json",
    }


def _file_response_or_404(task_id: str, path_attr: str, media_type: str, filename: str):
    """通用文件响应：取 result.<path_attr>，404 兜底。"""
    result = get_task(task_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"task {task_id} 不存在或已过期")
    path = getattr(result, path_attr, None)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path_attr} 不存在")
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/{task_id}/download", summary="下载 FTTH 合并工作簿 xlsx")
async def download_workbook(task_id: str):
    result = get_task(task_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"task {task_id} 不存在或已过期")
    return FileResponse(
        result.workbook_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=result.workbook_filename,
    )


@router.get("/{task_id}/validation", summary="下载 FTTH 自检报告 JSON")
async def download_validation(task_id: str):
    return _file_response_or_404(
        task_id, "validation_path",
        media_type="application/json",
        filename=f"{task_id}_ftth-validation.json",
    )


@router.get("/{task_id}/json", summary="下载 FTTH 前端 JSON 数据")
async def download_ftth_json(task_id: str):
    return _file_response_or_404(
        task_id, "ftth_json_path",
        media_type="application/json",
        filename=f"{task_id}_ftth-data.json",
    )
