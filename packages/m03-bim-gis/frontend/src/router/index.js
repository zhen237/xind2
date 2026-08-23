import { createRouter, createWebHashHistory } from 'vue-router'
import { logger } from '@/utils/logger.js'

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
    path: '/viewer',
    name: 'CesiumViewer',
    component: () => import('@/components/CesiumViewer.vue'),
    meta: { title: '3D视图' }
  },
  {
    path: '/models',
    name: 'Models',
    component: () => import('@/views/Models.vue'),
    meta: { title: '模型管理' }
  },
  {
    path: '/regions',
    name: 'Regions',
    component: () => import('@/views/Regions.vue'),
    meta: { title: '区域管理' }
  },
  {
    path: '/ftth',
    name: 'Ftth',
    component: () => import('@/views/Ftth.vue'),
    meta: { title: 'FTTH 交付物' }
  },
  // ── 404 兜底路由 ──────────────────────────────────────────
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面未找到' }
  }
]

const router = createRouter({
  history: createWebHashHistory('/modules/m03/'),
  routes
})

router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = `${to.meta.title || 'M03 BIM+GIS'} - 通信基建数智化平台`

  // Token 鉴权检查（iframe 嵌入场景下非强制，仅开发模式提示）
  const token = localStorage.getItem('token')
  if (!token && import.meta.env.DEV) {
    logger.warn('Router', `访问 ${to.path} 但未检测到有效 token — `
      + '请确认 M06 门户已通过 postMessage 注入 TOKEN')
  }

  next()
})

export default router
