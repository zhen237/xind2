import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import DeviceTwin from '../views/DeviceTwin.vue'
import AlertList from '../views/AlertList.vue'
import TwinView from '../views/TwinView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: Dashboard, meta: { title: '施工监测看板' } },
  { path: '/devices', name: 'devices', component: DeviceTwin, meta: { title: '设备孪生状态' } },
  { path: '/alerts', name: 'alerts', component: AlertList, meta: { title: '告警列表' } },
  { path: '/twin', name: 'twin', component: TwinView, meta: { title: '数字孪生' } }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
