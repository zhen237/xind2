import request from './request'
import axios from 'axios'

export const taskApi = {
  list: (params) => request.get('/s3/review/task', { params }),
  get: (id) => request.get(`/s3/review/task/${id}`),
  create: (data) => request.post('/s3/review/task', data),
  recheck: (id) => request.post(`/s3/review/task/${id}/recheck`),
  getResults: (id) => request.get(`/s3/review/task/${id}/results`),
  getDesignMeta: (id) => request.get(`/s3/review/task/${id}/design-meta`),
  getStatusOptions: () => request.get('/s3/review/task/status-options'),
  // B-3 PDF 导出：原始二进制下载，绕过 JSON 拦截器（直接拿 Blob + 响应头文件名）
  exportPdf: (id) => {
    const token = localStorage.getItem('token')
    return axios.get(`/api/v1/s3/review/task/${id}/export-pdf`, {
      responseType: 'blob',
      headers: token ? { Authorization: 'Bearer ' + token } : {}
    })
  },
  update: (data) => request.put('/s3/review/task', data),
  delete: (id) => request.delete(`/s3/review/task/${id}`)
}

export const ruleApi = {
  list: (params) => request.get('/s3/review/rule', { params }),
  get: (id) => request.get(`/s3/review/rule/${id}`),
  create: (data) => request.post('/s3/review/rule', data),
  update: (data) => request.put('/s3/review/rule', data),
  delete: (id) => request.delete(`/s3/review/rule/${id}`),
  getByCategory: (category) => request.get(`/s3/review/rule/category/${category}`),
  getCount: () => request.get('/s3/review/rule/count'),
  getCategories: () => request.get('/s3/review/rule/categories')
}

export const resultApi = {
  list: (params) => request.get('/s3/review/result', { params }),
  get: (id) => request.get(`/s3/review/result/${id}`),
  getByTask: (taskId) => request.get(`/s3/review/result/task/${taskId}`),
  // 分页查询
  page: (params) => request.get('/s3/review/result/page', { params }),
  pageByTask: (taskId, params) => request.get(`/s3/review/result/task-page/${taskId}`, { params }),
  // 统计
  statistics: (params) => request.get('/s3/review/result/statistics', { params }),
  create: (data) => request.post('/s3/review/result', data),
  update: (data) => request.put('/s3/review/result', data),
  delete: (id) => request.delete(`/s3/review/result/${id}`)
}
