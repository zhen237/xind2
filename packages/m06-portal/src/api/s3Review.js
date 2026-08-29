import axios from 'axios'

// S1 推送过来的审查任务，后端统一以 createBy='S1模块' 标记
export const S1_CREATE_BY = 'S1模块'

// 拉取 S3 审查任务列表（后端返回 {code,message,data:[...]}）
// 仅保留 createBy='S1模块' 的 S1 推送任务，按创建时间倒序取前 limit 条
export async function getS1ReviewTasks(limit = 6) {
  const res = await axios.get('/api/v1/s3/review/task')
  const rows = (res.data && res.data.data) || []
  const s1Rows = rows
    .filter((t) => t.createBy === S1_CREATE_BY)
    .sort((a, b) => String(b.createTime).localeCompare(String(a.createTime)))
    .slice(0, limit)
  return s1Rows
}

// S3 任务状态 -> 中文 + 展示色
export const TASK_STATUS_MAP = {
  COMPLETED: { label: '已完成', color: '#22c55e' },
  FAILED: { label: '失败', color: '#ef4444' },
  PROCESSING: { label: '审查中', color: '#3b82f6' },
  PENDING: { label: '待执行', color: '#94a3b8' }
}

export function statusLabel(status) {
  return (TASK_STATUS_MAP[status] || { label: status, color: '#94a3b8' }).label
}

export function statusColor(status) {
  return (TASK_STATUS_MAP[status] || { label: status, color: '#94a3b8' }).color
}

// 拉取单条 S3 审查任务的规则结果明细
// 返回 {code,message,data:[ReviewResultItem...]}，每条含
//   rule_code / rule_name / category / risk_level(pending|warning|error|critical)
//   / standard_param(国标阈值) / suggestion(缺参提示或整改建议) / actual_value / standard_value
export async function getTaskResults(taskId) {
  const res = await axios.get(`/api/v1/s3/review/task/${taskId}/results`)
  return (res.data && res.data.data) || []
}
