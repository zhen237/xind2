import { createRouter, createWebHistory } from 'vue-router'
import PipelineOverview from '../views/PipelineOverview.vue'
import BomHome from '../views/BomHome.vue'

const routes = [
  { path: '/', name: 'Pipeline', component: PipelineOverview },
  { path: '/bom', name: 'BomHome', component: BomHome },
  {
    path: '/detail/:taskId',
    name: 'BomDetail',
    component: () => import('../views/BomDetail.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
