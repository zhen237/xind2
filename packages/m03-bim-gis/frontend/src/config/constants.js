/**
 * 全局配置常量
 * 集中管理所有魔法数字和字符串
 */

import { DEFAULT_LOCATION, PRESET_LOCATIONS } from './location'

// ==================== 位置配置 ====================
// 唯一数据源: config/location.js
// 此处仅做映射导出以保持向后兼容

export const LOCATIONS = {
  YUNCHENG: {
    id: 'yuncheng',
    name: '运城学院',
    longitude: DEFAULT_LOCATION.longitude,
    latitude: DEFAULT_LOCATION.latitude,
    cameraHeight: DEFAULT_LOCATION.cameraHeight,
  },
  WUHAN: {
    id: 'wuhan',
    name: '武汉',
    longitude: 114.39,
    latitude: 30.506,
    cameraHeight: 50000,
  },
  BEIJING: {
    id: 'beijing',
    name: '北京',
    longitude: 116.4074,
    latitude: 39.9042,
    cameraHeight: 50000,
  },
}

// 位置选项列表
export const LOCATION_OPTIONS = Object.values(LOCATIONS).map(loc => ({
  label: loc.name,
  value: loc.id,
  ...loc,
}))

// ==================== 颜色配置 ====================

export const COLORS = {
  // 站点颜色
  SITE_VALID: '#67C23A',
  SITE_INVALID: '#F56C6C',
  SITE_WARNING: '#E6A23C',
  
  // 覆盖质量颜色
  COVERAGE_EXCELLENT: '#E1F3D8',
  COVERAGE_GOOD: '#B3E5FC',
  COVERAGE_FAIR: '#FFF3E0',
  COVERAGE_POOR: '#FFCDD2',
  
  // UI颜色
  PRIMARY: '#409EFF',
  SUCCESS: '#67C23A',
  WARNING: '#E6A23C',
  DANGER: '#F56C6C',
  INFO: '#909399'
}

// ==================== 性能配置 ====================

export const PERFORMANCE = {
  // 动画配置
  ANIMATION_DURATION: 2000,
  FLY_TO_DURATION: 2000,
  
  // 防抖延迟
  DEBOUNCE_DELAY: 300,
  
  // 渲染限制
  MAX_SITES_RENDER: 500,
  MAX_ENTITIES_PER_FRAME: 100,
  
  // 采样配置
  SAMPLE_COUNT_HEATMAP: 500,
  SAMPLE_COUNT_GAP_DETECTION: 500,
  
  // 自动保存
  AUTOSAVE_INTERVAL: 60000, // 60秒
  AUTOSAVE_MAX_HISTORY: 50
}

// ==================== 验证规则 ====================

export const VALIDATION_RULES = {
  // 坐标范围
  LONGITUDE_MIN: -180,
  LONGITUDE_MAX: 180,
  LATITUDE_MIN: -90,
  LATITUDE_MAX: 90,
  
  // 中国范围
  CHINA_LONGITUDE_MIN: 73.5,
  CHINA_LONGITUDE_MAX: 135.1,
  CHINA_LATITUDE_MIN: 3.8,
  CHINA_LATITUDE_MAX: 53.6,
  
  // 覆盖半径
  MIN_COVERAGE_RADIUS: 50,
  MAX_COVERAGE_RADIUS: 5000,
  RECOMMENDED_COVERAGE_RADIUS: 500,
  
  // 网格大小
  MIN_GRID_SIZE: 10,
  MAX_GRID_SIZE: 1000,
  RECOMMENDED_GRID_SIZE: 200,
  
  // 塔高
  MIN_TOWER_HEIGHT: 5,
  MAX_TOWER_HEIGHT: 100,
  RECOMMENDED_TOWER_HEIGHT: 30,
  
  // 频率
  MIN_FREQUENCY: 150,
  MAX_FREQUENCY: 3000,
  RECOMMENDED_FREQUENCY: 2100,
  
  // 扇区数
  VALID_SECTOR_COUNTS: [1, 3, 6],
  
  // 网格与覆盖半径比例
  MAX_GRID_RATIO: 0.5,
  MIN_GRID_RATIO: 0.05
}

// ==================== 模板配置 ====================

export const TEMPLATE_CONFIG = {
  MACRO: {
    id: 'macro',
    name: '标准宏基站(三扇区)',
    category: 'macro',
    defaultParams: {
      frequency: 2100,
      towerHeight: 35,
      coverageRadius: 500,
      gridSize: 200,
      sectorCount: 3
    }
  },
  MICRO: {
    id: 'micro',
    name: '微基站',
    category: 'micro',
    defaultParams: {
      frequency: 2600,
      towerHeight: 15,
      coverageRadius: 200,
      gridSize: 100,
      sectorCount: 6
    }
  },
  INDOOR: {
    id: 'indoor',
    name: '室内分布系统',
    category: 'indoor',
    defaultParams: {
      frequency: 2600,
      towerHeight: 3,
      coverageRadius: 50,
      gridSize: 20,
      sectorCount: 1
    }
  }
}

// ==================== API配置 ====================

export const API_CONFIG = {
  BASE_URL: '/api/m03',
  TIMEOUT: 30000,
  RETRY_COUNT: 3,
  RETRY_DELAY: 1000,
  
  // 端点
  ENDPOINTS: {
    HEALTH: '/health',
    TEMPLATES: '/design/templates',
    GENERATE: '/design/generate',
    UPLOAD: '/design/upload',
    TASKS: '/design/tasks'
  }
}

// ==================== 导出配置 ====================

export const EXPORT_CONFIG = {
  JSON_FILENAME_PREFIX: 'design_',
  CSV_FILENAME_PREFIX: 'sites_',
  GEOJSON_FILENAME_PREFIX: 'sites_',
  
  // CSV列定义
  CSV_HEADERS: [
    '站点ID',
    '经度',
    '纬度',
    '塔高(m)',
    'RSRP(dBm)',
    '状态',
    '场景'
  ]
}
