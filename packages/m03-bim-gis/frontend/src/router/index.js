import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/design'
  },
  {
    path: '/design',
    name: 'Design',
    component: () => import('@/views/Design.vue'),
    meta: { title: '三维场景设计' }
  },
  {
    path: '/project',
    name: 'Project',
    component: () => import('@/views/Design.vue'),
    meta: { title: '项目管理' }
  },
  {
    path: '/coverage',
    name: 'Coverage',
    component: () => import('@/views/Design.vue'),
    meta: { title: '覆盖评估' }
  },
  {
    path: '/station',
    name: 'Station',
    component: () => import('@/views/Design.vue'),
    meta: { title: '基站环境' }
  }
]

const router = createRouter({
  history: createWebHashHistory('/modules/m03/'),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'M03 BIM+GIS'} - 通信基建数智化平台`
  next()
})

export default router
