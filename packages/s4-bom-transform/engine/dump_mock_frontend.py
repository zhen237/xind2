"""
前端虚拟数据生成器（仿 S1 虚拟数据做法）— 用真实引擎管线跑出 BOM 快照，
落到前端 mock 目录，使 5190 前端不依赖后端（8090/8100）即可演示。

产物:
    frontend/src/mock/data/design_{Dxxx}.json    # 样例设计数据（S1 视角）
    frontend/src/mock/data/bom_{Dxxx}.json       # BOM 全量结果（物料+工序+纤芯+闸门）
    frontend/src/mock/data/index.js              # 数据入口（聚合导出）
    frontend/public/mock/BOM_demo.xlsx            # 演示用真实 Excel（导出按钮下载）

用法: cd engine && venv/Scripts/python dump_mock_frontend.py
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR))

from app.services import bom_engine, process_requirements, fiber_allocation, excel_export, review_gate  # noqa: E402

MOCK_DIR = ENGINE_DIR / "data" / "mock"
FRONTEND = ENGINE_DIR.parent / "frontend"
DATA_OUT = FRONTEND / "src" / "mock" / "data"
PUBLIC_OUT = FRONTEND / "public" / "mock"

SCENARIOS = {
    "D001": {"file": "design_yuncheng_site_A001.json", "name": "运城南风广场 5G 宏站",
             "projectId": "PRJ-yuncheng", "siteType": "macro"},
    "D002": {"file": "design_indoor_B001.json", "name": "万象城商业综合体室分覆盖",
             "projectId": "PRJ-indoor-mall", "siteType": "indoor"},
    "D003": {"file": "design_micro_C001.json", "name": "解放路步行街微站群",
             "projectId": "PRJ-micro-urban", "siteType": "micro"},
}


def normalize_devices(design: dict) -> dict:
    devices = []
    for dev in design.get("devices", []):
        nd = dict(dev)
        if "deviceType" in nd and "type" not in nd:
            nd["type"] = nd["deviceType"]
        if "deviceModel" in nd and "model" not in nd:
            nd["model"] = nd["deviceModel"]
        if "deviceName" in nd and "name" not in nd:
            nd["name"] = nd["deviceName"]
        devices.append(nd)
    design["devices"] = devices
    return design


def load_s3_violations() -> dict:
    path = MOCK_DIR / "s3_review_results.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def run_pipeline(scenario: str, cfg: dict) -> tuple[dict, dict]:
    """复用 verify_bom.py 同一套管线（不走 HTTP，直接调引擎服务）。"""
    with open(MOCK_DIR / cfg["file"], "r", encoding="utf-8") as f:
        design = normalize_devices(json.load(f))

    violations = load_s3_violations().get(scenario, [])
    review = {"result": "approved_with_warnings" if violations else "approved",
              "violations": violations,
              "reviewTaskId": f"R-{scenario}", "designTaskId": scenario,
              "projectName": cfg["name"],
              "violationCount": len(violations),
              "reviewedAt": "2026-07-22 11:00:00"}
    gate = review_gate.check_gate(review)
    if gate["decision"] == review_gate.ALLOWED_WITH_WARNINGS:
        design = review_gate.flag_devices(design, gate)
    rect_steps = review_gate.build_rectification_steps(gate)

    items = bom_engine.generate_bom_items(design)
    device_types = list({d.get("type", "") for d in design["devices"]})
    proc = process_requirements.generate_process_requirements(device_types) + rect_steps
    fiber_alloc, fiber_summary = fiber_allocation.generate_fiber_allocation(design["devices"])

    task_id = f"demo-{scenario}"
    excel_path = excel_export.export_to_excel(
        task_id=task_id, bom_items=items, process_steps=proc,
        fiber_alloc=fiber_alloc, fiber_summary=fiber_summary)

    main_qty = sum(i["qty"] for i in items if i["category"] == "main_device")
    aux_qty = sum(i["qty"] for i in items if i["category"] == "auxiliary")
    cable_qty = sum(i["qty"] for i in items if i["category"] == "cable")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 与 dev-proxy _build_detail + /full 响应结构保持一致
    full = {
        "taskId": task_id,
        "designTaskId": scenario,
        "projectId": cfg["projectId"],
        "projectName": cfg["name"],
        "status": "done",
        "totalCategories": len({i["materialCode"] for i in items}),
        "totalQty": len(items),
        "mainDeviceQty": main_qty,
        "auxiliaryQty": aux_qty,
        "cableQty": cable_qty,
        "items": items,
        "createdAt": now,
        "finishedAt": now,
        "processRequirements": proc,
        "fiberAllocation": {"allocations": fiber_alloc, "summary": fiber_summary},
        "reviewGate": {
            "decision": gate["decision"],
            "result": gate["result"],
            "counts": gate["counts"],
            "degraded": gate["degraded"],
            "violations": gate["violations"],
            "rectificationSteps": rect_steps,
        },
    }
    return full, {"excel": excel_path, "design": design, "review": review}


def main():
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.mkdir(parents=True, exist_ok=True)

    design_list = []
    for scenario, cfg in SCENARIOS.items():
        full, extra = run_pipeline(scenario, cfg)

        with open(DATA_OUT / f"design_{scenario}.json", "w", encoding="utf-8") as f:
            json.dump(extra["design"], f, ensure_ascii=False, indent=2)
        with open(DATA_OUT / f"bom_{scenario}.json", "w", encoding="utf-8") as f:
            json.dump(full, f, ensure_ascii=False, indent=2)

        design_list.append({
            "designTaskId": scenario,
            "projectId": cfg["projectId"],
            "projectName": cfg["name"],
            "siteType": cfg["siteType"],
            "status": "approved",
            "deviceCount": len(extra["design"]["devices"]),
            "createdAt": "2026-07-15 10:30:00",
            "reviewedAt": "2026-07-20 14:00:00",
        })
        print(f"[dump] {scenario} {cfg['name']}: {len(full['items'])} 条物料, "
              f"Excel → {Path(extra['excel']).name}")

    # S1 设计任务列表（与 dev-proxy design_tasks 同构）
    with open(DATA_OUT / "design_tasks.json", "w", encoding="utf-8") as f:
        json.dump(design_list, f, ensure_ascii=False, indent=2)

    # 演示 Excel → 前端静态目录（导出按钮下载）
    demo_src = ENGINE_DIR / "exports" / "demo-D001.xlsx"
    shutil.copyfile(demo_src, PUBLIC_OUT / "BOM_demo.xlsx")
    print(f"[dump] demo Excel → {PUBLIC_OUT / 'BOM_demo.xlsx'}")

    print("\n全部虚拟数据已生成，前端执行 npm run dev 即可免后端演示。")
    print("（如需重新生成: venv/Scripts/python dump_mock_frontend.py）")


if __name__ == "__main__":
    main()
