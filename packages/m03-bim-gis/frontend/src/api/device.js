/**
 * 设备 API
 */
import request from '@/utils/request'

export default {
  /** 分页查询设备 */
  page(params) {
    return request.get('/device/page', { params })
  },
  /** 根据项目ID获取所有设备 */
  listByProject(projectId) {
    return request.get(`/device/project/${projectId}`)
  },
  /** 添加设备 */
  add(data) {
    return request.post('/device', data)
  },
  /** 批量添加设备 */
  batchAdd(data) {
    return request.post('/device/batch', data)
  },
  /** 更新设备 */
  update(data) {
    return request.put('/device', data)
  },
  /** 更新设备位置（拖拽） */
  updatePosition(id, lng, lat, height) {
    const params = { lng, lat }
    if (height !== undefined) params.height = height
    return request.put(`/device/${id}/position`, null, { params })
  },
  /** 更新天线参数 */
  updateAntennaParams(id, azimuth, downtilt) {
    return request.put(`/device/${id}/antenna`, null, { params: { azimuth, downtilt } })
  },
  /** 删除设备 */
  delete(id) {
    return request.delete(`/device/${id}`)
  },
  /** 统计项目下设备数量 */
  statsByType(projectId) {
    return request.get(`/device/stats/${projectId}`)
  }
}
