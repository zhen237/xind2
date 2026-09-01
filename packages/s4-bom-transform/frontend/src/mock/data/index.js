/**
 * 前端虚拟数据入口 — 由 engine/dump_mock_frontend.py 自动生成，勿手改。
 * 数据来自真实 BOM 引擎管线（运城宏站 / 室分 / 微站 三场景快照）。
 */
import designTasks from './design_tasks.json'
import designD001 from './design_D001.json'
import designD002 from './design_D002.json'
import designD003 from './design_D003.json'
import bomD001 from './bom_D001.json'
import bomD002 from './bom_D002.json'
import bomD003 from './bom_D003.json'

export const DESIGN_TASKS = designTasks

export const DESIGNS = { D001: designD001, D002: designD002, D003: designD003 }

export const BOM_SNAPSHOTS = { D001: bomD001, D002: bomD002, D003: bomD003 }

/** S3 审查结果（从 BOM 快照的 reviewGate + 原始违规构造，保持与 dev-proxy 响应同构） */
export function buildReviewResult(designTaskId) {
  const bom = BOM_SNAPSHOTS[designTaskId]
  if (!bom) return null
  const gate = bom.reviewGate || {}
  return {
    status: 'ok',
    reviewTaskId: `R-${designTaskId}`,
    designTaskId,
    projectName: bom.projectName,
    result: gate.result || 'approved',
    violationCount: (gate.violations || []).length,
    summary: gate.counts || {},
    violations: gate.violations || [],
    reviewedAt: '2026-07-22 11:00:00',
  }
}
