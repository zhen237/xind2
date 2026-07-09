/**
 * 参数校验工具
 * 提供实时参数验证和智能推荐功能
 */

/**
 * 中国有效坐标范围
 */
const CHINA_COORDINATES = {
  longitude: { min: 73.5, max: 135.1 },
  latitude: { min: 3.8, max: 53.6 }
}

/**
 * 参数推荐配置
 */
export const PARAMETER_RECOMMENDATIONS = {
  macro: {
    coverageRadius: { min: 300, max: 5000, recommended: 500 },
    gridSize: { min: 100, max: 1000, recommended: 200 },
    sectorCount: [1, 3, 6]
  },
  micro: {
    coverageRadius: { min: 50, max: 1000, recommended: 200 },
    gridSize: { min: 30, max: 300, recommended: 100 },
    sectorCount: [1, 3, 6]
  },
  indoor: {
    coverageRadius: { min: 20, max: 200, recommended: 50 },
    gridSize: { min: 10, max: 50, recommended: 20 },
    sectorCount: [1]
  }
}

/**
 * 校验参数并返回警告和错误
 * @param {Object} params - 参数对象
 * @returns {Object} { warnings: string[], errors: string[] }
 */
export function validateParameters(params) {
  const warnings = []
  const errors = []

  // 1. 校验经纬度
  validateCoordinates(params, errors, warnings)
  
  // 2. 校验覆盖半径
  validateCoverageRadius(params, errors, warnings)
  
  // 3. 校验网格大小
  validateGridSize(params, errors, warnings)
  
  // 4. 校验网格与覆盖半径比例
  validateGridRatio(params, warnings)
  
  // 5. 校验扇区数
  validateSectorCount(params, errors, warnings)

  return { warnings, errors }
}

/**
 * 校验坐标范围
 */
function validateCoordinates(params, errors, warnings) {
  const lon = parseFloat(params.centerLongitude)
  const lat = parseFloat(params.centerLatitude)

  if (isNaN(lon) || isNaN(lat)) {
    errors.push('请输入有效的经纬度数值')
    return
  }

  if (lon < CHINA_COORDINATES.longitude.min || lon > CHINA_COORDINATES.longitude.max) {
    errors.push(`经度超出中国范围(${CHINA_COORDINATES.longitude.min}-${CHINA_COORDINATES.longitude.max})`)
  }

  if (lat < CHINA_COORDINATES.latitude.min || lat > CHINA_COORDINATES.latitude.max) {
    errors.push(`纬度超出中国范围(${CHINA_COORDINATES.latitude.min}-${CHINA_COORDINATES.latitude.max})`)
  }

  // 警告：接近边界
  if (lon < 80 || lon > 130) {
    warnings.push('经度接近中国边界，可能影响覆盖计算准确性')
  }
  if (lat < 10 || lat > 50) {
    warnings.push('纬度接近中国边界，可能影响覆盖计算准确性')
  }
}

/**
 * 校验覆盖半径
 */
function validateCoverageRadius(params, errors, warnings) {
  const radius = parseInt(params.coverageRadius)
  
  if (isNaN(radius)) {
    errors.push('请输入有效的覆盖半径')
    return
  }

  if (radius < 50) {
    errors.push('覆盖半径不能小于50米')
  } else if (radius < 100) {
    warnings.push('覆盖半径较小(＜100m)，可能无法生成有效站点')
  } else if (radius > 5000) {
    warnings.push('覆盖半径过大(＞5km)，建议分区域规划')
  }
}

/**
 * 校验网格大小
 */
function validateGridSize(params, errors, warnings) {
  const gridSize = parseInt(params.gridSize)
  
  if (isNaN(gridSize)) {
    errors.push('请输入有效的网格大小')
    return
  }

  if (gridSize < 10) {
    errors.push('网格大小不能小于10米')
  } else if (gridSize > 1000) {
    warnings.push('网格较大(＞1km)，可能遗漏覆盖细节')
  }
}

/**
 * 校验网格与覆盖半径比例
 */
function validateGridRatio(params, warnings) {
  const radius = parseInt(params.coverageRadius)
  const gridSize = parseInt(params.gridSize)

  if (isNaN(radius) || isNaN(gridSize) || radius === 0 || gridSize === 0) {
    return
  }

  if (gridSize > radius * 0.5) {
    warnings.push('网格大小相对于覆盖半径过大，可能导致覆盖不均')
  }
  
  if (gridSize < radius * 0.05) {
    warnings.push('网格过小可能导致生成站点数量过多，影响性能')
  }
}

/**
 * 校验扇区数
 */
function validateSectorCount(params, errors, warnings) {
  const sectors = parseInt(params.sectorCount)
  
  if (isNaN(sectors)) {
    errors.push('请输入有效的扇区数')
    return
  }

  if (![1, 3, 6].includes(sectors)) {
    warnings.push(`非常规扇区数(${sectors})，建议使用1、3或6扇区`)
  }
}

/**
 * 获取参数推荐值
 * @param {string} templateType - 模板类型
 * @returns {Object} 推荐参数
 */
export function getRecommendedParams(templateType = 'macro') {
  const rec = PARAMETER_RECOMMENDATIONS[templateType] || PARAMETER_RECOMMENDATIONS.macro
  return {
    coverageRadius: rec.coverageRadius.recommended,
    gridSize: rec.gridSize.recommended,
    sectorCount: rec.sectorCount[0]
  }
}

/**
 * 格式化参数显示
 * @param {string} fieldName - 字段名
 * @param {*} value - 值
 * @returns {string} 格式化后的字符串
 */
export function formatParameterDisplay(fieldName, value) {
  const units = {
    centerLongitude: '°',
    centerLatitude: '°',
    coverageRadius: 'm',
    gridSize: 'm'
  }
  
  const unit = units[fieldName] || ''
  return `${value}${unit}`
}
