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
 * 底图策略（国内最佳 + 全球兜底）：
 *
 * 1. 天地图影像（默认首选）★ 国内最佳
 *    - 国家地理信息公共服务平台，国内网络最稳定、最清晰
 *    - 卫星影像，zoom 0~18，需 token（VITE_TIANDITU_TOKEN）
 *    - URL: t0.tianditu.gov.cn/DataServer
 *
 * 2. ArcGIS World Imagery（全球兜底）★ 最稳定
 *    - Esri 官方瓦片服务，全球 CDN，中国网络可达
 *    - 卫星影像，zoom 0~19，无需 token
 *    - URL: server.arcgisonline.com
 *
 * 3. CartoDB Positron（矢量底图备选）
 *    - 全球 CDN，轻量矢量风格，无需 token
 *    - URL: basemaps.cartocdn.com
 *
 * 4. OpenStreetMap（第三备选）
 *    - 经典 OSM 瓦片，全球覆盖
 *
 * 5. Natural Earth II（离线兜底）
 *    - 随 Cesium 打包，断网时降级使用
 */

/**
 * 天地图 token（国家地理信息公共服务平台）。
 * 优先从环境变量读取，缺失时回退到内置值。
 * 注意：内置 token 不应公开泄露，轮换请改 VITE_TIANDITU_TOKEN。
 */
const TIANDITU_TOKEN =
  (import.meta.env && import.meta.env.VITE_TIANDITU_TOKEN) ||
  '5ca1282d53249d3b0ac07f6b68c9c38b'

/** 天地图影像底图（国内最佳卫星影像，需 token）*/
function buildTiandituImagery() {
  console.log('[Cesium] 使用天地图影像作为默认底图（国内最佳）')
  return new Cesium.UrlTemplateImageryProvider({
    url: `https://t0.tianditu.gov.cn/DataServer?T=img_w&x={x}&y={y}&l={z}&tk=${TIANDITU_TOKEN}`,
    maximumLevel: 18,
    credit: '天地图 GS(2023)332号',
  })
}

/** 天地图影像注记（路名/地名，可叠加在影像之上）*/
function buildTiandituLabels() {
  return new Cesium.UrlTemplateImageryProvider({
    url: `https://t0.tianditu.gov.cn/DataServer?T=cia_w&x={x}&y={y}&l={z}&tk=${TIANDITU_TOKEN}`,
    maximumLevel: 18,
    credit: '天地图注记',
  })
}

/** ArcGIS World Imagery（全球最稳定免费卫星源，无需 token，作为国内兜底）*/
function buildArcGISImagery() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    maximumLevel: 19,
    credit: '\u963f\u91cc Esri \u536b\u661f\u5f71\u50cf',
  })
}

/**
 * 默认底图 —— 天地图影像（国内最佳，需 token）
 * 若需要全局/离线场景可回退到 ArcGIS / CartoDB / OSM。
 */
function buildBaseLayer() {
  return buildTiandituImagery()
}

/** CartoDB Positron 矢量底图（轻量备选）*/
function buildCartoDBLayer() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    maximumLevel: 19,
    credit: 'CartoDB Positron',
  })
}

/** 离线兜底：Natural Earth II（低分辨率但永不失败）*/
function buildOfflineFallback() {
  return new Cesium.TileMapServiceImageryProvider({
    url: Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII'),
  })
}

/** OpenStreetMap 经典瓦片（第三备选）*/
function buildOSMLayer() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://{a,b,c}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    maximumLevel: 19,
    credit: 'OpenStreetMap',
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

  // 默认使用天地图影像（国内最佳免费卫星底图，需 token）；
  // 若调用方显式传 baseLayer:false 则退化为纯椭球。
  const options = {
    ...DEFAULT_VIEWER_OPTIONS,
    baseLayer: new Cesium.ImageryLayer(buildBaseLayer()),
    ...overrides,
  }
  if (overrides.baseLayer === false) delete options.baseLayer

  const viewer = new Cesium.Viewer(container, options)

  // ── 底图健康检测 + 五级自动降级链 ──
  // 天地图 → ArcGIS → CartoDB Positron → OpenStreetMap → Natural Earth II(离线)
  // Cesium 的 imageryProvider.errorEvent 对"返回200但空白"/"代理超时"等静默失败不触发
  // 改用 tileLoadProgressEvent 监听实际瓦片加载情况，配合超时兜底
  const layer = viewer.imageryLayers.get(0)
  if (layer) {
    let tilesLoaded = 0
    let fallbackDone = false
    const FALLBACK_DELAY_MS = 5000  // 5 秒内无有效瓦片则判定失败

    // 方式 A：监听瓦片加载进度事件（最可靠）
    const removeProgressListener = viewer.scene.globe.tileLoadProgressEvent.addEventListener(
      (remainingTilesToLoad) => {
        if (fallbackDone) return
        if (remainingTilesToLoad === 0 && tilesLoaded > 0) {
          tilesLoaded = 999  // 标记为已确认正常
        }
      }
    )

    // 方式 B：监听 readyPromise（辅助）
    if (layer.imageryProvider.readyPromise) {
      layer.imageryProvider.readyPromise.then(() => {
        if (!fallbackDone) tilesLoaded = Math.max(tilesLoaded, 1)
      }).catch(() => {})
    }

    // 方式 C：超时兜底（最终安全网）—— 五级降级
    const fallbackTimer = setTimeout(() => {
      if (fallbackDone) return
      fallbackDone = true
      removeProgressListener()

      const providerName = layer.imageryProvider.credit?.text || '底图'
      console.warn(`[Cesium] ${providerName} ${FALLBACK_DELAY_MS}ms 内无有效瓦片，启动降级`)

      // 第 1 级：ArcGIS World Imagery（全球 CDN，国内可兜底）
      viewer.imageryLayers.remove(layer, false)
      const arcgisLayer = viewer.imageryLayers.addImageryProvider(buildArcGISImagery(), 0)

      const timer1 = setTimeout(() => {
        if (fallbackDone) return
        console.warn('[Cesium] ArcGIS 未生效，降级到 CartoDB')
        viewer.imageryLayers.remove(arcgisLayer, false)
        const cartoLayer = viewer.imageryLayers.addImageryProvider(buildCartoDBLayer(), 0)

        const timer2 = setTimeout(() => {
          if (fallbackDone) return
          console.warn('[Cesium] CartoDB 未生效，降级到 OpenStreetMap')
          viewer.imageryLayers.remove(cartoLayer, false)
          const osmLayer = viewer.imageryLayers.addImageryProvider(buildOSMLayer(), 0)

          const timer3 = setTimeout(() => {
            if (fallbackDone) return
            console.warn('[Cesium] OSM 也未生效，最终降级到离线 Natural Earth II')
            viewer.imageryLayers.remove(osmLayer, false)
            viewer.imageryLayers.addImageryProvider(buildOfflineFallback(), 0)
          }, FALLBACK_DELAY_MS)

          if (osmLayer.imageryProvider.readyPromise) {
            osmLayer.imageryProvider.readyPromise.then(() => { clearTimeout(timer3) }).catch(() => {})
          }
        }, FALLBACK_DELAY_MS)

        if (cartoLayer.imageryProvider.readyPromise) {
          cartoLayer.imageryProvider.readyPromise.then(() => { clearTimeout(timer2) }).catch(() => {})
        }
      }, FALLBACK_DELAY_MS)

      if (arcgisLayer.imageryProvider.readyPromise) {
        arcgisLayer.imageryProvider.readyPromise.then(() => { clearTimeout(timer1) }).catch(() => {})
      }
    }, FALLBACK_DELAY_MS)

    // 底图确认正常后清除所有定时器
    const checkInterval = setInterval(() => {
      if (tilesLoaded >= 999 || fallbackDone) {
        clearInterval(checkInterval)
        clearTimeout(fallbackTimer)
        removeProgressListener()
      }
    }, 1000)
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
  buildBaseLayer,
  buildTiandituImagery,
  buildTiandituLabels,
  buildArcGISImagery,
  buildCartoDBLayer,
  buildOSMLayer,
  buildOfflineFallback,
}
