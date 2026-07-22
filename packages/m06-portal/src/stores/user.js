import { defineStore } from 'pinia'
import axios from 'axios'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null,
    menus: []
  }),
  actions: {
    async login(username, password) {
      const res = await axios.post('/api/m01/auth/login', { username, password })
      const d = res.data.data || res.data
      this.token = d.token
      localStorage.setItem('token', this.token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      this.userInfo = {
        userId: d.userId,
        username: d.username,
        realName: d.realName
      }
      await this.fetchMenus()
      return true
    },
    async fetchMenus() {
      const res = await axios.get('/api/m01/menu/user')
      this.menus = res.data.data || res.data
    },
    logout() {
      this.token = ''
      this.userInfo = null
      this.menus = []
      localStorage.removeItem('token')
      delete axios.defaults.headers.common['Authorization']
    }
  }
})
