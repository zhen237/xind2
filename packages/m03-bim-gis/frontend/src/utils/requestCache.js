/**
 * 请求缓存管理器
 * 减少重复请求，提升响应速度
 */

import { logger } from '@/utils/logger'

class RequestCache {
  constructor(defaultTTL = 5 * 60 * 1000, maxSize = 200) {
    this.cache = new Map()
    this.defaultTTL = defaultTTL // 默认5分钟
    this.maxSize = maxSize       // 最大缓存条目数，防止内存泄漏
  }

  /**
   * 获取缓存数据
   * @param {string} key - 缓存键
   * @returns {Object|null}
   */
  get(key) {
    const item = this.cache.get(key)
    if (!item) return null

    // 检查是否过期
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key)
      return null
    }

    return item.data
  }

  /**
   * 设置缓存
   * @param {string} key - 缓存键
   * @param {any} data - 数据
   * @param {number} [ttl] - 过期时间（毫秒）
   */
  set(key, data, ttl) {
    // LRU 淘汰：超过上限时删除最旧的条目
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const oldestKey = this.cache.keys().next().value
      this.cache.delete(oldestKey)
    }
    this.cache.set(key, {
      data: JSON.parse(JSON.stringify(data)), // 深拷贝
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL
    })
  }

  /**
   * 检查缓存是否存在且未过期
   * @param {string} key
   * @returns {boolean}
   */
  has(key) {
    return this.get(key) !== null
  }

  /**
   * 删除缓存
   * @param {string} key
   */
  delete(key) {
    this.cache.delete(key)
  }

  /**
   * 清空所有缓存
   */
  clear() {
    this.cache.clear()
  }

  /**
   * 获取缓存大小
   * @returns {number}
   */
  get size() {
    return this.cache.size
  }

  /**
   * 获取缓存统计信息
   * @returns {Object}
   */
  getStats() {
    return {
      size: this.cache.size,
      entries: Array.from(this.cache.entries()).map(([key, value]) => ({
        key,
        age: Date.now() - value.timestamp,
        ttl: value.ttl
      }))
    }
  }
}

// 导出单例
export const requestCache = new RequestCache(5 * 60 * 1000)

/**
 * 带缓存的请求函数
 * @param {string} key - 缓存键
 * @param {Function} requestFn - 请求函数
 * @param {number} [ttl] - 过期时间
 * @returns {Promise<any>}
 */
export async function cachedRequest(key, requestFn, ttl) {
  // 尝试从缓存获取
  const cached = requestCache.get(key)
  if (cached) {
    logger.debug('RequestCache', '使用缓存', key)
    return cached
  }

  // 执行请求
  logger.debug('RequestCache', '执行请求', key)
  const data = await requestFn()
  
  // 存入缓存
  requestCache.set(key, data, ttl)
  
  return data
}

/**
 * 失效缓存
 * @param {string} key 
 */
export function invalidateCache(key) {
  requestCache.delete(key)
  logger.debug('RequestCache', '缓存已失效', key)
}

/**
 * 失效所有缓存
 */
export function invalidateAllCache() {
  requestCache.clear()
  logger.debug('RequestCache', '所有缓存已清除')
}
