import axios from 'axios'

// 所有请求走 /api/s5 前缀，由 vite 代理到后端 (http://localhost:8091)
const http = axios.create({ baseURL: '/api/s5', timeout: 10000 })

export const getDashboard = () => http.get('/dashboard').then(r => r.data)
export const getDevices = () => http.get('/devices').then(r => r.data)
export const getDevice = (code) => http.get(`/devices/${code}`).then(r => r.data)
export const getAlerts = (params = {}) => http.get('/alerts', { params }).then(r => r.data)

// AI 助手对话（后端代理 DeepSeek，模型回复慢，单独放宽超时到 90s）
export const sendAiChat = (payload) => http.post('/ai/chat', payload, { timeout: 90000 }).then(r => r.data)
