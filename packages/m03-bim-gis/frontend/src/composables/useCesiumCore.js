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

/**
 * 底图选择：
 *   开发/生产 → 高德卫星影像
 *   开发环境瓦片走 Vite 代理（/gaode-tile）注入 CORS 头，解决截图黑屏
 *   生产环境需 nginx 反向代理做同样的事（或接受无底图截图）
 */
function buildBaseLayer() {
  // 统一使用高德卫星底图，开发环境通过 Vite 代理解决跨域
  const tileUrl = import.meta.env.DEV
    ? '/gaode-tile/appmaptile?style=6&x={x}&y={y}&z={z}'  // 走 vite proxy → 注入 CORS
    : 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}'  // 直连

  console.log(`[Cesium] ${import.meta.env.DEV ? 'DEV（代理+CORS）' : 'PROD'} 模式：使用高德卫星底图`)

  return new Cesium.UrlTemplateImageryProvider({
    url: tileUrl,
    subdomains: import.meta.env.DEV ? [] : ['1', '2', '3', '4'],
    maximumLevel: 18,
    credit: '\u9ad8\u5fb7\u536b\u661f',
  })
}

/** 别名（保持向后兼容）*/
const buildGaodeSatelliteLayer = buildBaseLayer
const buildGaodeStreetLayer = buildBaseLayer

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
  // 开启 preserveDrawingBuffer 以支持 canvas.toDataURL() 截图导出
  // （WebGL 默认每帧清缓冲区，不开启则 toDataURL 读到黑色空帧）
  contextOptions: {
    webgl: {
      preserveDrawingBuffer: true,
    },
  },
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
