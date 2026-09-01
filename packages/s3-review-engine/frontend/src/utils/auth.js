import { computed } from 'vue'

/**
 * 前端当前登录用户信息（登录时由 Login.vue 写入 localStorage 的 user）。
 * 供敏感操作按钮做角色门控展示；真正的权限判定以后端拦截器为准。
 */
export function useAuth() {
  const user = computed(() => {
    const raw = localStorage.getItem('user')
    if (!raw) return null
    try {
      return JSON.parse(raw)
    } catch (e) {
      return null
    }
  })
  const isAdmin = computed(
    () => !!user.value && Array.isArray(user.value.roles) && user.value.roles.includes('ADMIN')
  )
  return { user, isAdmin }
}
