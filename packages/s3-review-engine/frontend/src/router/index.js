import { createRouter, createWebHashHistory } from 'vue-router'

// iframe 子模块路由：使用 hash 模式，匹配 m06-portal 的 moduleUrl('s3','work-order')
// 拼接出的 URL 形如 /modules/s3/#/work-order。
// 登录与导航栏由门户(m06)统一提供，本模块只暴露业务路由，不再内置 Login。
const routes = [
  {
    path: '/',
    redirect: '/work-order'
  },
  {
    // 门户「智能审查」菜单(安全规范审查/资源冲突检测/审查报告)均指向此入口
    path: '/work-order',
    name: 'Workbench',
    component: () => import('../views/Workbench.vue')
  },
  {
    // 任务列表「报告」按钮 / 报告页自身切换任务时直接跳转的独立路由（保留以便深度链接）
    path: '/report/:taskId?',
    name: 'ReviewReport',
    component: () => import('../views/ReviewReport.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
