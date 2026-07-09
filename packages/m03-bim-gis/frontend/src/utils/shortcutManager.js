/**
 * 快捷键管理器
 * 提供统一的快捷键注册和使用功能
 */

import { logger } from '@/utils/logger'

export class ShortcutManager {
  constructor() {
    this.shortcuts = new Map()
    this.modifiers = {
      ctrl: false,
      alt: false,
      shift: false
    }
  }

  /**
   * 注册快捷键
   * @param {string} combination - 组合键，如 'Ctrl+Enter'
   * @param {Function} handler - 处理函数
   * @param {Object} [options] - 选项
   * @param {boolean} [options.preventDefault=true] - 是否阻止默认行为
   * @param {boolean} [options.ignoreInput=false] - 是否在输入框聚焦时忽略
   */
  register(combination, handler, options = {}) {
    const {
      preventDefault = true,
      ignoreInput = false
    } = options

    this.shortcuts.set(combination, {
      handler,
      preventDefault,
      ignoreInput
    })
  }

  /**
   * 注销快捷键
   * @param {string} combination 
   */
  unregister(combination) {
    this.shortcuts.delete(combination)
  }

  /**
   * 初始化事件监听
   */
  init() {
    this._boundKeyDown = this.handleKeyDown.bind(this)
    this._boundKeyUp = this.handleKeyUp.bind(this)
    document.addEventListener('keydown', this._boundKeyDown)
    document.addEventListener('keyup', this._boundKeyUp)
  }

  /**
   * 销毁
   */
  destroy() {
    if (this._boundKeyDown) {
      document.removeEventListener('keydown', this._boundKeyDown)
      this._boundKeyDown = null
    }
    if (this._boundKeyUp) {
      document.removeEventListener('keyup', this._boundKeyUp)
      this._boundKeyUp = null
    }
  }

  /**
   * 处理按键按下
   * @param {KeyboardEvent} e 
   */
  handleKeyDown(e) {
    // 更新修饰键状态
    this.modifiers.ctrl = e.ctrlKey || e.metaKey
    this.modifiers.alt = e.altKey
    this.modifiers.shift = e.shiftKey

    // 检查是否在输入框中
    const isInInput = this.isInInputElement(e.target)
    
    // 构建组合键字符串
    const combination = this.buildCombination(e)
    
    if (!combination) return

    const shortcut = this.shortcuts.get(combination)
    if (!shortcut) return

    // 如果在输入框中且设置了忽略，则跳过
    if (isInInput && shortcut.ignoreInput) return

    // 执行处理函数
    if (shortcut.preventDefault) {
      e.preventDefault()
    }
    shortcut.handler(e)
  }

  /**
   * 处理按键释放
   * @param {KeyboardEvent} e 
   */
  handleKeyUp(e) {
    this.modifiers.ctrl = e.ctrlKey || e.metaKey
    this.modifiers.alt = e.altKey
    this.modifiers.shift = e.shiftKey
  }

  /**
   * 检查是否在输入元素中
   * @param {HTMLElement} target 
   * @returns {boolean}
   */
  isInInputElement(target) {
    if (!target) return false
    
    const tagName = target.tagName.toLowerCase()
    if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
      return true
    }
    
    return target.isContentEditable
  }

  /**
   * 构建组合键字符串
   * @param {KeyboardEvent} e 
   * @returns {string|null}
   */
  buildCombination(e) {
    const parts = []
    
    if (this.modifiers.ctrl) parts.push('Ctrl')
    if (this.modifiers.alt) parts.push('Alt')
    if (this.modifiers.shift) parts.push('Shift')
    
    // 主键
    let key = e.key
    if (key.length === 1) {
      key = key.toUpperCase()
    } else if (key === 'Enter') {
      key = 'Enter'
    } else if (key === 'z' || key === 'y') {
      // Ctrl+Z/Y 不需要大写
      key = key.toLowerCase()
    }
    
    if (parts.length > 0 || key !== 'Enter') {
      parts.push(key)
    }
    
    return parts.length > 0 ? parts.join('+') : null
  }

  /**
   * 获取所有注册的快捷键
   * @returns {Array}
   */
  getAllShortcuts() {
    return Array.from(this.shortcuts.entries()).map(([key, value]) => ({
      combination: key,
      hasHandler: typeof value.handler === 'function'
    }))
  }

  /**
   * 显示快捷键帮助
   * @param {Function} showMessage - 显示消息函数
   */
  showHelp(showMessage) {
    const shortcuts = this.getAllShortcuts()
    if (shortcuts.length === 0) {
      showMessage('暂无注册的快捷键')
      return
    }

    const helpText = shortcuts
      .map(s => `<tr><td><kbd>${s.combination}</kbd></td><td>已注册</td></tr>`)
      .join('')

    showMessage(`
      <div style="max-height: 400px; overflow-y: auto;">
        <h3 style="margin-bottom: 15px;">快捷键列表</h3>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="border-bottom: 2px solid #ddd;">
              <th style="padding: 8px; text-align: left;">组合键</th>
              <th style="padding: 8px; text-align: left;">功能</th>
            </tr>
          </thead>
          <tbody>
            ${helpText}
          </tbody>
        </table>
      </div>
    `, {
      dangerouslyUseHTMLString: true
    })
  }
}

// 导出单例
export const shortcutManager = new ShortcutManager()

/**
 * 注册默认快捷键
 * @param {Object} handlers - 处理函数对象
 */
export function registerDefaultShortcuts(handlers) {
  const {
    generateDesign,
    clearSites,
    zoomToSites,
    undo,
    redo,
    toggleLayer,
    handleLocationChange,
    showHelp
  } = handlers

  // 生成方案
  shortcutManager.register('Ctrl+Enter', generateDesign)
  
  // 清除站点
  shortcutManager.register('Ctrl+L', clearSites)
  
  // 缩放到站点
  shortcutManager.register('Ctrl+Shift+S', zoomToSites)
  
  // 撤销
  shortcutManager.register('Ctrl+Z', undo)
  
  // 重做
  shortcutManager.register('Ctrl+Y', redo)
  
  // 切换图层
  shortcutManager.register('Ctrl+1', () => toggleLayer('site'))
  shortcutManager.register('Ctrl+2', () => toggleLayer('tower'))
  shortcutManager.register('Ctrl+3', () => toggleLayer('coverage'))
  shortcutManager.register('Ctrl+4', () => toggleLayer('label'))
  
  // 位置切换
  shortcutManager.register('Alt+1', () => handleLocationChange('yuncheng'))
  shortcutManager.register('Alt+2', () => handleLocationChange('wuhan'))
  shortcutManager.register('Alt+3', () => handleLocationChange('beijing'))
  
  // 帮助
  shortcutManager.register('?', showHelp, { ignoreInput: true })
  
  // 初始化
  shortcutManager.init()
  
  logger.info('ShortcutManager', '默认快捷键已注册')
}
