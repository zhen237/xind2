import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import MainLayout from '../layout/MainLayout.vue'
import ProjectList from '../views/m03/ProjectList.vue'
import Design from '../views/m03/Design.vue'
import CoverageAssessment from '../views/m03/CoverageAssessment.vue'
import Station3D from '../views/m03/Station3D.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Main',
    component: MainLayout,
    meta: { requiresAuth: true }
  },
  {
    path: '/m03/project',
    name: 'M03Project',
    component: ProjectList,
    meta: { requiresAuth: true }
  },
  {
    path: '/m03/design',
    name: 'M03Design',
    component: Design,
    meta: { requiresAuth: true }
  },
  {
    path: '/m03/coverage',
    name: 'CoverageAssessment',
    component: CoverageAssessment,
    meta: { requiresAuth: true }
  },
  {
    path: '/m03/station3d',
    name: 'Station3D',
    component: Station3D,
    meta: { requiresAuth: true }
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
