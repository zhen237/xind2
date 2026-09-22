"""
关键工序工艺要求生成 — 从 JSON 模板库导入底层工艺/验收标准参数，
根据设备类型输出施工步骤与工艺规范。
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("s4-engine.process")


def _load_templates() -> tuple[dict, list]:
    """加载外部工序模板库（底层参数导入入口）。"""
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    template_path = data_dir / "process_templates.json"

    if not template_path.exists():
        logger.error(f"Process template file not found: {template_path}")
        return {}, []

    try:
        with template_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in process_templates.json: {e}")
        return {}, []

    templates = payload.get("templates", {})
    global_processes = payload.get("globalProcesses", [])
    logger.info(f"Loaded process templates: {len(templates)} device types, {len(global_processes)} global steps")
    return templates, global_processes


PROCESS_TEMPLATES, GLOBAL_PROCESSES = _load_templates()


def generate_process_requirements(device_types: list[str]) -> list[dict]:
    """
    根据设备类型列表生成关键工序工艺要求。
    去重：同类型设备只生成一次工序。
    """
    seen = set()
    result = []

    for dtype in device_types:
        if dtype in seen:
            continue
        seen.add(dtype)
        template = PROCESS_TEMPLATES.get(dtype)
        if template:
            # 深拷贝，避免污染全局模板
            for step in template["steps"]:
                step_copy = dict(step)
                step_copy["适用设备类型"] = dtype
                result.append(step_copy)
        else:
            logger.warning(f"No process template for deviceType={dtype}")

    # 追加站点级通用工序（同样深拷贝）
    for step in GLOBAL_PROCESSES:
        result.append(dict(step))

    # 重排序号
    for i, step in enumerate(result, 1):
        step["序号"] = i

    logger.info(f"Generated {len(result)} process steps for {len(seen)} device types")
    return result
