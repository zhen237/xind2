import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

service.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.message || 'Error')
      return Promise.reject(new Error(res.message || 'Error'))
    }
    return res
  },
  error => {
    const status = error.response && error.response.status
    if (status === 401) {
      // token 缺失 / 失效：清除本地凭证。iframe 形态下登录由门户(m06)统一处理，
      // 门户会通过 postMessage 重新下发 TOKEN；此处不再跳转到不存在的 /login。
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      ElMessage.error('登录已失效，请在门户重新登录')
    } else if (status === 403) {
      ElMessage.error('权限不足，无法执行该操作')
    } else {
      ElMessage.error(error.message || 'Network error')
    }
    return Promise.reject(error)
  }
)

export default service
