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
 * 构建在线高分辨率底图（OpenStreetMap）。
 * 免费、无需 token、全球覆盖、支持缩放到街道级别（zoom 0~19）。
 * 离线/网络不通时自动降级到 Natural Earth II。
 *
 * 底图优先级：OSM(在线) > 天地图(需 token) > NEII(离线兜底)
 */
function buildOnlineBaseLayer() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    subdomains: ['a', 'b', 'c'],
    maximumLevel: 19,
    credit: '\u00a9 OpenStreetMap \u8d21\u732e\u8005',
  })
}

/**
 * 构建离线降级底图（Natural Earth II）。
 * 随 Cesium 打包发布，由 vite-plugin-cesium 通过 CESIUM_BASE_URL 暴露。
 * 分辨率低（全球 ~2km/pixel），仅作为无网环境兜底——不可缩放到城市级别。
 */
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

  // 默认使用 OpenStreetMap（免费/高分辨率/无需 token，可缩至街道级）；
  // 若调用方显式传 baseLayer:false 则退化为纯椭球。
  const options = {
    ...DEFAULT_VIEWER_OPTIONS,
    baseLayer: new Cesium.ImageryLayer(buildOnlineBaseLayer()),
    ...overrides,
  }
  if (overrides.baseLayer === false) delete options.baseLayer

  const viewer = new Cesium.Viewer(container, options)

  // 在线底图加载失败时自动降级到离线 Natural Earth II（低分辨率兜底）
  const layer = viewer.imageryLayers.get(0)
  if (layer) {
    layer.imageryProvider.errorEvent.addEventListener(() => {
      console.warn('[Cesium] 在线底图(OSM)不可用, 切换到离线 Natural Earth II')
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
}
