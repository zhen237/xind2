import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api/s2/cad',
  timeout: 60000,
})

http.interceptors.response.use(
  (res) => {
    const data = res.data
    if (data && data.code !== undefined && data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data
  },
  (err) => {
    ElMessage.error(err.response?.data?.message || err.message || '网络错误')
    return Promise.reject(err)
  },
)

export const health = () => http.get('/health')

export const uploadCadFile = (file, { sourceEpsg = 'EPSG:4490', targetEpsg = 'EPSG:4326' } = {}) => {
  const form = new FormData()
  form.append('file', file)
  form.append('sourceEpsg', sourceEpsg)
  form.append('targetEpsg', targetEpsg)
  return http.post('/cad-files/upload', form)
}

export const getCadFiles = () => http.get('/cad-files')

export const parseCadFile = (id) => http.post(`/cad-files/${id}/parse`)

export const getCadFileContent = (id) => http.get(`/cad-files/${id}/content`)

export const getSupportedSystems = () => http.get('/coordinate/supported-systems')

export const transformCoordinate = (payload) => http.post('/coordinate/transform', payload)

export const batchTransform = (payload) => http.post('/coordinate/batch-transform', payload)

export const createFusionTask = (payload) => http.post('/fusion/tasks', payload)

export const getFusionTasks = () => http.get('/fusion/tasks')

export const autoFuse = (payload) => http.post('/fusion/auto-fuse', payload)

export const getFusionGeoJson = (taskId) => http.get(`/fusion/tasks/${taskId}/geojson`, { responseType: 'text' })

export const getFusionResult = (taskId) => http.get(`/fusion/tasks/${taskId}`)
