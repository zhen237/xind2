import axios from 'axios'

// 一键跑通全流程：跨服务真实编排（S2→S1→S3→S4→S5）
// 与 stageStatus.js 同理：独立实例，带 token 但不挂全局 alert 拦截器（避免轮询弹窗）。
const http = axios.create({
  baseURL: '/api',
  timeout: 30000
})
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) config.headers['Authorization'] = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

// m03 的 /api/m03/design/** 需要 X-API-Key（默认值与 m03 后端 application.yml 一致）
const M03_API_KEY = import.meta.env.VITE_M03_API_KEY || 'CHANGE_ME'

// 兼容 Spring Result 包裹：取 r.data；裸数组/对象原样返回
function unwrap(r) {
  if (r == null) return null
  if (typeof r === 'object' && 'data' in r) return r.data
  return r
}
function toArray(r) {
  const p = unwrap(r)
  if (Array.isArray(p)) return p
  if (p && Array.isArray(p.records)) return p.records
  if (p && Array.isArray(p.list)) return p.list
  return []
}
const sleep = (ms) => new Promise((res) => setTimeout(res, ms))

// ---- 各阶段真实调用（任一失败 throw，由 UI 捕获并展示真实错误） ----

// S2 数据融合：取一个已解析且能成功融合的 CAD 文件 → auto-fuse
// 说明：文件列表首个可能是空 DXF（融合 FAILED），故按体积降序挑选已解析文件逐个尝试，
// 取首个「非 FAILED」的融合结果；全部失败才抛错（由 UI 标红 + 给手动入口）。
export async function s2EnsureFusion() {
  const files = toArray(await http.get('/s2/cad/cad-files'))
  const candidates = files
    .filter((f) => f.parseStatus == null || f.parseStatus === '已解析' || f.parseStatus === 'PARSED')
    .sort((a, b) => (b.fileSize || 0) - (a.fileSize || 0))
  if (!candidates.length) {
    throw new Error('S2 暂无已解析的 CAD 文件，请先在「S2 数据融合」上传并解析一个 CAD 文件')
  }
  let lastErr = null
  for (const src of candidates) {
    try {
      const body = {
        taskName: '一键演示-融合-' + Date.now(),
        sourceFileId: src.id,
        sourceEpsg: 'EPSG:4326',
        targetEpsg: 'EPSG:4490',
        transformationType: 'helmert'
      }
      const res = unwrap(await http.post('/s2/cad/fusion/auto-fuse', body))
      const fusionId = res?.taskId ?? res?.id
      const status = res?.status
      if (status && String(status).toUpperCase() === 'FAILED') {
        lastErr = res?.errorMessage || `源文件 ${src.originalName || src.fileName} 融合失败`
        continue
      }
      return {
        fusionId,
        srcName: src.originalName || src.fileName || src.name,
        summary: `S2 融合任务 #${fusionId} 已完成（源文件 ${src.originalName || src.fileName || src.name}）`
      }
    } catch (e) {
      lastErr = e?.response?.data?.message || e?.message || 'S2 融合调用失败'
    }
  }
  throw new Error(lastErr || 'S2 融合：所有候选 CAD 文件均融合失败')
}

// S1 智能设计：参考历史任务的设计参数建任务 → 生成（generate 内部自动 submitToS3Review 送审）→ 取 taskNo
// 说明：m03_design_task.params_json 是 NOT NULL 无默认值，建任务必须带 paramsJson（真实 S1 前端同款行为）。
// 数据驱动：优先沿用同区域一条历史任务的 paramsJson+projectId，保证 generate 能真实出结果。
export async function s1CreateAndGenerate() {
  const headers = { 'X-API-Key': M03_API_KEY }
  const body = { taskName: '一键演示-设计-' + Date.now() }
  const existing = toArray(await http.get('/m03/design/tasks', headers))
  const ref = existing.find((t) => t.paramsJson && t.projectId)
  if (ref) {
    body.projectId = String(ref.projectId)
    body.paramsJson = typeof ref.paramsJson === 'string' ? ref.paramsJson : JSON.stringify(ref.paramsJson)
  } else {
    // 兜底：运城学院样例区域的标准宏基站参数（与 m03 历史样例任务一致）
    body.projectId = '90915'
    body.paramsJson = JSON.stringify({
      templateType: 'macro',
      centerLongitude: 110.932025,
      centerLatitude: 35.123754,
      coverageRadius: 500,
      gridSize: '200',
      sectorCount: 3,
      towerHeight: 35,
      frequencyBand: '3.5GHz'
    })
  }
  const created = unwrap(await http.post('/m03/design/tasks', body, headers))
  const id = String(created)
  const gen = unwrap(await http.post(`/m03/design/tasks/${id}/generate`, {}, headers))
  const task = unwrap(await http.get(`/m03/design/tasks/${id}`, headers))
  const taskNo = task?.taskNo || gen?.taskNo || id
  return { designTaskId: id, taskNo, summary: `S1 设计任务 #${id}（${taskNo}）已生成并送审 S3` }
}

// S3 智能审查：轮询等待 S1 推送的审查任务 → forward-to-s4
export async function s3WaitAndForward(designTaskId) {
  let reviewTaskId = null
  let reviewTask = null
  for (let i = 0; i < 20; i++) {
    const arr = toArray(await http.get('/v1/s3/review/task'))
    if (arr.length) {
      const match = designTaskId ? arr.find((t) => String(t.designTaskId) === String(designTaskId)) : null
      reviewTask = match || arr[0]
      reviewTaskId = reviewTask.id ?? reviewTask.reviewTaskId
      break
    }
    await sleep(1500)
  }
  if (!reviewTaskId) {
    throw new Error('S3 未收到 S1 推送的审查任务（可能 S1 生成未成功送审，或 m03-llm 未启动导致生成失败）')
  }
  await http.post(`/v1/s3/review/task/${reviewTaskId}/forward-to-s4`)
  return { reviewTaskId, summary: `S3 审查任务 #${reviewTaskId} 已生成并转发 S4` }
}

// S4 施工指令：按 designTaskId(=S1 taskNo) 生成 BOM → 轮询状态
export async function s4GenerateBom(designTaskId) {
  const g = unwrap(await http.post('/s4/bom/generate', { designTaskId: String(designTaskId) }))
  const bomTaskId = g?.taskId
  if (!bomTaskId) throw new Error('S4 BOM 生成未返回任务 ID')
  let status = 'running'
  for (let i = 0; i < 30; i++) {
    const st = unwrap(await http.get(`/s4/bom/${bomTaskId}/status`))
    status = st?.status || 'running'
    if (status === 'done' || status === 'failed') break
    await sleep(1500)
  }
  return { bomTaskId, status, summary: `S4 BOM 任务 #${bomTaskId} 状态=${status}` }
}

// S5 施工监管：轮询等待 S4 推送的 BOM 核验任务
export async function s5WaitVerify() {
  const before = toArray(await http.get('/s5/verify/tasks'))
  const beforeLen = before.length
  for (let i = 0; i < 20; i++) {
    const cur = toArray(await http.get('/s5/verify/tasks'))
    if (cur.length > beforeLen) {
      return { verifyCount: cur.length, summary: `S5 已接收 S4 推送的 BOM 核验任务（共 ${cur.length} 条）` }
    }
    await sleep(1500)
  }
  return { verifyCount: beforeLen, summary: `S5 核验任务数=${beforeLen}（未检测到新增，可能 S4→S5 推送延迟）` }
}
