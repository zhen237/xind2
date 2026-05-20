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
      this.token = res.data.token
      localStorage.setItem('token', this.token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      this.userInfo = {
        userId: res.data.userId,
        username: res.data.username,
        realName: res.data.realName
      }
      await this.fetchMenus()
      return true
    },
    async fetchMenus() {
      const res = await axios.get('/api/m01/menu/user')
      this.menus = res.data
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
