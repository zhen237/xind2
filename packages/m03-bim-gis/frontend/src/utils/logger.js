/**
 * logger — 统一日志工具
 *
 * 开发环境: 输出带标签的彩色日志到 console
 * 生产环境: 静默 (esbuild drop console 也会处理，这里做双保险)
 *
 * 用法:
 *   import { logger } from '@/utils/logger'
 *   logger.info('SiteManager', '站点已加载', siteCount)
 *   logger.warn('RequestCache', '缓存即将过期', key)
 *   logger.error('CesiumViewer', '初始化失败', error)
 */

const isDev = import.meta.env.DEV

const COLORS = {
  info: '#2563eb',
  warn: '#f59e0b',
  error: '#dc2626',
  debug: '#6b7280',
}

const TAGS = {
  info: '[INFO]',
  warn: '[WARN]',
  error: '[ERROR]',
  debug: '[DEBUG]',
}

/**
 * @param {'info'|'warn'|'error'|'debug'} level
 * @param {string} module - 模块名
 * @param {string} message - 日志消息
 * @param {*} [data] - 附加数据
 */
function log(level, module, message, data) {
  if (!isDev && level !== 'error') return

  const tag = TAGS[level]
  const color = COLORS[level]
  const timestamp = new Date().toISOString().split('T')[1].replace('Z', '')

  const prefix = `%c${timestamp} ${tag} [${module}]`
  const style = `color:${color};font-weight:bold`

  if (data !== undefined) {
    console[level === 'debug' ? 'log' : level](prefix, style, message, data)
  } else {
    console[level === 'debug' ? 'log' : level](prefix, style, message)
  }
}

export const logger = {
  info: (module, message, data) => log('info', module, message, data),
  warn: (module, message, data) => log('warn', module, message, data),
  error: (module, message, data) => log('error', module, message, data),
  debug: (module, message, data) => log('debug', module, message, data),
}

export default logger
