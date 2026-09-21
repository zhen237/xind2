/**
 * DeepSeek AI 接入（OpenAI 兼容协议）。
 * - Key 只从环境变量 DEEPSEEK_API_KEY 读取（backend/.env，已 gitignore，不入库）
 * - 前端永不直接持有 Key，一律经 POST /api/s5/ai/chat 代理
 * - 非流式：一次请求一次返回（demo 场景够用，流式可后续升级 SSE）
 */
import { getDashboard, getDevices, getAlerts } from './data.js'

const BASE_URL = process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com/chat/completions'
const MODEL = process.env.DEEPSEEK_MODEL || 'deepseek-chat'
const TIMEOUT_MS = 60000

/** 构造 system prompt：把 S5 实时看板/设备/告警摘要注入上下文，供监管数据问答 */
export function buildSystemPrompt() {
  const dash = getDashboard()
  const devices = getDevices()
  const alerts = getAlerts()

  const levelText = { 1: '提示', 2: '警告', 3: '严重' }
  const statusText = { 0: '离线', 1: '在线', 2: '故障' }

  const deviceLines = devices.map(
    (d) =>
      `- ${d.deviceCode} ${d.deviceName}（${d.deviceType}，${d.stationCode}区），状态=${statusText[d.status] ?? d.status}` +
      `，温度${d.twin?.temperature ?? '-'}℃，负载${d.twin?.load ?? '-'}%，健康度${d.twin?.health ?? '-'}`
  )

  const alertLines = alerts.slice(0, 8).map(
    (a) => `- [${levelText[a.level] ?? a.level}] ${a.alertContent}，设备 ${a.deviceCode}，状态=${a.status === 0 ? '待处理' : '已处理'}，时间 ${a.createTime}`
  )

  return [
    '你是 S5 施工智能监管系统的 AI 助手，服务于施工监管数字孪生平台。请用简洁中文回答。',
    `当前时间：${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}。`,
    '以下是系统实时数据快照（可能略有滞后），回答设备/告警/看板相关问题时请以这份数据为准；数据里查不到的就如实说明，不要编造：',
    `【看板】设备总数 ${dash.totalDevices}，在线 ${dash.onlineCount}，离线 ${dash.offlineCount}，故障 ${dash.faultCount}；告警总数 ${dash.alertTotal}，未处理 ${dash.alertActive}（提示 ${dash.alertByLevel?.['提示'] ?? 0}、警告 ${dash.alertByLevel?.['警告'] ?? 0}、严重 ${dash.alertByLevel?.['严重'] ?? 0}）。`,
    '【设备】' + (deviceLines.length ? deviceLines.join('\n') : '（暂无）'),
    '【最近告警】' + (alertLines.length ? alertLines.join('\n') : '（暂无）')
  ].join('\n')
}

/** 调 DeepSeek Chat Completions，返回 { reply, usage }；失败抛带 status 的 Error */
export async function chatDeepSeek(messages) {
  const key = process.env.DEEPSEEK_API_KEY
  if (!key) {
    const err = new Error('后端未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写后重启后端')
    err.status = 503
    throw err
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

  let resp
  try {
    resp = await fetch(BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key}`
      },
      body: JSON.stringify({
        model: MODEL,
        messages,
        temperature: 0.7,
        stream: false
      }),
      signal: controller.signal
    })
  } catch (e) {
    const err = new Error(e.name === 'AbortError' ? 'DeepSeek 请求超时，请稍后重试' : `无法连接 DeepSeek 服务: ${e.message}`)
    err.status = 502
    throw err
  } finally {
    clearTimeout(timer)
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const body = await resp.json()
      if (body?.error?.message) detail += `: ${body.error.message}`
    } catch {}
    const err = new Error(`DeepSeek 接口错误：${detail}`)
    err.status = 502
    throw err
  }

  const data = await resp.json()
  const reply = data?.choices?.[0]?.message?.content ?? ''
  if (!reply) {
    const err = new Error('DeepSeek 返回内容为空')
    err.status = 502
    throw err
  }
  return { reply, usage: data.usage }
}
