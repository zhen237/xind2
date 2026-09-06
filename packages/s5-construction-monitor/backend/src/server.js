/**
 * S5 数字孪生后端（Node.js 版）。
 * 接口契约与 twin-csharp 一致：/api/s5/*，端口 8091，CORS 仅放行 http://localhost:5191。
 * 启动：npm install && npm start
 * AI 端点（/api/s5/ai/chat）：仅本 Node 版提供（twin-csharp 不同步为已知限制），
 * DeepSeek Key 从 backend/.env 读取（已 gitignore，不入库）。
 */
import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import { getDashboard, getDevices, getDevice, getAlerts } from './data.js'
import { buildSystemPrompt, chatDeepSeek } from './deepseek.js'

const app = express()
const PORT = process.env.PORT || 8091

// CORS：仅放行 S5 前端（与 C# 版一致）
app.use(
  cors({
    origin: 'http://localhost:5191'
  })
)
app.use(express.json())

// ===== S5 数字孪生 API =====

/** 健康检查（S5 分支整改验收端点） */
app.get('/api/s5/health', (_req, res) => {
  res.json({ status: 'ok', module: 's5', time: new Date().toISOString() })
})

/** 施工监测看板聚合数据 */
app.get('/api/s5/dashboard', (_req, res) => {
  res.json(getDashboard())
})

/** 设备列表 */
app.get('/api/s5/devices', (_req, res) => {
  res.json(getDevices())
})

/** 单个设备（含孪生状态），不存在返回 404 */
app.get('/api/s5/devices/:code', (req, res) => {
  const device = getDevice(req.params.code)
  if (!device) {
    return res.status(404).json({ code: 404, message: `设备不存在: ${req.params.code}` })
  }
  res.json(device)
})

/** 告警列表（支持 level / status / deviceCode 过滤） */
app.get('/api/s5/alerts', (req, res) => {
  const { level, status, deviceCode } = req.query
  res.json(
    getAlerts({
      level: level !== undefined ? Number(level) : undefined,
      status: status !== undefined ? Number(status) : undefined,
      deviceCode
    })
  )
})

/** AI 助手对话（DeepSeek 代理，Key 仅存于后端 .env，前端不接触） */
app.post('/api/s5/ai/chat', async (req, res) => {
  try {
    const { message, history } = req.body ?? {}

    if (typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({ code: 400, message: 'message 不能为空' })
    }
    if (message.length > 2000) {
      return res.status(400).json({ code: 400, message: 'message 过长（最多 2000 字）' })
    }

    // 校验并裁剪历史（只带最近 6 条，防上下文过长）
    const valid = (m) =>
      m && typeof m === 'object' &&
      (m.role === 'user' || m.role === 'assistant') &&
      typeof m.content === 'string' && m.content.trim()
    const recent = Array.isArray(history) ? history.filter(valid).slice(-6) : []
    const trimmed = recent.map((m) => ({ role: m.role, content: m.content.trim().slice(0, 1000) }))

    const messages = [{ role: 'system', content: buildSystemPrompt() }, ...trimmed, { role: 'user', content: message.trim() }]

    const { reply, usage } = await chatDeepSeek(messages)
    res.json({ reply, usage, model: process.env.DEEPSEEK_MODEL || 'deepseek-chat' })
  } catch (e) {
    res.status(e.status ?? 500).json({ code: e.status ?? 500, message: e.message ?? 'AI 服务内部错误' })
  }
})

app.listen(PORT, () => {
  console.log(`[S5] 数字孪生后端已启动: http://localhost:${PORT}`)
  console.log(`[S5] 接口: /api/s5/dashboard | /api/s5/devices | /api/s5/devices/:code | /api/s5/alerts`)
})
