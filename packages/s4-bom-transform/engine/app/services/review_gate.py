"""S3 审查结果消费 — 分级闸门 + 违规提取 + BOM→S3 反馈回路。

闭合 S3 对比分析发现的 3 个关键差距:
  1. S3 分级违规数据消费（critical/error/warning/pending + 涉及设备 + 整改建议 + 国标依据）
  2. 四档分级审查闸门（替代二元 approved 拦截）
  3. BOM 完成后反馈回路给 S3（施工可行性 / 物料替代建议回灌）

S3 审查结果契约（消费字段）:
  {
    "result": "approved" | "approved_with_warnings" | "rejected",
    "summary": {"critical": 0, "error": 0, "warning": 2, "pending": 1},
    "violations": [
      {
        "ruleId": "LP-203",             # 规则编号（前缀=类别 EL/LP/GD/EM/OS）
        "ruleName": "...",               # 规则名
        "category": "LP",                # 规则类别
        "severity": "warning",           # critical | error | warning | pending
        "standard": "GB/T 6451-2015 ...",# 国标依据
        "deviceIds": ["DEV-003"],        # 涉及设备（精确到设备级）
        "deviceCount": 1,
        "field": "cableRoute",           # 违规字段（精确到字段级）
        "suggestion": "..."              # 整改建议
      }
    ]
  }

闸门策略:
  - critical / error > 0  → BLOCKED                （拦截 BOM 生成）
  - 仅 warning / pending  → ALLOWED_WITH_WARNINGS  （放行，结果携带整改标记）
  - 无违规 / S3 不可达    → ALLOWED                （降级放行，联调期不阻断主链路）
"""
import logging

import requests

from app.config import settings

logger = logging.getLogger("s4-engine.review-gate")

# 闸门判定档位
BLOCKED = "blocked"
ALLOWED_WITH_WARNINGS = "allowed_with_warnings"
ALLOWED = "allowed"

# 严重级别 → 中文说明
SEVERITY_LABEL = {
    "critical": "致命",
    "error": "严重",
    "warning": "警告",
    "pending": "待复核",
}

# 规则类别前缀 → 类别名（与 S3 规则库对齐）
CATEGORY_LABEL = {
    "EL": "电气",
    "LP": "线缆路由",
    "GD": "工艺/管道",
    "EM": "电磁",
    "OS": "空间/其他",
}


# ────────────────────────────────────────
#  1. 拉取 S3 审查结果
# ────────────────────────────────────────

def load_review(design_task_id: str) -> dict | None:
    """拉取 S3 审查结果。

    mock 模式: 请求 dev-proxy(8090) 的 S3 mock 接口
    real 模式: 请求 S3 真实服务 GET {s3_base_url}/api/s3/review/result/{id}

    S3 不可达时返回 None（降级放行，联调期不阻断主链路）。
    """
    if settings.data_source == "real" and settings.s3_base_url:
        base = settings.s3_base_url.rstrip("/")
    else:
        base = settings.java_backend_url.rstrip("/")  # dev-proxy 同时模拟 S3
    url = f"{base}/api/s3/review/result/{design_task_id}"
    try:
        logger.info("[review] fetching S3 review result: %s", url)
        resp = requests.get(url, timeout=settings.s1_timeout)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        review = data if isinstance(data, dict) else payload
        if not isinstance(review, dict):
            logger.warning("[review] S3 返回格式异常，降级放行: %s", str(payload)[:150])
            return None
        logger.info("[review] S3 review loaded: designTaskId=%s result=%s violations=%d",
                    design_task_id, review.get("result"), len(review.get("violations", [])))
        return review
    except Exception as e:
        logger.warning("[review] S3 审查服务不可达，降级放行: %s err=%s", design_task_id, e)
        return None


# ────────────────────────────────────────
#  2. 四档分级闸门
# ────────────────────────────────────────

def check_gate(review: dict | None) -> dict:
    """分级闸门判定。

    返回 {
      "decision": blocked | allowed_with_warnings | allowed,
      "result": S3 原始结论,
      "counts": {critical, error, warning, pending},
      "blockers": [致命/严重违规摘要],   # decision=blocked 时非空
      "violations": [全部违规明细],
      "degraded": bool                   # true=S3 不可达降级放行
    }
    """
    if review is None:
        return {
            "decision": ALLOWED,
            "result": "unknown",
            "counts": {"critical": 0, "error": 0, "warning": 0, "pending": 0},
            "blockers": [],
            "violations": [],
            "degraded": True,
        }

    violations = review.get("violations", []) or []
    counts = {"critical": 0, "error": 0, "warning": 0, "pending": 0}
    for v in violations:
        sev = str(v.get("severity", "warning")).lower()
        if sev in counts:
            counts[sev] += 1

    blockers = [
        {
            "ruleId": v.get("ruleId"),
            "ruleName": v.get("ruleName"),
            "severity": v.get("severity"),
            "standard": v.get("standard", ""),
            "deviceIds": v.get("deviceIds", []),
            "suggestion": v.get("suggestion", ""),
        }
        for v in violations
        if str(v.get("severity", "")).lower() in ("critical", "error")
    ]

    if counts["critical"] > 0 or counts["error"] > 0:
        decision = BLOCKED
    elif counts["warning"] > 0 or counts["pending"] > 0:
        decision = ALLOWED_WITH_WARNINGS
    else:
        decision = ALLOWED

    return {
        "decision": decision,
        "result": review.get("result", "unknown"),
        "counts": counts,
        "blockers": blockers,
        "violations": violations,
        "degraded": False,
    }


# ────────────────────────────────────────
#  3. 违规数据落地：设备打标 + 工序吸收
# ────────────────────────────────────────

def flag_devices(design_data: dict, gate: dict) -> dict:
    """把 warning/pending 违规关联到具体设备 — 受影响设备打 requiresRectification 标记。

    S3 违规精确到设备级（deviceIds），S4 据此在 BOM 结果中对相应设备物料打标，
    提醒施工班组领料时核对整改要求。
    """
    marked_ids: set[str] = set()
    for v in gate.get("violations", []):
        if str(v.get("severity", "")).lower() in ("warning", "pending"):
            for did in v.get("deviceIds", []) or []:
                marked_ids.add(str(did))

    if not marked_ids:
        return design_data

    devices = design_data.get("devices", [])
    for dev in devices:
        dev_id = str(dev.get("deviceId") or dev.get("id") or dev.get("name") or "")
        if dev_id in marked_ids:
            dev["requiresRectification"] = True

    logger.info("[review] %d devices flagged requiresRectification", len(marked_ids))
    return design_data


def build_rectification_steps(gate: dict) -> list[dict]:
    """把 S3 整改建议转化为 BOM 工序清单中的「整改核验」工序。

    每条 warning/pending 违规 → 一道整改核验工序，携带国标依据与 S3 规则编号，
    施工班组按工序执行即可完成整改闭环（不再靠人工翻审查报告）。
    """
    steps = []
    for idx, v in enumerate(gate.get("violations", []), start=1):
        sev = str(v.get("severity", "")).lower()
        if sev not in ("warning", "pending"):
            continue
        category = str(v.get("category", ""))
        steps.append({
            "stepId": f"RECT-{idx:02d}",
            "stepType": "rectification",
            "name": f"整改核验：{v.get('ruleName', 'S3 审查项')}",
            "severity": sev,
            "category": category,
            "categoryLabel": CATEGORY_LABEL.get(category, category),
            "ruleId": v.get("ruleId", ""),
            "standard": v.get("standard", ""),
            "deviceIds": v.get("deviceIds", []),
            "deviceCount": v.get("deviceCount", len(v.get("deviceIds", []) or [])),
            "requirement": v.get("suggestion", ""),
            "checkMethod": "现场核验 + 拍照回传 S5，复核通过后回灌 S3",
        })
    return steps


# ────────────────────────────────────────
#  4. 反馈回路：BOM → S3
# ────────────────────────────────────────

def send_feedback(design_task_id: str, bom_task_id: str, gate: dict, bom_stats: dict) -> bool:
    """BOM 完成后回灌施工侧信息给 S3（旁路，失败不阻断）。

    反馈内容:
      - constructability: ok | with_warnings（施工可行性结论）
      - rectificationSteps: 已纳入 BOM 工序的整改核验项
      - materialSubstitutions: 物料替代建议（编码库无法映射时的人工替代方案）
      - bomStats: 物料统计
    """
    if settings.data_source == "real" and settings.s3_base_url:
        base = settings.s3_base_url.rstrip("/")
    else:
        base = settings.java_backend_url.rstrip("/")
    url = f"{base}/api/s3/review/feedback"

    rect_steps = build_rectification_steps(gate)
    payload = {
        "designTaskId": design_task_id,
        "bomTaskId": bom_task_id,
        "constructability": "with_warnings" if gate.get("decision") == ALLOWED_WITH_WARNINGS else "ok",
        "gateDecision": gate.get("decision"),
        "violationCounts": gate.get("counts", {}),
        "rectificationSteps": rect_steps,
        "materialSubstitutions": [],   # 预留：物料库未覆盖时的替代建议回灌
        "bomStats": bom_stats or {},
    }
    try:
        resp = requests.post(url, json=payload, timeout=settings.s1_timeout)
        logger.info("[feedback] BOM→S3 feedback sent: designTaskId=%s bomTaskId=%s http=%d",
                    design_task_id, bom_task_id, resp.status_code)
        return resp.status_code < 400
    except Exception as e:
        logger.warning("[feedback] BOM→S3 反馈失败（旁路，不阻断）: %s", e)
        return False
