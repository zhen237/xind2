/**
 * useCesiumCore — 标准化 Cesium Viewer 初始化和相机控制
 *
 * 消除 CesiumViewer.vue / CesiumStationScene.vue / Design.vue 中
 * 3 处重复的 Viewer 创建和 camera.flyTo 模式。
 *
 * 使用:
 *   const { createViewer, flyTo, flyHome } = useCesiumCore()
 *   viewer = createViewer(container, {
 *     enableTerrain: false,
 *     homeCoords: { lon: 110.93, lat: 35.12, height: 50000 }
 *   })
 */

import * as Cesium from 'cesium'
import { PERFORMANCE } from '@/config/constants'

/**
 * 底图策略（按优先级）：
 *
 * 1. 高德卫星影像（默认在线）
 *    - 免费、无需 token、国内 CDN 极速、zoom 0~18
 *    - URL: webst0{s}.is.autonavi.com（高德瓦片服务）
 *    - 适合通信基建场景：可看清地形/道路/建筑，辅助站点选址
 *
 * 2. 天地图影像 + 注记（需 VITE_TIANDITU_TOKEN）
 *    - 由 CesiumViewer.vue 的 addTiandituLayers() 按需叠加
 *
 * 3. Natural Earth II（离线兜底）
 *    - 随 Cesium 打包，vite-plugin-cesium 通过 CESIUM_BASE_URL 暴露
 *    - 分辨率低 (~2km/pixel)，仅断网时降级使用
 */

/** 高德卫星底图 — 国内免费无 token */
function buildGaodeSatelliteLayer() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
    subdomains: ['1', '2', '3', '4'],
    maximumLevel: 18,
    credit: '\u9ad8\u5fb7\u5730\u56fe',
  })
}

/** 高德街道底图（备用方案，非卫星）— 国内免费无 token */
function buildGaodeStreetLayer() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    subdomains: ['1', '2', '3', '4'],
    maximumLevel: 18,
    credit: '\u9ad8\u5fb7\u5730\u56fe',
  })
}

/** 离线降级：Natural Earth II（低分辨率兜底）*/
function buildOfflineFallback() {
  return new Cesium.TileMapServiceImageryProvider({
    url: Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII'),
  })
}

/** 标准 Cesium Viewer 选项 — 所有组件统一的默认配置 */
export const DEFAULT_VIEWER_OPTIONS = {
  animation: false,
  timeline: false,
  baseLayerPicker: false,
  geocoder: false,
  homeButton: false,
  sceneModePicker: false,
  fullscreenButton: false,
  navigationHelpButton: false,
  navigationInstructionsInitiallyVisible: false,
  vrButton: false,
  infoBox: false,
  selectionIndicator: false,
}

/** 相机高度预设 */
export const CAMERA_HEIGHTS = {
  DEFAULT: 50000,       // 初始化 / 默认位置
  OVERVIEW: 10000,      // flyToDefault / flyToLocation
  SITE_DETAIL: 5000,    // flyToSite
  REGION: 3000,         // selectRegion
  OVERHEAD: 300,        // 俯视图
  CLOSE_UP: 250,        // 近景
  ISOMETRIC: 200,       // 等距视图
  FRONT_VIEW: 150,      // 前视
  SIDE_VIEW: 150,       // 侧视
}

/**
 * 创建标准化的 Cesium Viewer 实例
 * @param {HTMLElement} container - 容器元素
 * @param {Object} [overrides={}] - 覆盖选项
 * @returns {Cesium.Viewer}
 */
export function createViewer(container, overrides = {}) {
  if (!container) throw new Error('Container element is required')

  // 默认使用高德卫星图（国内免费/无需 token/zoom 0~18，适合通信基建选址）；
  // 若调用方显式传 baseLayer:false 则退化为纯椭球。
  const options = {
    ...DEFAULT_VIEWER_OPTIONS,
    baseLayer: new Cesium.ImageryLayer(buildGaodeSatelliteLayer()),
    ...overrides,
  }
  if (overrides.baseLayer === false) delete options.baseLayer

  const viewer = new Cesium.Viewer(container, options)

  // 在线底图加载失败时自动降级到离线 Natural Earth II（低分辨率兜底）
  const layer = viewer.imageryLayers.get(0)
  if (layer) {
    layer.imageryProvider.errorEvent.addEventListener(() => {
      console.warn('[Cesium] 高德卫星底图不可用, 切换到离线 Natural Earth II')
      viewer.imageryLayers.remove(layer, false)
      viewer.imageryLayers.addImageryProvider(buildOfflineFallback(), 0)
    })
  }

  return viewer
}

/**
 * 使用标准动画时长飞到指定经纬度位置
 * @param {Cesium.Viewer} viewer - Viewer 实例
 * @param {Object} coords - { lon, lat, height }
 * @param {Object} [opts] - 额外选项
 */
export function flyTo(viewer, coords, opts = {}) {
  const { lon, lat, height = CAMERA_HEIGHTS.OVERVIEW } = coords
  const duration = opts.duration ?? PERFORMANCE.FLY_TO_DURATION / 1000

  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(lon, lat, height),
    duration,
    ...opts.orientation ? { orientation: opts.orientation } : {},
  })
}

/**
 * 飞到默认位置
 * @param {Cesium.Viewer} viewer
 * @param {Object} homeCoords - { lon, lat, height }
 */
export function flyHome(viewer, homeCoords) {
  const { lon, lat, height = CAMERA_HEIGHTS.DEFAULT } = homeCoords

  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(lon, lat, height),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-90),
      roll: 0,
    },
  })
}

export default {
  DEFAULT_VIEWER_OPTIONS,
  CAMERA_HEIGHTS,
  createViewer,
  flyTo,
  flyHome,
  // 底图构建器（供组件按需切换）
  buildGaodeSatelliteLayer,
  buildGaodeStreetLayer,
  buildOfflineFallback,
}
