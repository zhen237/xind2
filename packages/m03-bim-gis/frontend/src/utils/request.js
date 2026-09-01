import axios from 'axios'
import { ElMessage } from 'element-plus'
import mockAdapter from '@/mock/adapter.js'

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
// 无后端静态部署（GitHub Pages）时，用虚拟数据适配器替代真实 HTTP 请求
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  ...(USE_MOCK ? { adapter: mockAdapter } : {})
})

service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    // M03 内部数据接口（design/project/device/model/region 等）由 DesignApiKeyInterceptor
    // 强制要求 X-API-Key，与 QGIS 插件保持一致；llm 接口为双通道，带 Key 亦可放行。
    // 本地调试默认 CHANGE_ME，上线通过 VITE_M03_API_KEY 覆盖，勿硬编码密钥到仓库。
    if (config.url && config.url.includes('/m03/')) {
      config.headers['X-API-Key'] = import.meta.env.VITE_M03_API_KEY || 'CHANGE_ME'
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
  generateDesign: (data) => service.post('/m03/design/generate', data),
  // ── 方案A：任务式生成（先建任务带 paramsJson，再执行任务，执行后自动推送 S3 审查） ──
  createDesignTask: (data) => service.post('/m03/design/tasks', data),
  listDesignTasks: (params) => service.get('/m03/design/tasks', { params }),
  executeDesignTask: (taskId) => service.post(`/m03/design/tasks/${taskId}/generate`),
  getTaskResult: (taskId) => service.get(`/m03/design/tasks/${taskId}/result`),
  deleteDesignTask: (taskId) => service.delete(`/m03/design/tasks/${taskId}`),
  saveTaskLocalData: (taskId, geojson) => service.put(`/m03/design/tasks/${taskId}/local-data`, { data: geojson }),
  // 任务主线：项目详情聚合（项目 + 方案缓存 + 项目下全部任务）
  projectDetails: (projectId) => service.get(`/m03/design/projects/${projectId}/details`),
  // ── 方案 A：S1 本地加载 GeoJSON 后「送审 S3 审查」（走 M03 后端转发到 S3） ──
  submitToS3: (data) => service.post('/m03/design/submit-to-s3', data)
}

// ── FTTH 数据集 API ────────────────────────────────────────
// 数据源由 QGIS 插件「同步 FTTH 成果到 S1」推送到后端 FTTH_DATA_DIR，
// 页面优先走这里拿最新成果；后端不可达时再回退 public/datasets 静态文件。
export const ftthAPI = {
  list: () => service.get('/m03/ftth'),
  getDataset: (tag) => service.get(`/m03/ftth/${tag}`),
  getPart: (tag, type) => service.get(`/m03/ftth/${tag}/${type}`)
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
