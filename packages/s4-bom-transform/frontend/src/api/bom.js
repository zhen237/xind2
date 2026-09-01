import axios from 'axios'
import { isMockEnabled } from '../mock'

const BASE = '/api/s4/bom'

/** 异步生成 BOM，立即返回 { taskId, status: "running" } */
export function generateBom(designTaskId, projectId) {
  return axios.post(`${BASE}/generate`, { designTaskId, projectId }).then(r => r.data)
}

/** 轮询任务状态 */
export function getTaskStatus(taskId) {
  return axios.get(`${BASE}/${taskId}/status`).then(r => r.data)
}

/** 查 BOM 详情（仅物料） */
export function getBomDetail(taskId) {
  return axios.get(`${BASE}/${taskId}`).then(r => r.data)
}

/** 全量查询（物料 + 工序 + 纤芯） */
export function getBomFull(taskId) {
  return axios.get(`${BASE}/${taskId}/full`).then(r => r.data)
}

/** 历史列表 */
export function listHistory(page = 1, size = 20) {
  return axios.get(`${BASE}/history`, { params: { page, size } }).then(r => r.data)
}

/** 导出 Excel URL（mock 模式下指向本地虚拟数据自带的演示 Excel） */
export function getExportUrl(taskId) {
  if (isMockEnabled()) return '/mock/BOM_demo.xlsx'
  return `${BASE}/${taskId}/export`
}
