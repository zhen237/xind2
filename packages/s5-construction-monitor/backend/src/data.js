/**
 * S5 数字孪生种子数据。
 * 从 twin-csharp/TwinCsharp/Services/InMemoryTwinDataService.cs 移植，
 * 数据结构/字段命名/生成规则保持一致（camelCase 输出）。
 * 确定性伪随机（mulberry32 + 固定种子），保证每次启动数据一致。
 */

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

/** 生成 ISO 时间字符串（无时区，对齐 System.Text.Json 的 DateTime 输出） */
const iso = (d) => d.toISOString().replace(/\.\d{3}Z$/, '')

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
  const list = []

  for (let i = 1; i <= 8; i++) {
    const dev = devices[(i - 1) % devices.length]
    const hourMs = i * 60 * 60 * 1000
    list.push({
      id: i,
      deviceId: dev.id,
      deviceCode: dev.deviceCode,
      alertContent: contents[(i - 1) % contents.length],
      level: i % 4 === 0 ? 3 : i % 2 === 0 ? 2 : 1,
      status: i <= 5 ? 0 : 1,
      source: 'S5-施工监测',
      orderNo: `WO-${2026000 + i}`,
      createTime: iso(new Date(baseTime.getTime() + hourMs)),
      updateTime: i <= 5 ? null : iso(new Date(baseTime.getTime() + (i + 1) * 60 * 60 * 1000))
    })
  }
  return list
}

const devices = seedDevices()
const alerts = seedAlerts(devices)
const verifyTasks = []

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
  return task
}

/** 返回已接收的 BOM 核验任务列表（最新在前） */
export const getVerifyTasks = () => verifyTasks
