import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import * as Cesium from 'cesium'
import App from './App.vue'
import router from './router'
import './styles/global.css'

// ============================================================
// Cesium 配置 — 禁用 Ion 服务（使用本地地形/影像）
// ============================================================
Cesium.Ion.defaultAccessToken = undefined

// ============================================================
// 安全: postMessage 白名单校验
// ============================================================
const ALLOWED_ORIGINS = [
  window.location.origin,
  // 开发环境本地端口
  ...(import.meta.env.DEV
    ? ['http://localhost:9000', 'http://localhost:8080', 'http://localhost:8083']
    : []),
  // 生产环境通过 VITE_ALLOWED_ORIGINS 环境变量配置（逗号分隔）
  ...(import.meta.env.VITE_ALLOWED_ORIGINS
    ? import.meta.env.VITE_ALLOWED_ORIGINS.split(',').map(s => s.trim())
    : []),
]

window.addEventListener('message', (event) => {
  // 验证消息来源
  if (!ALLOWED_ORIGINS.some(origin =>
    event.origin === origin || event.origin.startsWith(origin)
  )) {
    if (import.meta.env.DEV) {
      console.warn('[M03] 拒绝来自未授权源的 message:', event.origin)
    }
    return
  }

  // 验证消息格式
  if (!event.data || event.data.type !== 'TOKEN') return

  const token = event.data.token
  if (typeof token !== 'string' || !token.trim()) {
    console.warn('[M03] 收到无效 TOKEN')
    return
  }

  localStorage.setItem('token', token)
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
})

// ============================================================
// Token 恢复 (页面刷新后)
// ============================================================
const savedToken = localStorage.getItem('token')
if (savedToken) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`
}

// ============================================================
// 应用初始化
// ============================================================
const app = createApp(App)

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error('[M03 Error]', { message: err?.message, info, component: instance?.$?.type?.name })
  ElMessage.error({
    message: err?.message || '系统发生未知错误',
    duration: 5000,
  })
}

const pinia = createPinia()
// 开发环境启用 Pinia DevTools
if (import.meta.env.DEV) {
  pinia.use(({ store }) => {
    store.$patch = store.$patch  // trigger devtools
  })
}
app.use(pinia)
app.use(router)
app.mount('#app')
