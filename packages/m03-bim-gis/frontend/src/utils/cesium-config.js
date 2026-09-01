/**
 * Cesium 配置 — 天地图 Token、图层配置
 */

// 天地图 Token（需替换为实际申请的 Token）
export const TIANDITU_TOKEN = 'your-tianditu-token-here'

// Cesium Ion Token（可选，用于地形等）
export const CESIUM_ION_TOKEN = ''

// 天地图图层配置
export const TIANDITU_LAYERS = {
  // 影像底图
  img: {
    url: `https://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}&tk=${TIANDITU_TOKEN}`,
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maximumLevel: 18,
    credit: '天地图影像'
  },
  // 矢量底图
  vec: {
    url: `https://t{s}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}&tk=${TIANDITU_TOKEN}`,
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maximumLevel: 18,
    credit: '天地图矢量'
  },
  // 影像注记
  cia: {
    url: `https://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}&tk=${TIANDITU_TOKEN}`,
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maximumLevel: 18,
    credit: '天地图影像注记'
  },
  // 矢量注记
  cva: {
    url: `https://t{s}.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}&tk=${TIANDITU_TOKEN}`,
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maximumLevel: 18,
    credit: '天地图矢量注记'
  },
  // 地形
  ter: {
    url: `https://t{s}.tianditu.gov.cn/ter_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ter&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}&tk=${TIANDITU_TOKEN}`,
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maximumLevel: 14,
    credit: '天地图地形'
  }
}

// 设备类型配置
export const DEVICE_TYPE_CONFIG = {
  ANTENNA: {
    label: '天线',
    color: '#F56C6C',
    icon: 'el-icon-Connection',
    defaultHeight: 35
  },
  CABINET: {
    label: '机柜',
    color: '#E6A23C',
    icon: 'el-icon-Box',
    defaultHeight: 2
  },
  TOWER: {
    label: '铁塔',
    color: '#409EFF',
    icon: 'el-icon-Flag',
    defaultHeight: 35
  },
  CABLE: {
    label: '线缆',
    color: '#67C23A',
    icon: 'el-icon-Link',
    defaultHeight: 0
  },
  RRU: {
    label: 'RRU',
    color: '#909399',
    icon: 'el-icon-Monitor',
    defaultHeight: 30
  },
  BBU: {
    label: 'BBU',
    color: '#9B59B6',
    icon: 'el-icon-Cpu',
    defaultHeight: 1.5
  },
  POWER: {
    label: '电源',
    color: '#3498DB',
    icon: 'el-icon-Lightning',
    defaultHeight: 1.5
  }
}

/**
 * 初始化 Cesium Ion Token
 */
export function initCesiumIon() {
  if (typeof window !== 'undefined' && window.Cesium) {
    if (CESIUM_ION_TOKEN) {
      window.Cesium.Ion.defaultAccessToken = CESIUM_ION_TOKEN
    }
  }
}
