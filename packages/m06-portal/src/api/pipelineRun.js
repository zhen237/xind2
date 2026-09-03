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

/**
 * 把 S2 融合任务号写入发给 m03 的 paramsJson（paramsJson 为 m03_design_task 的 JSON 持久化字段）。
 * m03 的 executeDesignTask 用 Spring Boot 默认 ObjectMapper 反序列化到 GenerateRequest，
 * 未知顶层键（s2FusionId）默认忽略，宏基站模板参数不受影响；该键仅用于任务级可追溯记录。
 */
function attachS2FusionId(paramsJson, fusionId) {
  if (fusionId == null || fusionId === '' || String(fusionId) === 'undefined') return paramsJson
  let parsed = paramsJson
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed)
    } catch (e) {
      return paramsJson
    }
  }
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    parsed.s2FusionId = String(fusionId)
    return JSON.stringify(parsed)
  }
  return paramsJson
}

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
// fusionId：S2 融合任务号（可选）。m03 的 DesignTask 无 sourceTaskId/fusionId 专属列，paramsJson 是唯一
// 合法可持久化的自由 JSON 字段，故用 paramsJson.s2FusionId 记录融合来源，不影响宏基站模板参数。
export async function s1CreateAndGenerate(fusionId) {
  // 注意：axios 的 get/post 第 2/3 参数是 config 对象，必须把 key 包进 { headers }，
  // 否则 X-API-Key 不会作为请求头发出，m03 的 DesignApiKeyInterceptor 会返回 401。
  const headers = { 'X-API-Key': M03_API_KEY }
  const body = { taskName: '一键演示-设计-' + Date.now() }
  const existing = toArray(await http.get('/m03/design/tasks', { headers }))
  const ref = existing.find((t) => t.paramsJson && t.projectId)
  let paramsJson = null
  if (ref) {
    body.projectId = String(ref.projectId)
    paramsJson = typeof ref.paramsJson === 'string' ? ref.paramsJson : JSON.stringify(ref.paramsJson)
  } else {
    // 兜底：运城学院样例区域的标准宏基站参数（与 m03 历史样例任务一致）
    body.projectId = '90915'
    paramsJson = JSON.stringify({
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
  body.paramsJson = attachS2FusionId(paramsJson, fusionId)
  const created = unwrap(await http.post('/m03/design/tasks', body, { headers }))
  const id = String(created)
  const gen = unwrap(await http.post(`/m03/design/tasks/${id}/generate`, {}, { headers }))
  const task = unwrap(await http.get(`/m03/design/tasks/${id}`, { headers }))
  const taskNo = task?.taskNo || gen?.taskNo || id
  const fusionMark =
    fusionId != null && String(fusionId) !== '' && String(fusionId) !== 'undefined'
      ? `（已记录 S2 融合任务 #${fusionId}）`
      : ''
  return { designTaskId: id, taskNo, summary: `S1 设计任务 #${id}（${taskNo}）已生成并送审 S3${fusionMark}` }
}

// S3 智能审查：轮询等待 S1 推送的审查任务 → forward-to-s4
// 说明：m03 送审时把审查任务的 designTaskId 写成 S1 的 taskNo（如 DT-…，见 m03 S3ReviewPayloadMapper），
// 故入参传 taskNo 才能严格命中本次 S1 产生的审查任务；绝不转发其它设计任务的审查记录。
export async function s3WaitAndForward(designTaskId) {
  const expected = designTaskId == null ? '' : String(designTaskId)
  if (!expected) {
    throw new Error('S3 等待审查任务缺少 designTaskId（S1 未返回有效 taskNo）')
  }
  let matched = null
  let latestCount = 0
  for (let i = 0; i < 20; i++) {
    const arr = toArray(await http.get('/v1/s3/review/task'))
    latestCount = arr.length
    matched =
      arr.find(
        (t) =>
          (t?.designTaskId != null && String(t.designTaskId) === expected) ||
          (t?.taskNo != null && String(t.taskNo) === expected)
      ) || null
    if (matched) break
    await sleep(1500)
  }
  if (!matched) {
    throw new Error(
      `S3 未收到 S1 设计任务 ${expected} 的审查任务：已轮询 20×1.5s，当前 S3 审查任务 ${latestCount} 条。` +
        '可能 S1 送审未成功或推送延迟（请确认 m03 服务 8083 已启动、generate 已触发 submitToS3Review），' +
        '可到 S3 工作台核对是否有对应 designTaskId 的审查任务后重试。'
    )
  }
  const reviewTaskId = matched.id ?? matched.reviewTaskId
  await http.post(`/v1/s3/review/task/${reviewTaskId}/forward-to-s4`)
  return { reviewTaskId, summary: `S3 审查任务 #${reviewTaskId}（对应设计 ${expected}）已生成并转发 S4` }
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
// 说明：只有检测到核验任务数确实增加才算成功；窗口内无新增则抛错（不再返回伪成功对象）。
export async function s5WaitVerify() {
  const before = toArray(await http.get('/s5/verify/tasks'))
  const beforeLen = before.length
  let lastLen = beforeLen
  for (let i = 0; i < 20; i++) {
    await sleep(1500)
    const cur = toArray(await http.get('/s5/verify/tasks'))
    lastLen = cur.length
    if (cur.length > beforeLen) {
      return { verifyCount: cur.length, summary: `S5 已接收 S4 推送的 BOM 核验任务（共 ${cur.length} 条，较轮询前新增 ${cur.length - beforeLen} 条）` }
    }
  }
  throw new Error(
    `S5 未在 20×1.5s 内收到 S4 推送的 BOM 核验任务（轮询前 ${beforeLen} 条 → 轮询后仍 ${lastLen} 条）。` +
      '请确认：① S5 服务(8091)已启动且 /api/s5/verify/tasks 可访问；② S4→S5 推送链路可达（S4 生成 BOM 后会 POST /api/s5/verify/tasks）；' +
      '③ S4 BOM 任务确已完成。检查后可重试本步。'
  )
}
