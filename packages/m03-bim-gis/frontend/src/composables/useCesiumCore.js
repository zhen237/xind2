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
 * 构建离线 Natural Earth II 底图图层。
 * 该资源随 Cesium 打包发布（Build/Cesium/Assets/Textures/NaturalEarthII），
 * 由 vite-plugin-cesium 在 dev/build 时通过 CESIUM_BASE_URL 暴露，
 * 因此无需 Cesium Ion token、也无需联网即可渲染地球。
 *
 * 这是修复「无 Ion token 时地球空白」的核心：Cesium ≥1.104 的默认底图
 * 是走 Ion 的 Bing 地图，没有 token 就会加载失败导致整片空白。
 */
function buildOfflineBaseLayer() {
  return Cesium.ImageryLayer.fromProviderAsync(
    Cesium.TileMapServiceImageryProvider.fromUrl(
      Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII')
    ),
    { name: 'Natural Earth II (离线)' }
  )
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

  // 默认注入离线底图；若调用方显式传 baseLayer:false 则退化为纯椭球（空白地球）
  const options = {
    ...DEFAULT_VIEWER_OPTIONS,
    baseLayer: buildOfflineBaseLayer(),
    ...overrides,
  }
  if (overrides.baseLayer === false) delete options.baseLayer

  return new Cesium.Viewer(container, options)
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
