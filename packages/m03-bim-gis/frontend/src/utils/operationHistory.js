/**
 * 操作历史管理器
 * 支持撤销(Undo)和重做(Redo)功能
 */

import { logger } from '@/utils/logger'

export class OperationHistory {
  /**
   * @param {number} maxSteps - 最大历史记录数
   */
  constructor(maxSteps = 50) {
    this.history = []
    this.currentIndex = -1
    this.maxSteps = maxSteps
    this.listeners = []
  }

  /**
   * 添加新状态到历史
   * @param {Object} state - 状态快照
   */
  push(state) {
    // 深拷贝状态
    const snapshot = JSON.parse(JSON.stringify(state))
    
    // 删除当前行之后的历史
    this.history = this.history.slice(0, this.currentIndex + 1)
    this.history.push(snapshot)
    
    // 限制历史记录数量
    if (this.history.length > this.maxSteps) {
      this.history.shift()
    } else {
      this.currentIndex++
    }
    
    // 通知监听器
    this.notifyListeners('push', snapshot)
  }

  /**
   * 撤销操作
   * @returns {Object|null} 上一个状态
   */
  undo() {
    if (this.currentIndex > 0) {
      this.currentIndex--
      const state = JSON.parse(JSON.stringify(this.history[this.currentIndex]))
      this.notifyListeners('undo', state)
      return state
    }
    return null
  }

  /**
   * 重做操作
   * @returns {Object|null} 下一个状态
   */
  redo() {
    if (this.currentIndex < this.history.length - 1) {
      this.currentIndex++
      const state = JSON.parse(JSON.stringify(this.history[this.currentIndex]))
      this.notifyListeners('redo', state)
      return state
    }
    return null
  }

  /**
   * 是否可以撤销
   * @returns {boolean}
   */
  get canUndo() {
    return this.currentIndex > 0
  }

  /**
   * 是否可以重做
   * @returns {boolean}
   */
  get canRedo() {
    return this.currentIndex < this.history.length - 1
  }

  /**
   * 获取历史长度
   * @returns {number}
   */
  get length() {
    return this.history.length
  }

  /**
   * 获取当前状态索引
   * @returns {number}
   */
  get index() {
    return this.currentIndex
  }

  /**
   * 清空历史
   */
  clear() {
    this.history = []
    this.currentIndex = -1
    this.notifyListeners('clear', null)
  }

  /**
   * 注册监听器
   * @param {Function} listener - 回调函数 (event, state) => void
   */
  subscribe(listener) {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  /**
   * 通知监听器
   * @param {string} event - 事件类型
   * @param {Object} state - 状态
   */
  notifyListeners(event, state) {
    this.listeners.forEach(listener => listener(event, state))
  }

  /**
   * 序列化（用于持久化）
   * @returns {string}
   */
  serialize() {
    return JSON.stringify({
      history: this.history,
      currentIndex: this.currentIndex,
      maxSteps: this.maxSteps
    })
  }

  /**
   * 反序列化
   * @param {string} data - JSON字符串
   * @returns {OperationHistory}
   */
  static deserialize(data) {
    try {
      const parsed = JSON.parse(data)
      const instance = new OperationHistory(parsed.maxSteps)
      instance.history = parsed.history
      instance.currentIndex = parsed.currentIndex
      return instance
    } catch (e) {
      logger.error('OperationHistory', '反序列化操作历史失败', e)
      return new OperationHistory()
    }
  }
}

/**
 * 创建操作历史管理器的便捷函数
 * @param {number} maxSteps - 最大步骤数
 * @returns {OperationHistory}
 */
export function createOperationHistory(maxSteps = 50) {
  return new OperationHistory(maxSteps)
}
