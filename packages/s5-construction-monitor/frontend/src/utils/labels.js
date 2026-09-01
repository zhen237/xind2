// 枚举标签映射（与 twin-csharp 后端约定一致）

export const deviceStatusLabel = (s) => ({ 0: '离线', 1: '在线', 2: '故障' }[s] ?? '未知')
export const deviceStatusType = (s) => ({ 0: 'info', 1: 'success', 2: 'danger' }[s] ?? 'info')

export const alertLevelLabel = (l) => ({ 1: '提示', 2: '警告', 3: '严重' }[l] ?? '未知')
export const alertLevelType = (l) => ({ 1: 'info', 2: 'warning', 3: 'danger' }[l] ?? 'info')

export const alertStatusLabel = (s) => ({ 0: '未处理', 1: '已处理' }[s] ?? '未知')
export const alertStatusType = (s) => ({ 0: 'warning', 1: 'success' }[s] ?? 'info')

export const fmt = (v) => (v == null ? '-' : String(v))
export const fmtTime = (v) => (v == null ? '-' : new Date(v).toLocaleString('zh-CN'))
