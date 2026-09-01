import axios from 'axios'

// 所有请求走 /api/s5 前缀，由 vite 代理到 C# 后端 (http://localhost:8091)
const http = axios.create({ baseURL: '/api/s5', timeout: 10000 })

export const getDashboard = () => http.get('/dashboard').then(r => r.data)
export const getDevices = () => http.get('/devices').then(r => r.data)
export const getDevice = (code) => http.get(`/devices/${code}`).then(r => r.data)
export const getAlerts = (params = {}) => http.get('/alerts', { params }).then(r => r.data)
