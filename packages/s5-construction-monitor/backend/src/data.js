/**
 * S5 数字孪生种子数据。
 * 从 twin-csharp/TwinCsharp/Services/InMemoryTwinDataService.cs 移植，
 * 数据结构/字段命名/生成规则保持一致（camelCase 输出）。
 * 确定性伪随机（mulberry32 + 固定种子），保证每次启动数据一致。
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// 核验任务落盘目录：backend/data/（gitignore 已排除）
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.resolve(__dirname, '../data')
const VERIFY_FILE = path.join(DATA_DIR, 'verify-tasks.json')

/** 简单确定性 PRNG（等价替代 .NET Random(20260831)，数据不必逐位一致） */
function mulberry32(seed) {
  let a = seed >>> 0
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** 生成本地时间 ISO 字符串（无时区后缀）。
 *  不能用 toISOString()——那是 UTC，会使"接收时间/告警时间"比北京时间早 8 小时。
 *  先按本地时区偏移回拨再格式化，形状仍为 YYYY-MM-DDTHH:mm:ss，前端零改动。 */
const iso = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000)
  .toISOString().replace(/\.\d{3}Z$/, '')

function seedDevices() {
  const rnd = mulberry32(20260831)
  const baseTime = new Date(2026, 0, 1, 8, 0, 0) // 2026-01-01 08:00:00
  const types = ['塔吊', '升降机', '摄像头', '传感器', '配电箱']
  const stations = ['A区', 'B区', 'C区']
  const list = []

  for (let i = 1; i <= 12; i++) {
    // status: i%5==0 → 2(故障), i%3==0 → 0(离线), 其余 1(在线)
    const status = i % 5 === 0 ? 2 : i % 3 === 0 ? 0 : 1
    const type = types[(i - 1) % types.length]
    const code = `DEV-${String(i).padStart(3, '0')}`
    const dayMs = i * 24 * 60 * 60 * 1000

    list.push({
      id: i,
      deviceCode: code,
      deviceName: `${type}-${String(i).padStart(3, '0')}`,
      deviceType: type,
      stationCode: stations[(i - 1) % stations.length],
      installTime: iso(new Date(baseTime.getTime() + dayMs)),
      status,
      manufacturer: '示范厂商',
      model: `X-${1000 + i}`,
      createTime: iso(new Date(baseTime.getTime() + dayMs)),
      twin: {
        temperature: Math.round((20 + rnd() * 35) * 10) / 10,
        load: Math.round(rnd() * 100 * 10) / 10,
        runtimeMinutes: Math.floor(rnd() * 50000),
        lastSync: iso(new Date(baseTime.getTime() + i * 37 * 60 * 1000)),
        health: status === 2 ? Math.floor(rnd() * 40) + 10 : Math.floor(rnd() * 39) + 60
      }
    })
  }
  return list
}

function seedAlerts(devices) {
  const baseTime = new Date(2026, 7, 31, 9, 0, 0) // 2026-08-31 09:00:00
  const contents = ['塔吊力矩超限', '升降机门联锁异常', '摄像头离线', '传感器数据中断', '配电箱温度偏高']
  // 处置建议规则库（按告警类型静态映射，属「规则建议」而非真实已执行的处置记录）
  const SUGGESTIONS = {
    '塔吊力矩超限': '立即停止吊装作业，核查吊重与工作幅度，确认力矩限制器标定有效后方可复位作业',
    '升降机门联锁异常': '暂停使用该升降机，检查门联锁开关、限位及线路，排除故障并试运行确认安全',
    '摄像头离线': '检查摄像机供电与网络链路，尝试重启设备，确认录像与存储恢复正常',
    '传感器数据中断': '检查传感器供电与信号线路，重启采集单元，必要时现场校准后恢复数据采集',
    '配电箱温度偏高': '停检散热与负载情况，红外测温排查过热点，清理积尘、确认通风后恢复送电'
  }
  const list = []

  for (let i = 1; i <= 8; i++) {
    const dev = devices[(i - 1) % devices.length]
    const hourMs = i * 60 * 60 * 1000
    const content = contents[(i - 1) % contents.length]
    list.push({
      id: i,
      deviceId: dev.id,
      deviceCode: dev.deviceCode,
      alertContent: content,
      level: i % 4 === 0 ? 3 : i % 2 === 0 ? 2 : 1,
      status: i <= 5 ? 0 : 1,
      source: 'S5-施工监测',
      orderNo: `WO-${2026000 + i}`,
      createTime: iso(new Date(baseTime.getTime() + hourMs)),
      updateTime: i <= 5 ? null : iso(new Date(baseTime.getTime() + (i + 1) * 60 * 60 * 1000)),
      // 规则库处置建议（静态映射，非真实处置记录）
      suggestion: SUGGESTIONS[content] || '请结合现场情况排查，必要时按应急预案处置',
      suggestionNote: '规则建议'
    })
  }
  return list
}

const devices = seedDevices()
const alerts = seedAlerts(devices)

/** 启动时从磁盘载入 S4 推送的核验任务（重启不丢）；损坏/缺失只告警并以空列表启动 */
function loadVerifyTasks() {
  try {
    if (existsSync(VERIFY_FILE)) {
      const raw = JSON.parse(readFileSync(VERIFY_FILE, 'utf8'))
      if (Array.isArray(raw)) return raw
      console.warn('[S5] verify-tasks.json 内容非数组，忽略并以空列表启动')
    }
  } catch (e) {
    console.warn(`[S5] 读取 verify-tasks.json 失败（以空列表启动）: ${e?.message || e}`)
  }
  return []
}

/** 每次变更后同步写盘（文件小，writeFileSync 足够） */
function persistVerifyTasks() {
  try {
    if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true })
    writeFileSync(VERIFY_FILE, JSON.stringify(verifyTasks, null, 2), 'utf8')
  } catch (e) {
    console.warn(`[S5] 写入 verify-tasks.json 失败: ${e?.message || e}`)
  }
}

const verifyTasks = loadVerifyTasks()

/** 聚合看板数据（对齐 DashboardDto） */
export function getDashboard() {
  const online = devices.filter((d) => d.status === 1).length
  const offline = devices.filter((d) => d.status === 0).length
  const fault = devices.filter((d) => d.status === 2).length

  const alertByLevel = {
    提示: alerts.filter((a) => a.level === 1).length,
    警告: alerts.filter((a) => a.level === 2).length,
    严重: alerts.filter((a) => a.level === 3).length
  }

  const deviceTypeDistribution = {}
  devices.forEach((d) => {
    const key = d.deviceType ?? '未知'
    deviceTypeDistribution[key] = (deviceTypeDistribution[key] ?? 0) + 1
  })

  return {
    totalDevices: devices.length,
    onlineCount: online,
    offlineCount: offline,
    faultCount: fault,
    alertTotal: alerts.length,
    alertActive: alerts.filter((a) => a.status === 0).length,
    alertByLevel,
    deviceTypeDistribution,
    recentAlerts: shiftAlertTimes(alerts)
      .sort((a, b) => b.createTime.localeCompare(a.createTime))
      .slice(0, 5)
  }
}

export const getDevices = () => devices

export const getDevice = (code) => devices.find((d) => d.deviceCode === code) ?? null

/** 告警时间相对当前时间的偏移分钟数（模拟实时：3~52 分钟前） */
const ALERT_TIME_OFFSETS = [3, 10, 17, 24, 31, 38, 45, 52]

/** 模拟实时告警：每次请求把告警时间映射到"当前时间的几分钟前" */
function shiftAlertTimes(list) {
  const now = Date.now()
  list.forEach((a, i) => {
    a.createTime = iso(new Date(now - ALERT_TIME_OFFSETS[i % ALERT_TIME_OFFSETS.length] * 60 * 1000))
  })
  return list
}

/** 告警列表（支持 level / status / deviceCode 过滤，时间实时偏移） */
export const getAlerts = ({ level, status, deviceCode } = {}) =>
  shiftAlertTimes(alerts).filter((a) => {
    if (level !== undefined && a.level !== Number(level)) return false
    if (status !== undefined && a.status !== Number(status)) return false
    if (deviceCode && a.deviceCode !== deviceCode) return false
    return true
  })

/** 接收 S4 推送的 BOM 施工指令（与 S4 S5NotifyService 契约一致），内存落库供前端展示 */
export function addVerifyTask(input = {}) {
  const task = {
    id: verifyTasks.length + 1,
    bomTaskId: input.bomTaskId ?? null,
    designTaskId: input.designTaskId ?? null,
    projectId: input.projectId ?? null,
    projectName: input.projectName ?? '',
    stats: input.stats && typeof input.stats === 'object' ? input.stats : {},
    receivedTime: iso(new Date())
  }
  verifyTasks.unshift(task) // 最新在前
  persistVerifyTasks() // 落盘，重启不丢
  return task
}

/** 返回已接收的 BOM 核验任务列表（最新在前） */
export const getVerifyTasks = () => verifyTasks
