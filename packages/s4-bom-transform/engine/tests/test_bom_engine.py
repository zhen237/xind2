"""
S4 BOM 引擎单元测试 — 验证 BOM 生成准确性（设备-物料映射 / 辅材 / 线缆 / 审查闸门）。

运行: cd engine && venv/Scripts/python -m pytest tests/ -v
"""
import json
import math
from pathlib import Path

import pytest

from app.services import bom_engine, review_gate
from app.services.catalog_service import get_mapping, get_site_auxiliaries, load_catalog
from app.services.cable_estimator import (
    FIBER_SLACK_FACTOR,
    FIXED_RF_JUMPER_M,
    RISER_HEIGHT_M,
    estimate_cable_length,
    haversine_m,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "mock"


# ────────────────────────────────────────
#  fixtures — 三套样例设计数据（运城宏站 / 室分 / 微站）
# ────────────────────────────────────────

def load_design(scenario: str) -> dict:
    filename = {
        "D001": "design_yuncheng_site_A001.json",
        "D002": "design_indoor_B001.json",
        "D003": "design_micro_C001.json",
    }[scenario]
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def design_d001() -> dict:
    return load_design("D001")


@pytest.fixture(scope="module")
def bom_d001(design_d001) -> list[dict]:
    return bom_engine.generate_bom_items(design_d001)


# ────────────────────────────────────────
#  S4-E-02: 物料编码库（设备 → 物料映射规则）
# ────────────────────────────────────────

class TestCatalogMapping:
    def test_exact_model_mapping(self):
        m = get_mapping("antenna", "HW-AAU5636w")
        assert m is not None
        assert m["mainDevice"]["materialCode"] == "M-ANT-001"

    def test_same_type_second_model(self):
        """同类型不同型号（GPS 天线）应精确匹配到第二条映射，而非回退。"""
        m = get_mapping("antenna", "GPS-BD-A01")
        assert m["mainDevice"]["materialCode"] == "M-ANT-002"

    def test_unknown_model_falls_back_to_type(self):
        """未知型号回退到同类型第一条映射（保证不漏主设备）。"""
        m = get_mapping("rru", "UNKNOWN-MODEL-X")
        assert m is not None
        assert m["deviceType"] == "rru"
        assert m["mainDevice"]["materialCode"] == "M-RRU-001"

    def test_unknown_type_returns_none(self):
        assert get_mapping("nonexistent_type", "whatever") is None

    def test_site_auxiliaries_loaded(self):
        aux = get_site_auxiliaries()
        codes = {a["materialCode"] for a in aux}
        assert {"M-ACC-020", "M-ACC-021", "M-ACC-022", "M-ACC-023"} <= codes

    def test_every_mapping_has_required_fields(self):
        catalog = load_catalog()
        for m in catalog["mappings"]:
            md = m["mainDevice"]
            assert md["materialCode"].startswith("M-"), m
            assert md["qtyPerUnit"] >= 1
            for aux in m.get("auxiliaries", []):
                assert aux["qtyPerDevice"] >= 1
            for cbl in m.get("cables", []):
                assert cbl["calcMethod"], f"cable 缺 calcMethod: {cbl['materialCode']}"


# ────────────────────────────────────────
#  S4-E-05: 线缆长度估算公式
# ────────────────────────────────────────

class TestCableEstimator:
    def test_haversine_zero_distance(self):
        assert haversine_m(35.0, 111.0, 380.0, 35.0, 111.0, 380.0) == 0.0

    def test_haversine_one_degree_lat(self):
        """纬度 1° ≈ 111.195 km（地球半径 6371km 基线）。"""
        d = haversine_m(0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        assert abs(d - 111_194.93) < 1.0

    def test_fixed_3m_jumper(self):
        est = estimate_cable_length({"lat": 1, "lng": 1, "alt": 1}, {"lat": 2, "lng": 2, "alt": 2}, "fixed_3m")
        assert est["single_length_m"] == FIXED_RF_JUMPER_M == 3.0

    def test_fixed_15m_indoor_feeder(self):
        est = estimate_cable_length({}, {}, "fixed_15m")
        assert est["single_length_m"] == 15.0

    def test_fiber_horizontal_x1_2_ignores_vertical(self):
        """光纤 = 水平距 × 1.2，垂直高差不应参与（走弱电井另计）。"""
        dev = {"lat": 35.02571, "lng": 111.00651, "alt": 385.0}
        bbu = {"lat": 35.02571, "lng": 111.00652, "alt": 360.0}
        est = estimate_cable_length(dev, bbu, "horizontal_distance_x1.2")
        expected = haversine_m(dev["lat"], dev["lng"], 0, bbu["lat"], bbu["lng"], 0) * FIBER_SLACK_FACTOR
        assert est["single_length_m"] == round(expected, 2)
        # 纯竖直偏移不改变水平距 → 长度不变
        dev2 = dict(dev, alt=999.0)
        est2 = estimate_cable_length(dev2, bbu, "horizontal_distance_x1.2")
        assert est2["single_length_m"] == est["single_length_m"]

    def test_distance_plus_riser(self):
        dev = {"lat": 35.02571, "lng": 111.00651, "alt": 385.0}
        bbu = {"lat": 35.02571, "lng": 111.00652, "alt": 360.0}
        est = estimate_cable_length(dev, bbu, "distance_plus_riser")
        d = haversine_m(dev["lat"], dev["lng"], dev["alt"], bbu["lat"], bbu["lng"], bbu["alt"])
        assert est["single_length_m"] == round(d + RISER_HEIGHT_M, 2)

    def test_tower_to_ground(self):
        est = estimate_cable_length({"lat": 1, "lng": 1, "alt": 385.0},
                                    {"lat": 1, "lng": 1, "alt": 360.0}, "tower_to_ground")
        assert est["single_length_m"] == 27.0  # 25m 高差 + 2m 地面预留

    def test_rack_ground_fixed_2m(self):
        est = estimate_cable_length({}, {}, "rack_ground")
        assert est["single_length_m"] == 2.0


# ────────────────────────────────────────
#  S4-E-03/04/05: BOM 生成（D001 运城宏站样例）
# ────────────────────────────────────────

class TestBomGenerationD001:
    def test_every_device_mapped_to_main_item(self, bom_d001, design_d001):
        """AC-2: 每台设备都必须映射到 main_device 物料，不允许静默丢失。"""
        n_devices = len(design_d001["devices"])
        main_items = [i for i in bom_d001 if i["category"] == "main_device"]
        assert len(main_items) == n_devices

    def test_main_item_material_code_format(self, bom_d001):
        for item in bom_d001:
            if item["category"] == "main_device":
                assert item["materialCode"].startswith("M-")
                assert item["qty"] >= 1

    def test_rack_qty_multiplied(self, bom_d001):
        """机柜 qty=2 → 主设备物料数量 = 2 × qtyPerUnit。"""
        rack = next(i for i in bom_d001
                    if i["category"] == "main_device" and i["materialCode"] == "M-RACK-001")
        assert rack["qty"] == 2

    def test_auxiliary_qty_per_device(self, bom_d001):
        """AC-3: 辅材数量 = 设备数 × qtyPerDevice（每台 RRU 2 张标签 × 3 台 = 每条 2，共 3 条）。"""
        rru_labels = [i for i in bom_d001
                      if i["materialCode"] == "M-ACC-004" and i["deviceType"] == "rru"]
        assert len(rru_labels) == 3
        assert all(i["qty"] == 2 for i in rru_labels)  # 3 台 RRU × 2 张/台

    def test_rf_jumper_fixed_3m(self, bom_d001):
        """AC-4: 射频跳线 3m/根。"""
        jumpers = [i for i in bom_d001 if i["materialCode"] == "M-CBL-004"]
        assert len(jumpers) == 3  # 3 台 RRU
        for j in jumpers:
            assert j["singleLength"] == 3.0
            assert j["totalLength"] == 3.0

    def test_fiber_length_formula(self, bom_d001, design_d001):
        """AC-4: 光纤长度 = 水平距 × 1.2，单根/总长均输出。"""
        fibers = [i for i in bom_d001 if i["materialCode"] == "M-CBL-001"]
        assert len(fibers) == 3  # 3 台 AAU
        dev = next(d for d in design_d001["devices"] if d["deviceId"] == "DEV-ANT-001")
        bbu = next(d for d in design_d001["devices"] if d["type"] == "bbu")
        expected = round(
            haversine_m(dev["coordinates"]["lat"], dev["coordinates"]["lng"], 0,
                        bbu["coordinates"]["lat"], bbu["coordinates"]["lng"], 0) * 1.2, 2)
        assert fibers[0]["singleLength"] == pytest.approx(expected, abs=0.01)
        assert fibers[0]["qty"] == 2  # qtyPerDevice=2（主备双芯）
        assert fibers[0]["totalLength"] == pytest.approx(expected * 2, abs=0.01)

    def test_cable_total_length_equals_single_times_qty(self, bom_d001):
        for i in bom_d001:
            if i["category"] == "cable":
                assert i["totalLength"] == pytest.approx(i["singleLength"] * i["qty"], abs=0.01), i

    def test_site_level_auxiliaries_present(self, bom_d001):
        """FR-3: 站点级辅材（接地网/走线架/防火封堵/室外扎带）。"""
        codes = {i["materialCode"] for i in bom_d001 if i["deviceType"] == "site"}
        assert {"M-ACC-020", "M-ACC-021", "M-ACC-022", "M-ACC-023"} <= codes

    def test_label_packs_dynamic_rule(self, bom_d001, design_d001):
        """FR-3: 包标识标签 = max(1, int(天线数/2))。D001 天线 3 AAU + 1 GPS = 4 → 2 包。"""
        antenna_count = sum(d.get("qty", 1) for d in design_d001["devices"]
                            if d.get("type") == "antenna")
        assert antenna_count == 4
        labels = next(i for i in bom_d001 if i["materialCode"] == "M-ACC-028")
        assert labels["qty"] == max(1, antenna_count // 2) == 2

    def test_category_ordering(self, bom_d001):
        order = [i["category"] for i in bom_d001]
        assert order == sorted(order, key=lambda c: {"main_device": 0, "auxiliary": 1, "cable": 2}[c])

    def test_stats_consistency(self, bom_d001):
        """三类数量统计口径一致（供 s4_bom_task 落库字段核对）。"""
        assert all(i["category"] in ("main_device", "auxiliary", "cable") for i in bom_d001)
        main_qty = sum(i["qty"] for i in bom_d001 if i["category"] == "main_device")
        assert main_qty >= len([i for i in bom_d001 if i["category"] == "main_device"])


# ────────────────────────────────────────
#  设备归一化（兼容 D002/D003 字段格式）
# ────────────────────────────────────────

class TestDeviceNormalization:
    def test_normalize_deviceType_fields(self):
        dev = {"deviceType": "indoor_ru", "deviceModel": "IRU-5G-4T4R-500mW",
               "deviceName": "pRU-1", "qty": 1, "longitude": 111.0, "latitude": 35.0}
        nd = bom_engine._normalize_device(dev)
        assert nd["type"] == "indoor_ru"
        assert nd["model"] == "IRU-5G-4T4R-500mW"
        assert nd["name"] == "pRU-1"
        coords = bom_engine._coords(nd)
        assert coords["lat"] == 35.0 and coords["lng"] == 111.0

    def test_d002_and_d003_generate_bom(self):
        """室分/微站样例数据同样能完整生成 BOM（AC-8 数据兼容性）。"""
        for scenario in ("D002", "D003"):
            items = bom_engine.generate_bom_items(load_design(scenario))
            mains = [i for i in items if i["category"] == "main_device"]
            assert len(mains) >= 5, f"{scenario} 主设备映射异常"
            assert all(i["materialCode"].startswith("M-") for i in mains)

    def test_d002_review_flag_propagates(self):
        """S3 警告设备 → BOM 明细 requiresRectification 传导打标（FR-10）。"""
        with open(DATA_DIR / "s3_review_results.json", "r", encoding="utf-8") as f:
            violations = json.load(f)["D002"]
        design = load_design("D002")
        gate = review_gate.check_gate({"result": "approved_with_warnings", "violations": violations})
        assert gate["decision"] == review_gate.ALLOWED_WITH_WARNINGS
        flagged = review_gate.flag_devices(design, gate)
        items = bom_engine.generate_bom_items(flagged)
        flagged_items = [i for i in items if i.get("requiresRectification")]
        assert flagged_items, "警告设备的 BOM 明细应带 requiresRectification 标记"


# ────────────────────────────────────────
#  FR-10: 四档分级审查闸门
# ────────────────────────────────────────

class TestReviewGate:
    def _review(self, *severities):
        return {"result": "x", "violations": [
            {"ruleId": f"R-{s}", "ruleName": f"规则{s}", "severity": s,
             "standard": "GB xxx", "deviceIds": [], "suggestion": ""} for s in severities]}

    def test_none_degrades_to_allowed(self):
        gate = review_gate.check_gate(None)
        assert gate["decision"] == review_gate.ALLOWED
        assert gate["degraded"] is True

    def test_critical_blocks(self):
        gate = review_gate.check_gate(self._review("warning", "critical"))
        assert gate["decision"] == review_gate.BLOCKED
        assert gate["counts"]["critical"] == 1
        assert gate["blockers"][0]["ruleId"] == "R-critical"

    def test_error_blocks(self):
        assert review_gate.check_gate(self._review("error"))["decision"] == review_gate.BLOCKED

    def test_warning_only_allows_with_warnings(self):
        gate = review_gate.check_gate(self._review("warning", "pending"))
        assert gate["decision"] == review_gate.ALLOWED_WITH_WARNINGS
        assert gate["counts"] == {"critical": 0, "error": 0, "warning": 1, "pending": 1}

    def test_clean_review_allowed(self):
        gate = review_gate.check_gate({"result": "approved", "violations": []})
        assert gate["decision"] == review_gate.ALLOWED
        assert gate["degraded"] is False
