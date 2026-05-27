import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import MainLayout from '../layout/MainLayout.vue'
import Dashboard from '../views/Dashboard.vue'
import ProjectList from '../views/m03/ProjectList.vue'
import Design from '../views/m03/Design.vue'
import CoverageAssessment from '../views/m03/CoverageAssessment.vue'
import Station3D from '../views/m03/Station3D.vue'
import M04ProjectList from '../views/m04/ProjectList.vue'
import M04WorkOrderList from '../views/m04/WorkOrderList.vue'
import M04AcceptanceList from '../views/m04/AcceptanceList.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard,
        meta: { requiresAuth: true }
      },
      {
        path: 'm03/project',
        name: 'M03Project',
        component: ProjectList,
        meta: { requiresAuth: true }
      },
      {
        path: 'm03/design',
        name: 'M03Design',
        component: Design,
        meta: { requiresAuth: true }
      },
      {
        path: 'm03/coverage',
        name: 'CoverageAssessment',
        component: CoverageAssessment,
        meta: { requiresAuth: true }
      },
      {
        path: 'm03/station3d',
        name: 'Station3D',
        component: Station3D,
        meta: { requiresAuth: true }
      },
      {
        path: 'm04/project',
        name: 'M04Project',
        component: M04ProjectList,
        meta: { requiresAuth: true }
      },
      {
        path: 'm04/work-order',
        name: 'M04WorkOrder',
        component: M04WorkOrderList,
        meta: { requiresAuth: true }
      },
      {
        path: 'm04/acceptance',
        name: 'M04Acceptance',
        component: M04AcceptanceList,
        meta: { requiresAuth: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
