/**
 * 虚拟演示数据（仅用于 GitHub Pages 无后端部署）
 * ------------------------------------------------------------------
 * 当构建时设置 VITE_USE_MOCK=true，前端请求会走 src/mock/adapter.js，
 * 直接返回本文件中的虚拟数据，无需任何后端服务即可在 GitHub Pages 上跑通
 * 「加载数据 → 渲染站点 → 叠加 FTTH 图层」的完整演示链路。
 *
 * 坐标采用与 public/ftth-data.json（卡萨布兰卡 JAD-MAR 竣工数据集）一致的范围，
 * 使虚拟基站与 FTTH 光交箱在地图同一区域叠加显示。
 */

const PM_LON = -8.5275
const PM_LAT = 33.2245

// 汇聚机房（与 FTTH 图层最近站点连线使用）
export const MOCK_MACHINE_ROOMS = [
  {
    roomId: 'ROOM-HUB-001',
    name: '卡萨布兰卡汇聚机房',
    longitude: PM_LON,
    latitude: PM_LAT,
    routeType: 'manhattan'
  }
]

// 虚拟基站（覆盖有效性/RSRP 各异，演示筛选、排序、统计能力）
export const MOCK_SITES = [
  { siteId: 'SITE-001', longitude: -8.5285, latitude: 33.2240, isValid: true,  rsrp: -78, towerHeight: 40, frequencyBand: '3.5GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-002', longitude: -8.5270, latitude: 33.2238, isValid: true,  rsrp: -82, towerHeight: 35, frequencyBand: '3.5GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-003', longitude: -8.5300, latitude: 33.2242, isValid: true,  rsrp: -85, towerHeight: 30, frequencyBand: '2.6GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-004', longitude: -8.5265, latitude: 33.2225, isValid: true,  rsrp: -88, towerHeight: 45, frequencyBand: '3.5GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-005', longitude: -8.5295, latitude: 33.2220, isValid: true,  rsrp: -91, towerHeight: 32, frequencyBand: '2.6GHz', sectorCount: 2, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-006', longitude: -8.5280, latitude: 33.2255, isValid: true,  rsrp: -79, towerHeight: 38, frequencyBand: '3.5GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-007', longitude: -8.5255, latitude: 33.2240, isValid: false, rsrp: -105, towerHeight: 30, frequencyBand: '2.6GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-008', longitude: -8.5310, latitude: 33.2230, isValid: true,  rsrp: -83, towerHeight: 42, frequencyBand: '3.5GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-009', longitude: -8.5275, latitude: 33.2215, isValid: true,  rsrp: -90, towerHeight: 28, frequencyBand: '2.6GHz', sectorCount: 2, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-010', longitude: -8.5305, latitude: 33.2210, isValid: true,  rsrp: -87, towerHeight: 36, frequencyBand: '3.5GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-011', longitude: -8.5260, latitude: 33.2250, isValid: true,  rsrp: -84, towerHeight: 34, frequencyBand: '2.6GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' },
  { siteId: 'SITE-012', longitude: -8.5290, latitude: 33.2255, isValid: true,  rsrp: -80, towerHeight: 40, frequencyBand: '3.5GHz', sectorCount: 3, roomId: 'ROOM-HUB-001' }
]

export const MOCK_PROJECTS = [
  { id: 1, projectName: '卡萨布兰卡 JAD-MAR 通信基建试点', projectCode: 'JAD-MAR-DEMO' },
  { id: 2, projectName: '运城学院 Campus 5G 覆盖示范', projectCode: 'YCXY-2026-001' }
]

export const MOCK_DESIGNS = {
  1: {
    id: 1,
    schemeName: '卡萨布兰卡 JAD-MAR 宏微协同规划',
    projectId: 1,
    frequencyBand: '3.5GHz',
    towerHeight: 38,
    totalSites: MOCK_SITES.length,
    validSites: MOCK_SITES.filter(s => s.isValid).length,
    invalidSites: MOCK_SITES.filter(s => !s.isValid).length,
    machineRooms: MOCK_MACHINE_ROOMS
  },
  2: {
    id: 2,
    schemeName: '运城学院 Campus 宏站规划',
    projectId: 2,
    frequencyBand: '3.5GHz',
    towerHeight: 35,
    totalSites: MOCK_SITES.length,
    validSites: MOCK_SITES.filter(s => s.isValid).length,
    invalidSites: MOCK_SITES.filter(s => !s.isValid).length,
    machineRooms: MOCK_MACHINE_ROOMS
  }
}

export const MOCK_TEMPLATES = [
  { id: 'macro', name: '宏站覆盖模板', templateType: 'macro', defaultBand: '3.5GHz', defaultTower: 40, description: '城市宏站密集覆盖，3 扇区' },
  { id: 'micro', name: '微站补盲模板', templateType: 'micro', defaultBand: '2.6GHz', defaultTower: 25, description: '热点区域容量补充，2 扇区' }
]

// 极简 GeoJSON（设计与导出模块在无后端时的兜底）
export const MOCK_GEOJSON = {
  type: 'FeatureCollection',
  properties: { band: '3.5GHz', tower_height: 38 },
  features: MOCK_SITES.map(s => ({
    type: 'Feature',
    properties: {
      site_id: s.siteId,
      longitude: s.longitude,
      latitude: s.latitude,
      tower_height: s.towerHeight,
      is_valid: s.isValid,
      rsrp: s.rsrp
    },
    geometry: { type: 'Point', coordinates: [s.longitude, s.latitude] }
  }))
}
