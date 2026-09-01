/**
 * 模型 API
 */
import request from '@/utils/request'

export default {
  /** 分页查询模型 */
  page(params) {
    return request.get('/model/page', { params })
  },
  /** 按类型查询模型列表 */
  listByType(modelType) {
    return request.get('/model/list', { params: { modelType } })
  },
  /** 获取模型详情 */
  getById(id) {
    return request.get(`/model/${id}`)
  },
  /** 上传模型文件 */
  upload(file, params) {
    const formData = new FormData()
    formData.append('file', file)
    if (params.modelName) formData.append('modelName', params.modelName)
    if (params.modelType) formData.append('modelType', params.modelType)
    if (params.description) formData.append('description', params.description)
    return request.post('/model/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  /** 获取模型文件下载URL */
  getModelUrl(id) {
    return request.get(`/model/${id}/url`)
  },
  /** 更新模型版本 */
  updateVersion(id, version, description) {
    const params = { version }
    if (description) params.description = description
    return request.put(`/model/${id}/version`, null, { params })
  },
  /** 删除模型 */
  delete(id) {
    return request.delete(`/model/${id}`)
  }
}
