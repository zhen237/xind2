"""
BOM 生成核心路由 (FR-1~FR-8)。
/api/v1/bom/generate — 主入口（串联全部引擎模块）
/api/v1/bom/export   — Excel 导出
"""
import json
import logging
from pathlib import Path

import requests
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse

from app.services import bom_engine, process_requirements, fiber_allocation, excel_export
from app.services.design_source import load_design

router = APIRouter()
logger = logging.getLogger("s4-engine.bom")

EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "exports"


def _normalize_devices(design_data: dict) -> dict:
    """归一化设备字段，兼容 D001/D002/D003 不同 mock 数据格式。"""
    devices = design_data.get("devices", [])
    normalized = []
    for dev in devices:
        nd = dict(dev)
        if "deviceType" in nd and "type" not in nd:
            nd["type"] = nd["deviceType"]
        if "deviceModel" in nd and "model" not in nd:
            nd["model"] = nd["deviceModel"]
        if "deviceName" in nd and "name" not in nd:
            nd["name"] = nd["deviceName"]
        normalized.append(nd)
    result = dict(design_data)
    result["devices"] = normalized
    return result


@router.post("/generate")
def generate_bom(body: dict):
    """
    [FR-7] BOM 生成主入口。

    输入: {"taskId": "str", "designTaskId": "str", "projectId": "str"}
    输出: {
        "status": "ok",
        "taskId": "...",
        "bom": { "mainDeviceQty": 15, "auxiliaryQty": 46, "cableQty": 42, "items": [...] },
        "processRequirements": [...],
        "fiberAllocation": { "allocations": [...], "summary": {...} },
        "excelFile": "path/to/file.xlsx"
    }
    """
    task_id = body.get("taskId", "")
    design_task_id = body.get("designTaskId", "")
    project_id = body.get("projectId", "")

    logger.info(f"BOM generate: taskId={task_id} designTaskId={design_task_id}")

    # ─── 1. 加载设计数据（mock 模式：读本地场景；real 模式：请求 S1 真实接口） ───
    try:
        design_data = load_design(design_task_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"S1 接口请求失败: {e}")

    # 归一化设备字段（兼容 D001/D002/D003 不同格式）
    design_data = _normalize_devices(design_data)

    # ─── 2. S4-E-03~05: 生成 BOM 物料清单 ───
    bom_items = bom_engine.generate_bom_items(design_data)

    main_qty = sum(i["qty"] for i in bom_items if i["category"] == "main_device")
    aux_qty = sum(i["qty"] for i in bom_items if i["category"] == "auxiliary")
    cable_qty = sum(i["qty"] for i in bom_items if i["category"] == "cable")

    # ─── 3. S4-E-08: 生成关键工序工艺 ───
    device_types = list(set(d.get("type", "") for d in design_data.get("devices", [])))
    proc_steps = process_requirements.generate_process_requirements(device_types)

    # ─── 4. S4-E-09: 生成纤芯分配表 ───
    fiber_alloc, fiber_summary = fiber_allocation.generate_fiber_allocation(
        design_data.get("devices", [])
    )

    # ─── 5. S4-E-06: 导出 Excel ───
    excel_path = excel_export.export_to_excel(
        task_id=task_id,
        bom_items=bom_items,
        process_steps=proc_steps,
        fiber_alloc=fiber_alloc,
        fiber_summary=fiber_summary,
    )

    return {
        "status": "ok",
        "taskId": task_id,
        "designTaskId": design_task_id,
        "projectId": project_id,
        "bom": {
            "mainDeviceQty": main_qty,
            "auxiliaryQty": aux_qty,
            "cableQty": cable_qty,
            "totalItems": len(bom_items),
            "items": bom_items,
        },
        "processRequirements": proc_steps,
        "fiberAllocation": {
            "allocations": fiber_alloc,
            "summary": fiber_summary,
        },
        "excelFile": excel_path,
    }


@router.get("/export")
def export_bom(taskId: str = Query(..., description="BOM 任务 ID")):
    """
    [FR-8] 下载已生成的 Excel 文件。
    """
    filepath = EXPORT_DIR / f"{taskId}.xlsx"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Excel not found: {filepath}")
    return FileResponse(
        path=str(filepath),
        filename=f"BOM_{taskId}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
