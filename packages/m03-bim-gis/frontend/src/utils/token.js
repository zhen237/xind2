/**
 * JWT Token 工具 — 接收 M06 门户 iframe 传递的 Token
 */

const TOKEN_KEY = 'm03_token'
const USER_KEY = 'm03_user'

/**
 * 获取 Token
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 设置 Token
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 移除 Token
 */
export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * 初始化 Token 监听
 * 接收来自 M06 门户的 postMessage
 */
export function initTokenListener() {
  window.addEventListener('message', (event) => {
    // 验证来源（可根据实际门户地址配置）
    // if (event.origin !== 'http://localhost:5173') return

    const data = event.data
    if (data && data.type === 'TOKEN') {
      setToken(data.token)
      if (data.user) {
        localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      }
      console.log('[M03] 接收到来自门户的 Token')
    }

    // 接收项目ID跳转指令
    if (data && data.type === 'NAVIGATE') {
      const { path, params } = data
      if (path) {
        const query = params || {}
        window.__m03_navigate?.(path, query)
      }
    }
  })

  // 向父窗口发送就绪消息
  if (window.parent !== window) {
    window.parent.postMessage({ type: 'M03_READY' }, '*')
  }
}

/**
 * 获取当前用户信息
 */
export function getCurrentUser() {
  const userStr = localStorage.getItem(USER_KEY)
  if (userStr) {
    try {
      return JSON.parse(userStr)
    } catch {
      return null
    }
  }
  return null
}
