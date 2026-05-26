import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/project'
  },
  {
    path: '/project',
    name: 'ProjectList',
    component: () => import('@/views/ProjectList.vue'),
    meta: { title: '项目列表' }
  },
  {
    path: '/design',
    name: 'Design',
    component: () => import('@/views/Design.vue'),
    meta: { title: '三维场景设计' }
  },
  {
    path: '/coverage',
    name: 'CoverageAssessment',
    component: () => import('@/views/CoverageAssessment.vue'),
    meta: { title: '覆盖评估' }
  },
  {
    path: '/station3d',
    name: 'Station3D',
    component: () => import('@/views/Station3D.vue'),
    meta: { title: '基站环境' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
