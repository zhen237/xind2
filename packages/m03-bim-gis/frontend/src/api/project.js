/**
 * 项目 API
 */
import request from '@/utils/request'

export default {
  /** 分页查询项目 */
  page(params) {
    return request.get('/project/page', { params })
  },
  /** 查询所有项目 */
  list() {
    return request.get('/project/list')
  },
  /** 获取项目详情 */
  getById(id) {
    return request.get(`/project/${id}`)
  },
  /** 创建项目 */
  create(data) {
    return request.post('/project', data)
  },
  /** 更新项目 */
  update(data) {
    return request.put('/project', data)
  },
  /** 删除项目 */
  delete(id) {
    return request.delete(`/project/${id}`)
  }
}
