import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import axios from 'axios'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import App from './App.vue'
import router from './router'
import './styles/global.css'

// 配置 Cesium - 禁用 Ion 服务，使用天地图
Cesium.Ion.defaultAccessToken = undefined
window.Cesium = Cesium

// 监听 M06 门户传来的 JWT Token
window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'TOKEN') {
    const token = event.data.token
    localStorage.setItem('token', token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }
})

// 初始化：如果已有 token（刷新页面后），直接设置
const savedToken = localStorage.getItem('token')
if (savedToken) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`
}

// 开发环境：如果没有token，使用测试token
if (!savedToken && import.meta.env.DEV) {
  const testToken = 'test-token-m03-dev'
  localStorage.setItem('token', testToken)
  axios.defaults.headers.common['Authorization'] = `Bearer ${testToken}`
}

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
