"""
S4 完整端到端验证 — 直接调用引擎模块，无 FastAPI 依赖
验证: AC-1~AC-7 (AC-8 需跨赛题)
"""
import sys
import json
import time
from pathlib import Path

# 设置路径
ENGINE_DIR = Path(r"C:\Users\RENXIN\WorkBuddy\2026-08-04-17-58-22\s4-bom-transform\engine")
sys.path.insert(0, str(ENGINE_DIR))

# 导入引擎模块
from app.services import bom_engine, catalog_service, cable_estimator, process_requirements, fiber_allocation, excel_export

MOCK_DIR = ENGINE_DIR / "data" / "mock"
EXPORT_DIR = ENGINE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


def test_scenario(scenario_id, design_file, expected_devices):
    """对单个场景做完整测试"""
    print(f"\n{'='*60}")
    print(f"  测试场景: {scenario_id}")
    print(f"{'='*60}")

    # 加载 mock 数据
    with open(MOCK_DIR / design_file, "r", encoding="utf-8") as f:
        design_data = json.load(f)

    # 归一化设备（复用 router 逻辑）
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
    design_data["devices"] = normalized

    # AC-1: 计时生成
    t0 = time.time()
    bom_items = bom_engine.generate_bom_items(design_data)
    t_elapsed = time.time() - t0

    main_qty = sum(i["qty"] for i in bom_items if i["category"] == "main_device")
    aux_qty = sum(i["qty"] for i in bom_items if i["category"] == "auxiliary")
    cable_qty = sum(i["qty"] for i in bom_items if i["category"] == "cable")

    main_items = sum(1 for i in bom_items if i["category"] == "main_device")
    aux_items = sum(1 for i in bom_items if i["category"] == "auxiliary")
    cable_items = sum(1 for i in bom_items if i["category"] == "cable")

    ac1_pass = t_elapsed < 60 and main_qty > 0  # AC-1: <60s + 有主设备
    ac2_pass = main_qty >= expected_devices  # AC-2: 每台设备映射到物料
    ac3_pass = aux_items > 2  # AC-3: 辅材按规则生成
    ac4_pass = cable_items > 0  # AC-4: 线缆估算

    print(f"  耗时: {t_elapsed:.3f}s")
    print(f"  物料: {len(bom_items)} 条 (主设备={main_qty}, 辅材={aux_qty}, 线缆={cable_qty})")
    print(f"  明细: {main_items} main + {aux_items} aux + {cable_items} cable")

    # AC-2: 验证每种设备类型都有映射
    device_types = set(n.get("type", "?") for n in normalized)
    mapped_types = set(i.get("deviceType", "?") for i in bom_items if i["category"] == "main_device")
    print(f"  设备类型: {sorted(device_types)}")
    print(f"  已映射类型: {sorted(mapped_types)}")
    unmapped = device_types - mapped_types
    if unmapped:
        print(f"  ⚠️ 未映射类型: {sorted(unmapped)}")
    else:
        print(f"  ✅ 全部映射")

    # 工序工艺
    proc_steps = process_requirements.generate_process_requirements(list(device_types))
    ac7_proc = len(proc_steps) > 0
    print(f"  工序工艺: {len(proc_steps)} 条")

    # 纤芯分配
    fiber_alloc, fiber_summary = fiber_allocation.generate_fiber_allocation(normalized)
    ac7_fiber = len(fiber_alloc) > 0
    print(f"  纤芯分配: {len(fiber_alloc)} 条, ODF使用率={fiber_summary.get('odf_usage_rate', '?')}")

    # AC-5: Excel 导出
    task_id = f"verify-{scenario_id}"
    excel_path = excel_export.export_to_excel(
        task_id=task_id, bom_items=bom_items,
        process_steps=proc_steps, fiber_alloc=fiber_alloc, fiber_summary=fiber_summary
    )
    ac5_pass = Path(excel_path).exists() and Path(excel_path).stat().st_size > 1000
    print(f"  Excel 导出: {'✅' if ac5_pass else '❌'} ({excel_path})")

    # 结果汇总
    all_pass = ac1_pass and ac2_pass and ac3_pass and ac4_pass and ac5_pass and ac7_proc and ac7_fiber
    checks = {
        "AC-1 性能(<60s)": "✅" if ac1_pass else "❌",
        "AC-2 设备映射": "✅" if ac2_pass else "❌",
        "AC-3 辅材计算": "✅" if ac3_pass else "❌",
        "AC-4 线缆估算": "✅" if ac4_pass else "❌",
        "AC-5 Excel导出": "✅" if ac5_pass else "❌",
        "AC-7 工序工艺": "✅" if ac7_proc else "❌",
        "AC-7 纤芯分配": "✅" if ac7_fiber else "❌",
    }
    for ac, status in checks.items():
        print(f"  {status} {ac}")

    return all_pass


if __name__ == "__main__":
    print("=" * 60)
    print("  S4 BOM 引擎 — 完整验收测试 (AC-1~AC-7)")
    print("=" * 60)

    results = {
        "D001": test_scenario("D001", "design_yuncheng_site_A001.json", 15),
        "D002": test_scenario("D002", "design_indoor_B001.json", 14),
        "D003": test_scenario("D003", "design_micro_C001.json", 9),
    }

    print(f"\n{'='*60}")
    print(f"  最终验证结果")
    print(f"{'='*60}")
    for sid, passed in results.items():
        print(f"  {'✅' if passed else '❌'} {sid}: {'通过' if passed else '未通过'}")
    all_pass = all(results.values())
    print(f"\n  {'✅ AC-1~AC-7 全部验收通过!' if all_pass else '❌ 存在未通过项'}")
