import axios from 'axios'

// 状态条专用实例：带 token（S2/S1/S4 端点需鉴权），但**不挂全局错误拦截器**，
// 避免某个后端未启动时在 15s 轮询里反复弹 alert。失败由各调用点兜底为 null。
const http = axios.create({
  baseURL: '/api',
  timeout: 5000
})
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) config.headers['Authorization'] = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

// 统一把各后端不同返回结构解析为「数量」：
// - S2/S1/S3：Spring Result 包裹 {code,message,data:[...]}
// - S4：MyBatis-Plus Page 转 Map {records:[...], total:N, ...}（注意：total 字段偶发异常为 0，需回退 records.length）
// - S5：Node 直接返回数组 [...]
function countFrom(r) {
  if (r == null) return null
  // 兼容 Spring Result 包裹：取 r.data
  let payload = r && typeof r === 'object' && 'data' in r ? r.data : r
  if (Array.isArray(payload)) return payload.length
  if (payload && typeof payload === 'object') {
    if (Array.isArray(payload.records)) {
      // total 真实时优先用 total；total 异常(<=0 但 records 非空)时回退 records.length
      const total = typeof payload.total === 'number' ? payload.total : payload.records.length
      return total > 0 ? total : payload.records.length
    }
    if (typeof payload.total === 'number') return payload.total
    if (Array.isArray(payload.list)) return payload.list.length
  }
  return null
}

// m03 的 /api/m03/design/** 需要 X-API-Key（dev 默认 CHANGE_ME，可由 VITE_M03_API_KEY 覆盖）
const M03_API_KEY = import.meta.env.VITE_M03_API_KEY || 'CHANGE_ME'

async function safeGet(url, headers) {
  try {
    const res = await http.get(url, { headers: headers || {} })
    return res.data
  } catch (e) {
    return null
  }
}

// 拉取五个阶段的实时计数，任一失败返回 null（前端显示「—」）
export async function fetchStageCounts() {
  const [s2, s1, s3, s4, s5] = await Promise.all([
    safeGet('/s2/cad/fusion/tasks'), // S2 融合任务数
    safeGet('/m03/design/tasks', { 'X-API-Key': M03_API_KEY }), // S1 设计方案数（需 api-key）
    safeGet('/v1/s3/review/task'), // S3 审查任务数
    safeGet('/s4/bom/history?page=1&size=1'), // S4 BOM/指令数（total/records）
    safeGet('/s5/devices') // S5 监测设备数（数组长度）
  ])
  return {
    s2: countFrom(s2),
    s1: countFrom(s1),
    s3: countFrom(s3),
    s4: countFrom(s4),
    s5: countFrom(s5)
  }
}
