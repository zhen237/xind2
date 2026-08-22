"""
S4 Dev Proxy — 模拟完整流水线后端 (端口 8090)

模拟范围:
  S1 设计    → /api/s1/design/tasks, /api/s1/design/tasks/{id}
  S3 审查    → /api/s3/review/tasks, /api/s3/review/result/{designTaskId}
  S4 BOM     → /api/s4/bom/*  (转发到 Python 引擎 8100)
  S5 监管    → /api/s5/verify/* (占位)
  系统      → /health (三服务状态汇总)

用法: python main.py
"""

import os
import uuid
import time
import json
import threading
from datetime import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="XA-202610 Dev Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ENGINE_URL = "http://localhost:8100"
EXPORT_DIR = str(Path(__file__).resolve().parent.parent / "engine" / "exports")
MOCK_DIR = str(Path(__file__).resolve().parent.parent / "engine" / "data" / "mock")

# ── 数据源切换（联调配置）────────────────────────────
# DATA_SOURCE: mock | real
#   mock: S1/S3 数据读本地 mock JSON（默认）
#   real: 转发到 S1 真实接口（S1_REAL_URL 必填）
DATA_SOURCE = os.getenv("S4_DATA_SOURCE", "mock")
S1_REAL_URL = os.getenv("S1_REAL_URL", "").rstrip("/")

# ════════════════════════════════════════════
#  内存存储
# ════════════════════════════════════════════

tasks_store: dict[str, dict] = {}
review_results: dict[str, dict] = {}   # designTaskId → review result

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _load_design(design_task_id: str) -> dict:
    """加载设计清单 — 按 DATA_SOURCE 切换。

    mock: 读本地 data/mock/*.json
    real: 转发 S1 真实接口 GET {S1_REAL_URL}/api/s1/design/tasks/{id}
          失败时降级 mock 并打印警告（联调期保证服务可用）
    """
    if DATA_SOURCE == "real":
        if not S1_REAL_URL:
            print("[proxy][WARN] DATA_SOURCE=real 但未配置 S1_REAL_URL，降级 mock")
        else:
            try:
                r = requests.get(f"{S1_REAL_URL}/api/s1/design/tasks/{design_task_id}", timeout=10)
                r.raise_for_status()
                payload = r.json()
                data = payload.get("data") if isinstance(payload, dict) else None
                if isinstance(data, dict):
                    print(f"[proxy][real] S1 design loaded: {design_task_id} devices={len(data.get('devices', []))}")
                    return data
                print("[proxy][WARN] S1 返回格式异常，降级 mock:", str(payload)[:150])
            except Exception as e:
                print(f"[proxy][WARN] S1 请求失败，降级 mock: {e}")

    scenario_map = {
        "D001": "design_yuncheng_site_A001.json",
        "D002": "design_indoor_B001.json",
        "D003": "design_micro_C001.json",
    }
    filename = scenario_map.get(design_task_id, "design_yuncheng_site_A001.json")
    path = Path(MOCK_DIR) / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ════════════════════════════════════════════
#  /health — 三服务健康汇总
# ════════════════════════════════════════════

@app.get("/health")
def health():
    """返回三服务健康状态"""
    result = {"service": "s4-dev-proxy", "status": "UP", "timestamp": _now(), "dependencies": {}}

    # 检查 Python 引擎
    try:
        r = requests.get(f"{ENGINE_URL}/health", timeout=3)
        result["dependencies"]["engine"] = {"url": ENGINE_URL, "status": "UP" if r.status_code == 200 else "DEGRADED"}
    except Exception:
        result["dependencies"]["engine"] = {"url": ENGINE_URL, "status": "DOWN"}

    # 检查前端
    try:
        r = requests.get("http://localhost:5190", timeout=3)
        result["dependencies"]["frontend"] = {"url": "http://localhost:5190", "status": "UP" if r.status_code == 200 else "DEGRADED"}
    except Exception:
        result["dependencies"]["frontend"] = {"url": "http://localhost:5190", "status": "DOWN"}

    return result

# ════════════════════════════════════════════
#  S1 设计 mock — 提供设计任务和设备清单
# ════════════════════════════════════════════

design_tasks = [
    {
        "designTaskId": "D001", "projectId": "PRJ-yuncheng",
        "projectName": "运城南风广场 5G 宏站", "siteType": "macro",
        "status": "approved", "deviceCount": 15,
        "createdAt": "2026-07-15 10:30:00", "reviewedAt": "2026-07-20 14:00:00",
    },
    {
        "designTaskId": "D002", "projectId": "PRJ-indoor-mall",
        "projectName": "万象城商业综合体室分覆盖", "siteType": "indoor",
        "status": "approved", "deviceCount": 14,
        "createdAt": "2026-07-18 09:00:00", "reviewedAt": "2026-07-22 11:00:00",
    },
    {
        "designTaskId": "D003", "projectId": "PRJ-micro-urban",
        "projectName": "解放路步行街微站群", "siteType": "micro",
        "status": "approved", "deviceCount": 9,
        "createdAt": "2026-07-20 15:00:00", "reviewedAt": "2026-07-25 16:00:00",
    },
]


@app.get("/api/s1/design/tasks")
def s1_design_tasks(page: int = Query(1), size: int = Query(20)):
    """S1 设计任务列表（mock）"""
    return {"records": design_tasks, "total": len(design_tasks), "page": page, "size": size}


@app.get("/api/s1/design/tasks/{design_task_id}")
def s1_design_detail(design_task_id: str):
    """S1 设计任务详情（含设备清单）"""
    design = _load_design(design_task_id)
    if not design:
        raise HTTPException(404, f"Design task not found: {design_task_id}")
    return {"status": "ok", "designTaskId": design_task_id, "data": design}


# ════════════════════════════════════════════
#  S3 审查 mock — 分级违规数据（critical/error/warning/pending）
#  对齐 S3 真实规则库：规则前缀=类别（EL电气/LP线缆/GD工艺/EM电磁/OS空间），
#  违规精确到设备级（deviceIds）+ 字段级（field），携带国标依据与整改建议。
# ════════════════════════════════════════════

# 各设计任务的违规数据（演示分级闸门：D002 带警告+待复核 → 放行打标）
S3_VIOLATIONS = {
    "D002": [
        {
            "ruleId": "LP-203", "ruleName": "光缆与电源线间距不足",
            "category": "LP", "severity": "warning",
            "standard": "GB/T 6451-2015 第8.2条",
            "deviceIds": ["RRU-B001-03", "RRU-B001-05"], "deviceCount": 2,
            "field": "cableRoute",
            "suggestion": "光缆与电源线分管敷设，平行间距≥30cm，交叉处加隔离护套",
        },
        {
            "ruleId": "EL-112", "ruleName": "接地电阻临界",
            "category": "EL", "severity": "warning",
            "standard": "GB 50689-2011 第4.3条",
            "deviceIds": ["BBU-B001-01"], "deviceCount": 1,
            "field": "groundingResistance",
            "suggestion": "增设一组接地极，实测电阻<5Ω 后复验",
        },
        {
            "ruleId": "OS-301", "ruleName": "吊顶内路由待复核",
            "category": "OS", "severity": "pending",
            "standard": "YD 5120-2010 第6.4条",
            "deviceIds": ["POI-B001-02"], "deviceCount": 1,
            "field": "ceilingRoute",
            "suggestion": "现场核实吊顶承重与检修口位置，确认后回灌 S3 复核",
        },
    ],
    # D001 / D003：审查干净通过（无违规）
}


def _review_gate(design_task_id: str) -> dict:
    """分级闸门（与引擎 review_gate.check_gate 同一套判定规则）。

    critical/error>0 → blocked；仅 warning/pending → allowed_with_warnings；否则 allowed。
    """
    violations = S3_VIOLATIONS.get(design_task_id, [])
    counts = {"critical": 0, "error": 0, "warning": 0, "pending": 0}
    for v in violations:
        counts[v["severity"]] = counts.get(v["severity"], 0) + 1
    if counts["critical"] > 0 or counts["error"] > 0:
        decision = "blocked"
    elif counts["warning"] > 0 or counts["pending"] > 0:
        decision = "allowed_with_warnings"
    else:
        decision = "allowed"
    return decision, counts, violations


@app.get("/api/s3/review/tasks")
def s3_review_tasks(page: int = Query(1), size: int = Query(20)):
    """S3 审查任务列表（mock — 含分级违规统计）"""
    reviews = []
    for dt in design_tasks:
        decision, counts, violations = _review_gate(dt["designTaskId"])
        reviews.append({
            "reviewTaskId": f"R-{dt['designTaskId']}",
            "designTaskId": dt["designTaskId"],
            "projectName": dt["projectName"],
            "status": "approved",
            "violations": len(violations),
            "critical": counts["critical"], "error": counts["error"],
            "warning": counts["warning"], "pending": counts["pending"],
            "reviewedAt": dt.get("reviewedAt", _now()),
        })
    return {"records": reviews, "total": len(reviews), "page": page, "size": size}


@app.get("/api/s3/review/result/{design_task_id}")
def s3_review_result(design_task_id: str):
    """S3 审查结果详情（mock — 分级违规 + 设备关联 + 国标依据 + 整改建议）"""
    design = _load_design(design_task_id)
    if not design:
        raise HTTPException(404, f"Review result not found: {design_task_id}")
    decision, counts, violations = _review_gate(design_task_id)
    result = "rejected" if decision == "blocked" else (
        "approved_with_warnings" if decision == "allowed_with_warnings" else "approved"
    )
    return {
        "status": "ok",
        "reviewTaskId": f"R-{design_task_id}",
        "designTaskId": design_task_id,
        "projectName": design.get("projectName", ""),
        "result": result,
        "violationCount": len(violations),
        "summary": counts,
        "violations": violations,
        "reviewedAt": _now(),
    }


# ── S3 反馈接收端点（BOM→S3 回灌施工侧信息）─────────────────

s3_feedback_store: dict[str, dict] = {}   # designTaskId → 反馈记录


@app.post("/api/s3/review/feedback")
def s3_review_feedback(body: dict):
    """S3 接收 S4 BOM 反馈（反馈回路契约）

    body: {designTaskId, bomTaskId, constructability: ok|with_warnings,
           gateDecision, violationCounts, rectificationSteps[], materialSubstitutions[], bomStats{}}
    """
    design_task_id = body.get("designTaskId", "")
    if not design_task_id:
        raise HTTPException(400, "designTaskId 不能为空")
    s3_feedback_store[design_task_id] = {
        "designTaskId": design_task_id,
        "bomTaskId": body.get("bomTaskId", ""),
        "constructability": body.get("constructability", "ok"),
        "gateDecision": body.get("gateDecision", ""),
        "violationCounts": body.get("violationCounts", {}),
        "rectificationSteps": body.get("rectificationSteps", []),
        "materialSubstitutions": body.get("materialSubstitutions", []),
        "bomStats": body.get("bomStats", {}),
        "receivedAt": _now(),
    }
    print(f"[proxy] S3 received BOM feedback: designTaskId={design_task_id} "
          f"constructability={body.get('constructability')}")
    return {"status": "ok", "designTaskId": design_task_id, "message": "反馈已接收，待整改核验后闭环"}


@app.get("/api/s3/review/feedback/{design_task_id}")
def s3_review_feedback_get(design_task_id: str):
    """查询 S4 对某设计任务的 BOM 反馈"""
    if design_task_id not in s3_feedback_store:
        return {"designTaskId": design_task_id, "feedback": None, "message": "暂无 BOM 反馈"}
    return {"designTaskId": design_task_id, "feedback": s3_feedback_store[design_task_id]}


# ════════════════════════════════════════════
#  S4 BOM — 核心（转发到 Python 引擎）
# ════════════════════════════════════════════

@app.post("/api/s4/bom/generate")
def bom_generate(body: dict):
    """异步生成 BOM — 立即返回 taskId，后台调 Python 引擎"""
    task_id = str(uuid.uuid4())
    design_task_id = body.get("designTaskId", "D001")
    project_id = body.get("projectId", "yuncheng-5g")

    # S3 分级审查闸门预检（critical/error → 拦截，不让任务进入异步队列）
    decision, counts, violations = _review_gate(design_task_id)
    if decision == "blocked":
        blockers = [v for v in violations if v["severity"] in ("critical", "error")]
        print(f"[proxy] BOM blocked by S3 gate: designTaskId={design_task_id} counts={counts}")
        raise HTTPException(409, {
            "message": "设计存在致命/严重审查违规，已拦截 BOM 生成，请先整改并重新提交 S3 审查",
            "gateDecision": decision,
            "violationCounts": counts,
            "blockers": blockers,
        })

    tasks_store[task_id] = {
        "taskId": task_id,
        "designTaskId": design_task_id,
        "projectId": project_id,
        "status": "running",
        "createdAt": _now(),
    }
    print(f"[proxy] S4 task created: {task_id} designTaskId={design_task_id}")

    def _run():
        try:
            engine_resp = requests.post(
                f"{ENGINE_URL}/api/v1/bom/generate",
                json={"taskId": task_id, "designTaskId": design_task_id, "projectId": project_id},
                timeout=120,
            )
            data = engine_resp.json()
            if data.get("status") == "ok":
                bom = data.get("bom", {})
                tasks_store[task_id].update({
                    "status": "done",
                    "finishedAt": _now(),
                    "mainDeviceQty": bom.get("mainDeviceQty", 0),
                    "auxiliaryQty": bom.get("auxiliaryQty", 0),
                    "cableQty": bom.get("cableQty", 0),
                    "totalQty": bom.get("totalItems", 0),
                    "totalCategories": len(set(i.get("materialCode", "") for i in bom.get("items", []))),
                    "items": bom.get("items", []),
                    "processRequirements": data.get("processRequirements", []),
                    "fiberAllocation": data.get("fiberAllocation"),
                    "reviewGate": data.get("reviewGate"),
                    "projectName": _load_design(design_task_id).get("projectName", ""),
                })
                print(f"[proxy] S4 task done: {task_id} items={bom.get('totalItems')}")
            else:
                tasks_store[task_id]["status"] = "failed"
                tasks_store[task_id]["error"] = data.get("message", "引擎返回异常")
        except Exception as e:
            print(f"[proxy] S4 task failed: {task_id} {e}")
            tasks_store[task_id]["status"] = "failed"
            tasks_store[task_id]["error"] = str(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {"taskId": task_id, "status": "running"}


@app.get("/api/s4/bom/{task_id}/status")
def bom_status(task_id: str):
    """轮询任务状态"""
    task = tasks_store.get(task_id)
    if not task:
        return {"taskId": task_id, "status": "not_found"}
    result = {"taskId": task["taskId"], "status": task["status"], "createdAt": task["createdAt"]}
    if task["status"] == "done":
        result["totalItems"] = task.get("totalQty", 0)
        result["totalCategories"] = task.get("totalCategories", 0)
        result["finishedAt"] = task.get("finishedAt")
    if task["status"] == "failed":
        result["error"] = task.get("error", "BOM 生成失败")
    return result


@app.get("/api/s4/bom/history")
def bom_history(page: int = Query(1), size: int = Query(20)):
    """历史列表"""
    all_tasks = list(tasks_store.values())
    all_tasks.sort(key=lambda t: t.get("createdAt", ""), reverse=True)
    total = len(all_tasks)
    start = (page - 1) * size
    records = all_tasks[start : start + size]
    slim = []
    for t in records:
        slim.append({k: v for k, v in t.items() if k not in ("items", "processRequirements", "fiberAllocation")})
    return {"records": slim, "total": total, "page": page, "size": size}


@app.get("/api/s4/bom/{task_id}")
def bom_detail(task_id: str):
    """BOM 详情（仅物料）"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return _build_detail(task)


@app.get("/api/s4/bom/{task_id}/full")
def bom_full(task_id: str):
    """全量查询（物料 + 工序 + 纤芯）"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    result = _build_detail(task)
    if task.get("processRequirements"):
        result["processRequirements"] = task["processRequirements"]
    if task.get("fiberAllocation"):
        result["fiberAllocation"] = task["fiberAllocation"]
    if task.get("reviewGate"):
        result["reviewGate"] = task["reviewGate"]
    return result


@app.get("/api/s4/bom/{task_id}/export")
def bom_export(task_id: str):
    """Excel 导出"""
    filepath = Path(EXPORT_DIR) / f"{task_id}.xlsx"
    if not filepath.exists():
        raise HTTPException(404, f"Excel not found: {filepath}")
    return FileResponse(
        path=str(filepath),
        filename=f"BOM_{task_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _build_detail(task: dict) -> dict:
    return {
        "taskId": task["taskId"],
        "designTaskId": task.get("designTaskId"),
        "projectId": task.get("projectId"),
        "projectName": task.get("projectName", ""),
        "status": task["status"],
        "totalCategories": task.get("totalCategories", 0),
        "totalQty": task.get("totalQty", 0),
        "mainDeviceQty": task.get("mainDeviceQty", 0),
        "auxiliaryQty": task.get("auxiliaryQty", 0),
        "cableQty": task.get("cableQty", 0),
        "items": task.get("items", []),
        "createdAt": task.get("createdAt"),
        "finishedAt": task.get("finishedAt"),
    }


# ════════════════════════════════════════════
#  S5 施工监管 mock（占位）
# ════════════════════════════════════════════

s5_store: dict[str, dict] = {}   # bomTaskId → S5 推送记录


@app.get("/api/s5/verify/tasks")
def s5_verify_tasks():
    """S5 验真任务列表（mock 占位）"""
    return {"records": list(s5_store.values()), "total": len(s5_store)}


@app.post("/api/s5/verify/tasks")
def s5_notify_bom(body: dict):
    """S5 接收 BOM 推送（S4 → S5 联调契约 I4）

    body: {bomTaskId, designTaskId, projectId, projectName, stats{...}}
    """
    bom_task_id = body.get("bomTaskId", body.get("taskId", ""))
    if not bom_task_id:
        raise HTTPException(400, "bomTaskId 不能为空")
    s5_store[bom_task_id] = {
        "bomTaskId": bom_task_id,
        "designTaskId": body.get("designTaskId", ""),
        "projectId": body.get("projectId", ""),
        "projectName": body.get("projectName", ""),
        "stats": body.get("stats", {}),
        "status": "pending",
        "receivedAt": _now(),
    }
    print(f"[proxy] S5 received BOM: {bom_task_id}")
    return {"status": "ok", "bomTaskId": bom_task_id, "message": "已接收，等待施工验真"}


@app.get("/api/s5/verify/status/{bom_task_id}")
def s5_verify_status(bom_task_id: str):
    """S5 验真状态查询（mock）"""
    return {"bomTaskId": bom_task_id, "status": "pending", "message": "等待 BOM 生成后自动触发验真"}


# ════════════════════════════════════════════
#  流水线状态汇总（一次调遍 S1→S3→S4→S5）
# ════════════════════════════════════════════

@app.get("/api/pipeline/status")
def pipeline_status():
    """全流水线状态一览"""
    return {
        "pipeline": "XA-202610 通信基建工程数智化设计与交付",
        "stages": [
            {"id": "S1", "name": "智能辅助设计", "status": "online", "taskCount": len(design_tasks), "url": "/api/s1/design/tasks"},
            {"id": "S3", "name": "智能审查", "status": "online", "taskCount": len(design_tasks), "feedbackCount": len(s3_feedback_store), "url": "/api/s3/review/tasks"},
            {"id": "S4", "name": "施工指令转化 (BOM)", "status": "online", "taskCount": len(tasks_store), "url": "/api/s4/bom/history", "highlight": True},
            {"id": "S5", "name": "施工监管", "status": "online" if s5_store else "pending", "taskCount": len(s5_store), "url": "/api/s5/verify/tasks"},
        ],
        "timestamp": _now(),
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  S4 Dev Proxy  (XA-202610 全流水线模拟)")
    print("  S1 设计 :8090/api/s1/*  →  S3 审查 :8090/api/s3/*")
    print("  S4 BOM  :8090/api/s4/*  →  Python 引擎 :8100")
    print("  S5 监管 :8090/api/s5/*")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
