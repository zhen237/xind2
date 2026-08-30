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
