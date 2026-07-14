/**
 * useTokenReceiver - 接收 m06-portal 通过 postMessage 发来的 JWT Token
 *
 * m06-portal 在 iframe 加载后通过 postMessage 发送 { type: 'TOKEN', token: 'xxx' }，
 * 子应用监听此消息并将 token 存入 localStorage，供 axios 拦截器使用。
 *
 * 用法：
 *   // 在子应用 App.vue 或 main.js 中
 *   import { useTokenReceiver } from '@shared/composables/useTokenReceiver'
 *   useTokenReceiver()  // 一次调用即可，自动监听
 *
 * 配合 shared/utils/request.js 使用，request.js 已从 localStorage 读取 token。
 */

import { onMounted, onUnmounted } from 'vue'

const STORAGE_KEY = 'token'
const MESSAGE_TYPE = 'TOKEN'

/**
 * 处理 postMessage 事件
 * @param {MessageEvent} event
 */
function handleMessage(event) {
  // 安全校验：只接受有效来源的消息
  if (!event.data || typeof event.data !== 'object') return
  if (event.data.type !== MESSAGE_TYPE) return
  if (!event.data.token) return

  // 存储 token
  localStorage.setItem(STORAGE_KEY, event.data.token)

  // 同时存储用户信息（如果附带）
  if (event.data.userInfo) {
    localStorage.setItem('userInfo', JSON.stringify(event.data.userInfo))
  }
}

/**
 * 接收 m06-portal 发来的 Token
 * 在组件 setup 中调用，自动管理事件监听的生命周期
 */
export function useTokenReceiver() {
  onMounted(() => {
    window.addEventListener('message', handleMessage)
  })

  onUnmounted(() => {
    window.removeEventListener('message', handleMessage)
  })
}

/**
 * 非 Composition API 场景下手动调用
 * 适用于 main.js 中全局初始化
 */
export function initTokenReceiver() {
  window.addEventListener('message', handleMessage)
}

export default useTokenReceiver
