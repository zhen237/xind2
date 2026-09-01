import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import { isMockEnabled, setupMock } from './mock'

// 本地虚拟数据模式（仿 S1 做法）：免后端 8090/8100，用引擎预生成快照演示
if (isMockEnabled()) setupMock()

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')
