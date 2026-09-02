/**
 * 区域 API
 */
import request from '@/utils/request'

export default {
  /** 查询所有区域 */
  list() {
    return request.get('/region/list')
  },
  /** 根据区域编码查询 */
  getByCode(regionCode) {
    return request.get(`/region/${regionCode}`)
  },
  /** 创建区域 */
  create(data) {
    return request.post('/region', data)
  }
}
