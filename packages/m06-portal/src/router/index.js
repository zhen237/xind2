import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import MainLayout from '../layout/MainLayout.vue'
import ProgressBoard from '../views/system/ProgressBoard.vue'
import UserManagement from '../views/system/UserManagement.vue'
import RoleManagement from '../views/system/RoleManagement.vue'

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
        component: { render: () => null }
      },
      {
        path: 'system/progress',
        name: 'SystemProgress',
        component: ProgressBoard
      },
      {
        path: 'system/user',
        name: 'SystemUser',
        component: UserManagement
      },
      {
        path: 'system/role',
        name: 'SystemRole',
        component: RoleManagement
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
