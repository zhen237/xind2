/**
 * S4 前端本地虚拟数据 mock（仿 S1 虚拟数据做法）
 *
 * 目的: 让 5190 前端【不依赖后端 8090 / 引擎 8100】即可完整演示
 *      （生成 → 轮询 → 详情三类清单 → 工序/纤芯 → 导出 Excel）。
 *
 * 原理: 接管 axios 默认 adapter，拦截 /api/s1、/api/s3、/api/s4、/api/pipeline
 *      请求，返回 engine/dump_mock_frontend.py 用【真实 BOM 引擎管线】预生成的快照。
 *
 * 启用: frontend/.env 中 VITE_USE_MOCK=true（默认开启），联调时改 false 并重启。
 */
import axios from 'axios'
import { DESIGN_TASKS, DESIGNS, BOM_SNAPSHOTS, buildReviewResult } from './data'

const RESPONSE_DELAY_MS = 300   // 模拟网络延迟
const GENERATE_DURATION_MS = 3000  // 模拟引擎异步计算耗时（演示轮询进度条）

let taskSeq = 0
const tasks = new Map()   // taskId → 任务记录（含运行态）

function now() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
    `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

const clone = (obj) => JSON.parse(JSON.stringify(obj))

/** 预置历史任务（三场景各一条已完成），让历史列表/统计卡片一打开就有数据。 */
function seedHistory() {
  for (const [scenario, snapshot] of Object.entries(BOM_SNAPSHOTS)) {
    const seeded = clone(snapshot)
    seeded.createdAt = '2026-08-27 10:00:00'
    seeded.finishedAt = '2026-08-27 10:00:07'
    tasks.set(seeded.taskId, seeded)
  }
}

function makeError(status, message) {
  const err = new Error(message)
  err.isAxiosError = true
  err.response = { data: { message }, status, statusText: 'ERROR', headers: {}, config: {} }
  return err
}

// ────────────────────────────────────────
//  路由分发
// ────────────────────────────────────────

function route(method, url, config) {
  const params = config.params || {}
  let m

  // ── S1 设计（mock）──
  if (method === 'get' && url === '/api/s1/design/tasks') {
    return { records: DESIGN_TASKS, total: DESIGN_TASKS.length, page: params.page || 1, size: params.size || 20 }
  }
  if (method === 'get' && (m = url.match(/^\/api\/s1\/design\/tasks\/([\w-]+)$/))) {
    const design = DESIGNS[m[1]]
    if (!design) throw makeError(404, `Design task not found: ${m[1]}`)
    return { status: 'ok', designTaskId: m[1], data: design }
  }

  // ── S3 审查（mock）──
  if (method === 'get' && (m = url.match(/^\/api\/s3\/review\/result\/([\w-]+)$/))) {
    const review = buildReviewResult(m[1])
    if (!review) throw makeError(404, `Review result not found: ${m[1]}`)
    return review
  }

  // ── S4 BOM ──
  if (method === 'post' && url === '/api/s4/bom/generate') {
    const body = typeof config.data === 'string' ? JSON.parse(config.data || '{}') : (config.data || {})
    const designTaskId = body.designTaskId || ''
    if (!designTaskId) throw makeError(400, 'designTaskId 不能为空')
    // 演示分级闸门拦截：designTaskId 以 BLOCK 开头 → 409 拦截
    if (/^BLOCK/i.test(designTaskId)) {
      throw makeError(409, '设计存在致命/严重审查违规，已拦截 BOM 生成（[critical] GD-001 接地电阻超标），请先完成整改并重新提交 S3 审查')
    }
    const snapshot = BOM_SNAPSHOTS[designTaskId] || BOM_SNAPSHOTS.D001
    const taskId = `mock-${Date.now().toString(36)}-${++taskSeq}`
    const task = clone(snapshot)
    task.taskId = taskId
    task.designTaskId = designTaskId
    task.projectId = body.projectId || task.projectId
    task.status = 'running'
    task.createdAt = now()
    tasks.set(taskId, task)
    // 模拟引擎异步计算：3 秒后置为 done
    setTimeout(() => {
      task.status = 'done'
      task.finishedAt = now()
    }, GENERATE_DURATION_MS)
    return { taskId, status: 'running' }
  }

  if (method === 'get' && url === '/api/s4/bom/history') {
    const list = [...tasks.values()].sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''))
    const page = Number(params.page) || 1
    const size = Number(params.size) || 20
    const records = list.slice((page - 1) * size, page * size)
      .map(({ items, processRequirements, fiberAllocation, reviewGate, ...slim }) => slim)
    return { records, total: list.length, page, size }
  }

  if (method === 'get' && (m = url.match(/^\/api\/s4\/bom\/([\w-]+)\/status$/))) {
    const task = tasks.get(m[1])
    if (!task) return { taskId: m[1], status: 'not_found' }
    const result = { taskId: task.taskId, status: task.status, createdAt: task.createdAt }
    if (task.status === 'done') {
      result.totalItems = task.totalQty
      result.totalCategories = task.totalCategories
      result.finishedAt = task.finishedAt
    }
    return result
  }

  if (method === 'get' && (m = url.match(/^\/api\/s4\/bom\/([\w-]+)\/full$/))) {
    const task = tasks.get(m[1])
    if (!task) throw makeError(404, 'task not found')
    return task
  }

  if (method === 'get' && (m = url.match(/^\/api\/s4\/bom\/([\w-]+)$/))) {
    const task = tasks.get(m[1])
    if (!task) throw makeError(404, 'task not found')
    const { processRequirements, fiberAllocation, reviewGate, ...detail } = task
    return detail
  }

  // ── 任务主线（mock）── S1 任务列表 / 流水线看板 / 设计-审查聚合
  if (method === 'get' && url === '/api/s4/bom/s1-tasks') {
    // D001/D002/D003 是演示场景码，映射为整数 id 便于前端选择器展示
    return [
      { id: 1, taskNo: 'DESIGN-YC-A001', taskName: '示范宏站（5G NR 3.5GHz）', projectId: 'PROJ-DEMO-01', status: 'completed' },
      { id: 2, taskNo: 'DESIGN-IND-B001', taskName: '示范室分（商业综合体）', projectId: 'PROJ-DEMO-02', status: 'completed' },
      { id: 3, taskNo: 'DESIGN-MIC-C001', taskName: '示范微站（步行街站群）', projectId: 'PROJ-DEMO-03', status: 'completed' },
    ]
  }

  if (method === 'get' && (m = url.match(/^\/api\/s4\/bom\/([\w-]+)\/design-review$/))) {
    const id = m[1]
    let realId = id
    let scene = id
    if (id === 'D001' || id === 'D002' || id === 'D003') {
      realId = { D001: '1', D002: '2', D003: '3' }[id]
    }
    const designSrc = DESIGNS[scene] || DESIGNS.D001
    const review = buildReviewResult(scene) || {}
    const design = {
      projectName: designSrc._meta?.description || '设计对象',
      projectId: designSrc._meta?.projectId || realId,
      taskNo: designSrc._meta?.designTaskId || '',
      taskName: designSrc._meta?.description || '',
      siteType: designSrc.site?.type || 'macro',
      deviceCount: (designSrc.devices || []).length,
      devices: (designSrc.devices || []).map((d, i) => ({
        deviceId: d.id || `DEV-${i+1}`,
        deviceName: d.name || d.model || '未命名',
        modelSpec: d.model || '',
        deviceType: d.type || 'unknown',
        qty: d.qty || 1,
      })),
    }
    // mock 数据本身不带 pipelines → 给演示管线，让工程量报表页面在 mock 下也能完整展示
    design.pipelines = [
      { pipelineId: 'PL-001', startSite: 'S-A', endSite: 'S-B', pipelineType: '直埋', fiberType: 'G.652D', lengthM: 320 },
      { pipelineId: 'PL-002', startSite: 'S-B', endSite: 'S-C', pipelineType: '管道', fiberType: 'G.652D', lengthM: 180 },
      { pipelineId: 'PL-003', startSite: 'S-C', endSite: 'S-D', pipelineType: '架空', fiberType: 'G.657A2', lengthM: 240 },
    ]
    design.pipelineCount = design.pipelines.length
    return {
      designTaskId: id,
      realId,
      taskNo: design.taskNo,
      design,
      review: {
        taskName: design.taskName,
        coverageRate: 95.0,
        reviewedAt: review.reviewedAt,
        result: review.result || 'approved',
        violations: review.summary?.error || 0,
        warnings: review.summary?.warning || 0,
        pending: review.summary?.pending || 0,
        totalCount: review.violationCount || 0,
        checks: (review.violations || []).map(v => ({
          rule: v.ruleId || '',
          name: v.ruleName || '',
          riskLevel: v.riskLevel || v.severity || 'approved',
          actualValue: v.actualValue || '',
          standardValue: v.standardValue || '',
        })),
      },
      fallback: false,
    }
  }

  // [S4-S1-迁移 2026-09-22] 工程量报表（mock）—— 复用设计-审查聚合并附加 bomItems
  if (method === 'get' && (m = url.match(/^\/api\/s4\/bom\/([\w-]+)\/volume-report$/))) {
    const id = m[1]
    const inner = route('get', `/api/s4/bom/${id}/design-review`, config)
    const bomSnap = BOM_SNAPSHOTS[id] || BOM_SNAPSHOTS.D001
    const bomItems = (bomSnap.items || []).map(it => ({
      siteId: it.siteId || '',
      installMethod: it.installMethod || '',
      materialName: it.materialName || '',
      spec: it.spec || '',
      qty: it.qty,
      unit: it.unit || '',
    }))
    return {
      designTaskId: id,
      realId: inner.realId,
      design: inner.design,
      bomItems,
      fallback: false,
    }
  }
  if (method === 'get' && (m = url.match(/^\/api\/s4\/bom\/([\w-]+)\/volume-report\/export$/))) {
    // mock 模式：直接抛错提示用户切到真实后端导出。
    // 避免在演示时给一个伪造 xlsx 让评委误以为功能完整
    throw makeError(503, '工程量报表 Excel 导出需要启用真实 S4 后端（前端 .env 设 VITE_USE_MOCK=false 并重启）')
  }

  // ── [S4-S1-迁移 §5.2 2026-09-22] FTTH 上传式（mock 仅给元数据，提示切真实后端） ──
  if (method === 'post' && url === '/api/s4/ftth/upload') {
    throw makeError(503, 'FTTH 交付物上传需要启用真实 S4 后端 + Python 引擎（前端 .env 设 VITE_USE_MOCK=false 并重启）')
  }
  if (method === 'get' && /^\\/api\\/s4\\/ftth\\/[\\w-]+\\/(download|validation|json)$/.test(url)) {
    throw makeError(503, 'FTTH 文件下载需要启用真实 S4 后端 + Python 引擎')
  }

  // ── 流水线概览（mock）──
  if (method === 'get' && url === '/api/pipeline/status') {
    return {
      pipeline: 'XA-202610 通信基建工程数智化设计与交付 (本地虚拟数据模式)',
      stages: [
        { id: 'S1', name: '智能辅助设计', status: 'online', taskCount: DESIGN_TASKS.length, url: '/api/s1/design/tasks' },
        { id: 'S3', name: '智能审查', status: 'online', taskCount: DESIGN_TASKS.length, feedbackCount: 0, url: '/api/s3/review/tasks' },
        { id: 'S4', name: '施工指令转化 (BOM)', status: 'online', taskCount: tasks.size, url: '/api/s4/bom/history', highlight: true },
        { id: 'S5', name: '施工监管', status: 'pending', taskCount: 0, url: '/api/s5/verify/tasks' },
      ],
      timestamp: now(),
    }
  }

  return undefined  // 未覆盖 → 404
}

function mockAdapter(config) {
  const method = (config.method || 'get').toLowerCase()
  const url = config.url || ''
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      try {
        const data = route(method, url, config)
        if (data === undefined) {
          reject(makeError(404, `MOCK 未覆盖: ${method.toUpperCase()} ${url}`))
        } else {
          resolve({ data, status: 200, statusText: 'OK', headers: {}, config })
        }
      } catch (e) {
        reject(e.isAxiosError ? e : makeError(500, e.message))
      }
    }, RESPONSE_DELAY_MS)
  })
}

export function isMockEnabled() {
  return import.meta.env.VITE_USE_MOCK === 'true'
}

export function setupMock() {
  seedHistory()
  axios.defaults.adapter = mockAdapter
  console.info(
    '%c[S4 mock] 前端本地虚拟数据模式已启用（免后端演示）— 数据来自真实 BOM 引擎快照；' +
    '联调后端时在 frontend/.env 设 VITE_USE_MOCK=false 并重启 npm run dev',
    'color:#409eff;font-weight:bold',
  )
}
