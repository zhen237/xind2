"""物料编码库查询服务 — 加载 material_catalog.json。"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("s4-engine.catalog")

_CATALOG: Optional[dict] = None
_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "material_catalog.json"


def load_catalog() -> dict:
    global _CATALOG
    if _CATALOG is None:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            _CATALOG = json.load(f)
        logger.info(f"Material catalog loaded: {len(_CATALOG['mappings'])} mappings")
    return _CATALOG


def get_mapping(device_type: str, device_model: str) -> Optional[dict]:
    """
    根据 deviceType + deviceModel 查物料映射。
    优先精确 model 匹配，回退到仅 type 匹配。
    """
    catalog = load_catalog()
    # 精确匹配
    for m in catalog["mappings"]:
        if m["deviceType"] == device_type and m["deviceModel"] == device_model:
            return m
    # 回退：同类型第一条
    for m in catalog["mappings"]:
        if m["deviceType"] == device_type:
            logger.warning(f"No exact mapping for {device_model}, fallback to {m['deviceModel']}")
            return m
    return None


def get_site_auxiliaries() -> list[dict]:
    catalog = load_catalog()
    return catalog.get("siteLevelAuxiliaries", {}).get("items", [])
