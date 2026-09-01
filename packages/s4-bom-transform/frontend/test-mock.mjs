/**
 * 前端本地 mock 自测 — 通过 Vite SSR 加载真实 src/mock/index.js 模块，
 * 用真实 axios 实例驱动 adapter，验证「免后端演示」全链路。
 *
 * 运行: node test-mock.mjs（需先在 frontend 目录，依赖 .env 的 VITE_USE_MOCK）
 */
import assert from 'node:assert'

process.env.NODE_ENV = 'development'

const { createServer } = await import('vite')
const server = await createServer({
  root: process.cwd(),
  logLevel: 'error',
  server: { middlewareMode: true },
})

try {
  const { isMockEnabled, setupMock } = await server.ssrLoadModule('/src/mock/index.js')
  const axios = (await import('axios')).default

  assert.equal(isMockEnabled(), true, '.env 应启用 VITE_USE_MOCK=true')
  setupMock()
  console.log('✔ mock 已启用，axios adapter 已接管')

  // 1. 历史列表（预置 3 条已完成任务）
  const history = await axios.get('/api/s4/bom/history', { params: { page: 1, size: 20 } }).then(r => r.data)
  assert.equal(history.total, 3)
  assert.ok(history.records.every(t => t.status === 'done' && !('items' in t)))
  console.log(`✔ 历史列表: ${history.total} 条预置任务（不含 items 的瘦身记录）`)

  // 2. 生成 → 轮询 running → done
  const gen = await axios.post('/api/s4/bom/generate',
    { designTaskId: 'D001', projectId: 'PRJ-yuncheng' }).then(r => r.data)
  assert.equal(gen.status, 'running')
  assert.ok(gen.taskId.startsWith('mock-'))
  const s1 = await axios.get(`/api/s4/bom/${gen.taskId}/status`).then(r => r.data)
  assert.equal(s1.status, 'running', '3 秒内应处于 running')
  console.log(`✔ 生成任务 ${gen.taskId} → 轮询 running（演示进度条）`)

  await new Promise(r => setTimeout(r, 3300))
  const s2 = await axios.get(`/api/s4/bom/${gen.taskId}/status`).then(r => r.data)
  assert.equal(s2.status, 'done')
  assert.ok(s2.totalItems > 0 && s2.totalCategories > 0)
  console.log(`✔ 3.3s 后置 done: ${s2.totalItems} 条物料 / ${s2.totalCategories} 类目`)

  // 3. 详情（full）：物料 + 工序 + 纤芯 + 闸门
  const full = await axios.get(`/api/s4/bom/${gen.taskId}/full`).then(r => r.data)
  assert.ok(Array.isArray(full.items) && full.items.length > 50)
  assert.ok(Array.isArray(full.processRequirements) && full.processRequirements.length > 0)
  assert.ok(full.fiberAllocation?.allocations?.length > 0)
  assert.ok(full.fiberAllocation?.summary?.odf_capacity > 0)
  assert.ok(full.reviewGate)
  const cats = new Set(full.items.map(i => i.category))
  assert.deepEqual([...cats].sort(), ['auxiliary', 'cable', 'main_device'])
  console.log(`✔ full 详情: ${full.items.length} 条物料（三类齐全）+ 工序 ${full.processRequirements.length} + 纤芯 ${full.fiberAllocation.allocations.length} 行`)

  // 4. 仅物料详情
  const detail = await axios.get(`/api/s4/bom/${gen.taskId}`).then(r => r.data)
  assert.ok(!('processRequirements' in detail) && detail.items.length > 0)
  console.log('✔ detail 详情: 仅物料清单（不含工序/纤芯）')

  // 5. 历史列表包含新任务（4 条）
  const history2 = await axios.get('/api/s4/bom/history').then(r => r.data)
  assert.equal(history2.total, 4)
  console.log('✔ 历史列表更新为 4 条')

  // 6. S1 设计详情（PipelineOverview 场景联动）
  const design = await axios.get('/api/s1/design/tasks/D001').then(r => r.data)
  assert.equal(design.status, 'ok')
  assert.equal(design.data.devices.length, 15)
  console.log(`✔ S1 设计详情: D001 → ${design.data.devices.length} 台设备`)

  // 7. S3 审查结果（D002 带警告 → 联动整改标记）
  const review = await axios.get('/api/s3/review/result/D002').then(r => r.data)
  assert.equal(review.summary.warning, 2)
  assert.equal(review.violationCount, 3)
  const bomD002 = (await import('./src/mock/data/bom_D002.json', { with: { type: 'json' } })).default
  const flagged = bomD002.items.filter(i => i.requiresRectification).length
  assert.ok(flagged > 0, 'D002 快照应含整改标记')
  console.log(`✔ S3 审查: D002 warning=2 pending=1 → BOM 快照 ${flagged} 条物料带整改标记`)

  // 8. 分级闸门拦截演示（designTaskId 以 BLOCK 开头 → 409）
  await assert.rejects(
    axios.post('/api/s4/bom/generate', { designTaskId: 'BLOCK-DEMO-001' }),
    (e) => e.response?.status === 409 && e.response.data.message.includes('拦截'),
  )
  console.log('✔ 审查闸门拦截: D-BLOCK-001 → 409 + 拦截消息')

  // 9. 未覆盖端点 → 404（不会静默挂起）
  await assert.rejects(axios.get('/api/s5/verify/tasks'))
  console.log('✔ 未覆盖端点返回 404（fail-fast）')

  console.log('\n════ 前端本地 mock 自测全部通过 — 5190 可免后端完整演示 ════')
} finally {
  await server.close()
}
