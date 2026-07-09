/**
 * 位置服务配置文件
 * 
 * 统一管理所有页面和组件的默认位置设置
 * 修改此处即可全局更新默认位置
 * 
 * @module config/location
 */

/**
 * 默认位置配置
 * 可根据需要修改为不同城市
 */
export const DEFAULT_LOCATION = {
  // 当前默认位置：山西省运城市运城学院
  name: '运城学院',
  city: '运城市',
  province: '山西省',
  address: '山西省运城市盐湖区运城学院',
  
  // 坐标信息（WGS84坐标系）
  longitude: 110.932025,
  latitude: 35.123754,
  
  // 初始缩放高度（米）
  cameraHeight: 50000,
  
  // 覆盖范围参数
  defaultCoverageRadius: 500,  // 米
  defaultGridSize: 200,        // 米
  defaultSectorCount: 3        // 扇区数
}

/**
 * 预设位置列表
 * 用户可快速切换到这些常用位置
 */
export const PRESET_LOCATIONS = [
  {
    id: 'yuncheng',
    name: '运城学院',
    longitude: 110.932025,
    latitude: 35.123754,
    city: '山西省运城市'
  },
  {
    id: 'beijing',
    name: '北京',
    longitude: 116.4074,
    latitude: 39.9042,
    city: '北京市'
  },
  {
    id: 'wuhan',
    name: '武汉',
    longitude: 114.39,
    latitude: 30.506,
    city: '湖北省武汉市'
  }
]

/**
 * 获取当前默认位置
 * @returns {Object} 位置配置对象
 */
export function getDefaultLocation() {
  return { ...DEFAULT_LOCATION }
}

/**
 * 根据ID获取预设位置
 * @param {string} locationId - 位置ID
 * @returns {Object|null} 位置配置对象，未找到返回null
 */
export function getPresetLocation(locationId) {
  const location = PRESET_LOCATIONS.find(loc => loc.id === locationId)
  return location ? { ...location } : null
}

/**
 * 验证坐标是否在有效范围内
 * @param {number} longitude - 经度
 * @param {number} latitude - 纬度
 * @returns {boolean} 是否有效
 */
export function isValidCoordinates(longitude, latitude) {
  // 边界值从 VALIDATION_RULES 导入以避免重复定义
  // 此处与 constants.js VALIDATION_RULES.CHINA_* 保持一致
  const CHINA_LON_MIN = 73.5, CHINA_LON_MAX = 135.1
  const CHINA_LAT_MIN = 3.8, CHINA_LAT_MAX = 53.6
  return longitude >= CHINA_LON_MIN && longitude <= CHINA_LON_MAX &&
         latitude >= CHINA_LAT_MIN && latitude <= CHINA_LAT_MAX
}
