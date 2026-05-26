import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api',
  timeout: 15000
})

service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

service.interceptors.response.use(
  response => response.data,
  error => {
    const msg = error.response?.data?.message || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default service

// M03 API 封装
export const projectAPI = {
  list: () => service.get('/m03/project'),
  getById: (id) => service.get(`/m03/project/${id}`),
  create: (data) => service.post('/m03/project', data),
  update: (id, data) => service.put(`/m03/project/${id}`, data),
  delete: (id) => service.delete(`/m03/project/${id}`)
}

export const deviceAPI = {
  list: () => service.get('/m03/device'),
  getById: (id) => service.get(`/m03/device/${id}`),
  getByProject: (projectId) => service.get(`/m03/device/project/${projectId}`),
  getByStation: (stationCode) => service.get(`/m03/device/station/${stationCode}`),
  getByType: (deviceType) => service.get(`/m03/device/type/${deviceType}`),
  create: (data) => service.post('/m03/device', data),
  update: (id, data) => service.put(`/m03/device/${id}`, data),
  delete: (id) => service.delete(`/m03/device/${id}`)
}

export const modelAPI = {
  list: () => service.get('/m03/model'),
  getById: (id) => service.get(`/m03/model/${id}`),
  getByType: (modelType) => service.get(`/m03/model/type/${modelType}`),
  create: (data) => service.post('/m03/model', data),
  update: (id, data) => service.put(`/m03/model/${id}`, data),
  delete: (id) => service.delete(`/m03/model/${id}`)
}

export const regionAPI = {
  list: () => service.get('/m03/region'),
  getById: (id) => service.get(`/m03/region/${id}`),
  getByParent: (parentCode) => service.get(`/m03/region/parent/${parentCode}`)
}
