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
    path: '/station-scene',
    name: 'StationScene',
    component: () => import('@/components/CesiumStationScene.vue'),
    meta: { title: '基站3D场景' }
  },
  {
    path: '/coverage-report',
    name: 'CoverageReport',
    component: () => import('@shared/components/CoverageReport.vue'),
    meta: { title: '覆盖评估报告' }
  },
  {
    path: '/viewer',
    name: 'CesiumViewer',
    component: () => import('@/components/CesiumViewer.vue'),
    meta: { title: '3D视图' }
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
