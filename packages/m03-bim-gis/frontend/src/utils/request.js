import axios from 'axios'
import { ElMessage } from 'element-plus'

// ==================== 请求去重 ====================
const pendingRequests = new Map()

function getRequestKey(config) {
  const { method, url, params, data } = config
  return [method, url, JSON.stringify(params), JSON.stringify(data)].join('&')
}

function addPending(config) {
  const key = getRequestKey(config)
  // 如果已有相同请求在进行中，取消旧的
  if (pendingRequests.has(key)) {
    pendingRequests.get(key).abort()
  }
  const controller = new AbortController()
  config.signal = controller.signal
  pendingRequests.set(key, controller)
}

function removePending(config) {
  const key = getRequestKey(config)
  pendingRequests.delete(key)
}

// ==================== Axios 实例 ====================
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000
})

service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    // 请求去重: 对 GET 请求自动取消重复
    if (config.method === 'get' || config.method === 'GET') {
      addPending(config)
    }
    return config
  },
  error => Promise.reject(error)
)

service.interceptors.response.use(
  response => {
    removePending(response.config)
    return response.data
  },
  error => {
    // AbortController 取消的请求不视为错误，无需调用 removePending
    // （addPending 已用新 controller 覆盖，removePending 会误删新请求的引用）
    if (axios.isCancel(error)) {
      return Promise.resolve(null)
    }
    removePending(error.config || {})
    const msg = error.response?.data?.message || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default service

// M03 API 封装
export const projectAPI = {
  list: () => service.get('/m03/project'),
  getById: (id) => service.get(`/m03/project/${id}`),
  create: (data) => service.post('/m03/project', data),
  update: (id, data) => service.put(`/m03/project/${id}`, data),
  delete: (id) => service.delete(`/m03/project/${id}`)
}

export const deviceAPI = {
  list: () => service.get('/m03/device'),
  getById: (id) => service.get(`/m03/device/${id}`),
  getByProject: (projectId) => service.get(`/m03/device/project/${projectId}`),
  getByStation: (stationCode) => service.get(`/m03/device/station/${stationCode}`),
  getByType: (deviceType) => service.get(`/m03/device/type/${deviceType}`),
  create: (data) => service.post('/m03/device', data),
  update: (id, data) => service.put(`/m03/device/${id}`, data),
  delete: (id) => service.delete(`/m03/device/${id}`)
}

export const modelAPI = {
  list: () => service.get('/m03/model'),
  getById: (id) => service.get(`/m03/model/${id}`),
  getByType: (modelType) => service.get(`/m03/model/type/${modelType}`),
  create: (data) => service.post('/m03/model', data),
  update: (id, data) => service.put(`/m03/model/${id}`, data),
  delete: (id) => service.delete(`/m03/model/${id}`)
}

export const regionAPI = {
  list: () => service.get('/m03/region'),
  getById: (id) => service.get(`/m03/region/${id}`),
  getByParent: (parentCode) => service.get(`/m03/region/parent/${parentCode}`),
  create: (data) => service.post('/m03/region', data),
  update: (id, data) => service.put(`/m03/region/${id}`, data),
  delete: (id) => service.delete(`/m03/region/${id}`)
}

export const designAPI = {
  uploadDesign: (data) => service.post('/m03/design/upload', data),
  getDesign: (projectId) => service.get(`/m03/design/${projectId}`),
  getSites: (schemeId) => service.get(`/m03/design/${schemeId}/sites`),
  uploadSite: (schemeId, data) => service.post(`/m03/design/${schemeId}/sites`, data),
  getGeoJson: (projectId) => service.get(`/m03/design/${projectId}/geojson`),
  deleteDesign: (schemeId) => service.delete(`/m03/design/${schemeId}`),
  getTemplates: () => service.get('/m03/design/templates'),
  generateDesign: (data) => service.post('/m03/design/generate', data)
}

// ── 大模型辅助设计 API（①解析需求 ②生成报告） ──────────────
// 超时单独拉到 120s：大模型生成可能耗时 10~60s，避免默认 15s 把正常请求中断。
export const llmAPI = {
  parseDesignParams: (text, context) =>
    service.post(
      '/m03/llm/parse-design-params',
      context ? { text, context } : { text },
      { timeout: 120000 }
    ),
  generateReport: (scheme, context) =>
    service.post(
      '/m03/llm/generate-report',
      context ? { scheme, context } : { scheme },
      { timeout: 120000 }
    )
}
