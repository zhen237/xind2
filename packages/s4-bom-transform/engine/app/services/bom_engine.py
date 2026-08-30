"""
BOM 引擎核心 — 设备-物料映射 + 辅材计算 + 线缆估算。
串联 S4-E-03、S4-E-04、S4-E-05。
"""
import logging
from typing import Optional

from app.services.catalog_service import get_mapping, get_site_auxiliaries
from app.services.cable_estimator import estimate_cable_length

logger = logging.getLogger("s4-engine.bom")


def _coords(d: dict) -> dict:
    c = d.get("coordinates", {})
    if c:
        return {"lat": c.get("lat", 0), "lng": c.get("lng", 0), "alt": c.get("alt", 0)}
    # 兼容室分/微站 mock 数据：直接使用 longitude/latitude/altitude 字段
    return {
        "lat": d.get("latitude", d.get("lat", 0)),
        "lng": d.get("longitude", d.get("lng", 0)),
        "alt": d.get("altitude", d.get("alt", 0)),
    }


def _normalize_device(dev: dict) -> dict:
    """归一化设备字段，兼容不同 mock 数据格式。

    D001 (宏站): type, model, name, coordinates
    D002/D003 (室分/微站): deviceType, deviceModel, deviceName, longitude/latitude/altitude
    """
    normalized = dict(dev)  # shallow copy
    if "deviceType" in dev and "type" not in dev:
        normalized["type"] = dev["deviceType"]
    if "deviceModel" in dev and "model" not in dev:
        normalized["model"] = dev["deviceModel"]
    if "deviceName" in dev and "name" not in dev:
        normalized["name"] = dev["deviceName"]
    return normalized


def _find_target_coords(devices: list[dict], target_type: str) -> dict:
    """找设备间/BBU/机柜坐标（优先匹配 type）。"""
    # 找 type=power 且 model 不含 "BS-"
    power = next((d for d in devices if d.get("type") == "power" and "BS-" not in d.get("model", "")), None)
    bbu = next((d for d in devices if d.get("type") == "bbu"), None)
    rack = next((d for d in devices if d.get("type") == "rack"), None)
    odb = next((d for d in devices if d.get("type") == "power" and "ODB" in d.get("model", "")), None)

    targets = {"power": power, "bbu": bbu, "rack": rack, "odb": odb}
    target = targets.get(target_type)
    return _coords(target) if target else {"lat": 35.02571, "lng": 111.00652, "alt": 360.0}


def generate_bom_items(design_data: dict) -> list[dict]:
    """
    从设计设备清单生成完整 BOM 明细（主设备 + 辅材 + 线缆）。

    Args:
        design_data: 来自 design_yuncheng_site_A001.json 的完整设计数据
    Returns:
        BOM 明细列表，每项可映射到 s4_bom_item 字段
    """
    devices = design_data.get("devices", [])
    site = design_data.get("site", {})

    items = []

    # ───────── S4-E-03: 设备-物料映射 ─────────
    for raw_dev in devices:
        dev = _normalize_device(raw_dev)
        dtype = dev.get("type", "")
        model = dev.get("model", "")
        qty = dev.get("qty", 1)
        name = dev.get("name", "")

        mapping = get_mapping(dtype, model)
        if not mapping:
            logger.warning(f"No mapping for deviceType={dtype} model={model}, skipping")
            continue

        # 主设备（S3 违规设备传导 requiresRectification 标记，供前端/Excel 提示整改）
        md = mapping["mainDevice"]
        items.append({
            "materialCode": md["materialCode"],
            "materialName": md["materialName"],
            "spec": md["spec"],
            "unit": md["unit"],
            "qty": qty * md.get("qtyPerUnit", 1),
            "category": "main_device",
            "deviceName": name,
            "deviceType": dtype,
            "requiresRectification": bool(dev.get("requiresRectification", False)),
        })

        # ───────── S4-E-04: 辅材自动计算 ─────────
        for aux in mapping.get("auxiliaries", []):
            items.append({
                "materialCode": aux["materialCode"],
                "materialName": aux["materialName"],
                "spec": aux.get("spec", ""),
                "unit": aux["unit"],
                "qty": qty * aux["qtyPerDevice"],
                "category": "auxiliary",
                "deviceName": name,
                "deviceType": dtype,
                "requiresRectification": bool(dev.get("requiresRectification", False)),
            })

        # ───────── S4-E-05: 线缆长度估算 ─────────
        device_coords = _coords(dev)
        for cable in mapping.get("cables", []):
            calc_method = cable["calcMethod"]

            # 选择合适的参考坐标
            if "rack_to_power" in calc_method or "rack_ground" in calc_method:
                target_coords = _find_target_coords(devices, "rack")
            elif "battery_to_power" in calc_method or "dist_to_power_panel" in calc_method:
                target_coords = _find_target_coords(devices, "odb")
            else:
                # 默认：天线/RRU 到 BBU/设备间
                target_coords = _find_target_coords(devices, "bbu")

            est = estimate_cable_length(device_coords, target_coords, calc_method)
            if est is None:
                continue

            single_m = est["single_length_m"]
            # 线缆根数 = 设备数量 × 每台根数（qtyPerDevice）
            item_qty = qty * cable.get("qtyPerDevice", 1)
            # 总长度 = 单根长度 × 根数（与 BOM 数量口径一致）
            total_m = round(single_m * item_qty, 2)

            items.append({
                "materialCode": cable["materialCode"],
                "materialName": cable["materialName"],
                "spec": cable.get("spec", ""),
                "unit": cable["unit"],
                "qty": item_qty,
                "singleLength": single_m,
                "totalLength": total_m,
                "category": "cable",
                "deviceName": name,
                "deviceType": dtype,
            })

    # ───────── S4-E-04 站点级辅材 (FR-3) ─────────
    site_aux = get_site_auxiliaries()
    for sa in site_aux:
        items.append({
            "materialCode": sa["materialCode"],
            "materialName": sa["materialName"],
            "spec": sa.get("spec", ""),
            "unit": sa["unit"],
            "qty": sa.get("qtyPerSite", 1),
            "category": "auxiliary",
            "deviceName": "站点级",
            "deviceType": "site",
        })

    # FR-3: max(1, int(天线数/2)) 包标识标签（站点级动态计算）
    antenna_count = sum(
        raw_dev.get("qty", 1)
        for raw_dev in devices
        if _normalize_device(raw_dev).get("type") == "antenna"
    )
    label_packs = max(1, int(antenna_count / 2))
    items.append({
        "materialCode": "M-ACC-028",
        "materialName": "标识标签包（站点级）",
        "spec": f"含{label_packs}包, 每包50张室外耐候标签, 天线数={antenna_count}",
        "unit": "包",
        "qty": label_packs,
        "category": "auxiliary",
        "deviceName": "站点级(动态)",
        "deviceType": "site",
    })
    logger.info(f"FR-3 site labels: antenna_count={antenna_count} → {label_packs} 包")

    # 按 category 分组排序
    items.sort(key=lambda x: {"main_device": 0, "auxiliary": 1, "cable": 2}[x["category"]])

    # 汇总日志
    main_count = sum(1 for i in items if i["category"] == "main_device")
    aux_count = sum(1 for i in items if i["category"] == "auxiliary")
    cable_count = sum(1 for i in items if i["category"] == "cable")
    logger.info(f"BOM generated: {len(items)} items total ({main_count} main, {aux_count} aux, {cable_count} cable)")

    return items
