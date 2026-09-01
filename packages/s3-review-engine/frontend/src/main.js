import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/theme.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')

// —— iframe 集成：接收门户(m06-portal)下发的 JWT ——
// 门户在 iframe 加载完成后会 postMessage({ type: 'TOKEN', token, userInfo })。
// 收到后写入 localStorage，request.js 每次请求自动从 localStorage 读取并附带 Authorization 头。
window.addEventListener('message', (event) => {
  const data = event.data
  if (!data || data.type !== 'TOKEN') return
  if (data.token) {
    localStorage.setItem('token', data.token)
  }
  if (data.userInfo) {
    localStorage.setItem('user', JSON.stringify(data.userInfo))
  }
}, false)
