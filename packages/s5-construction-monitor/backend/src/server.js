/**
 * S5 数字孪生后端（Node.js 版）。
 * 接口契约与 twin-csharp 一致：/api/s5/*，端口 8092，CORS 仅放行 http://localhost:5191。
 * 启动：npm install && npm start
 */
import express from 'express'
import cors from 'cors'
import { getDashboard, getDevices, getDevice, getAlerts } from './data.js'

const app = express()
const PORT = process.env.PORT || 8092

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

app.listen(PORT, () => {
  console.log(`[S5] 数字孪生后端已启动: http://localhost:${PORT}`)
  console.log(`[S5] 接口: /api/s5/dashboard | /api/s5/devices | /api/s5/devices/:code | /api/s5/alerts`)
})
