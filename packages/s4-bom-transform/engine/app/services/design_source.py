"""
设计数据源加载器 — 支持 mock / real 双模式。

mock: 按 designTaskId 从 data/mock/*.json 读取模拟设计清单（默认）
real: 请求 S1 真实接口 GET {s1_base_url}/api/s1/design/tasks/{designTaskId}

联调日切换方式（二选一）：
  1. 环境变量:  S4_DATA_SOURCE=real S4_S1_BASE_URL=http://<S1服务地址> python main.py
  2. 配置文件:  engine/.env 中写 S4_DATA_SOURCE=real 与 S4_S1_BASE_URL=...
"""
import json
import logging
from pathlib import Path

import requests

from app.config import settings

logger = logging.getLogger("s4-engine.design-source")

MOCK_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "mock"

# 场景 → mock 文件映射（仅 mock 模式使用）
SCENARIO_MAP = {
    "D001": "design_yuncheng_site_A001.json",   # 宏站
    "D002": "design_indoor_B001.json",           # 室分
    "D003": "design_micro_C001.json",            # 微站
}


def load_design(design_task_id: str) -> dict:
    """统一入口：按当前 data_source 配置加载设计数据。"""
    if settings.data_source == "real":
        return _load_from_s1(design_task_id)
    return _load_from_mock(design_task_id)


def _load_from_mock(design_task_id: str) -> dict:
    filename = SCENARIO_MAP.get(design_task_id, "design_yuncheng_site_A001.json")
    path = MOCK_DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Design data not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_from_s1(design_task_id: str) -> dict:
    base = settings.s1_base_url.rstrip("/")
    if not base:
        raise RuntimeError(
            "data_source=real 但未配置 S4_S1_BASE_URL。请在 engine/.env 或环境变量中设置，"
            "例如 S4_S1_BASE_URL=http://localhost:8081"
        )
    url = f"{base}/api/s1/design/tasks/{design_task_id}"
    logger.info("[real] fetching design from S1: %s", url)
    resp = requests.get(url, timeout=settings.s1_timeout)
    resp.raise_for_status()
    payload = resp.json()

    # 兼容两种返回结构：
    #   {"status":"ok","designTaskId":"...","data":{...}}   ← S1 契约
    #   {...design 本身...}                                  ← 直接返回
    data = payload.get("data") if isinstance(payload, dict) else None
    if data is None:
        data = payload
    if not isinstance(data, dict):
        raise RuntimeError(f"S1 返回格式异常: {str(payload)[:200]}")
    logger.info("[real] design loaded from S1: designTaskId=%s devices=%d",
                design_task_id, len(data.get("devices", [])))
    return data
