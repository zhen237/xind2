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
 * 底图策略（卫星优先 + 多级兜底）：
 *
 * 1. ArcGIS World Imagery（默认首选）★ 最稳定
 *    - Esri 官方瓦片服务，全球 CDN，无需 token
 *    - 卫星影像，zoom 0~19
 *    - URL: server.arcgisonline.com
 *
 * 2. 高德卫星影像（首选兜底）★ 国内可达
 *    - webst0{s}.is.autonavi.com，卫星影像，无需 token
 *    - 注：中国境内为 GCJ-02 偏移坐标系；境外覆盖弱
 *
 * 3. CartoDB Positron（矢量可见兜底）
 *    - 全球 CDN，轻量矢量风格，无需 token
 *    - URL: basemaps.cartocdn.com
 *
 * 4. Natural Earth II（离线兜底）
 *    - 随 Cesium 打包，断网时降级使用
 *
 * 注：天地图影像（t0.tianditu.gov.cn/DataServer）当前内置 token 为「服务器端」Key，
 *     浏览器端调用返回 code:301013「权限类型错误」，无法作为浏览器底图，故不参与
 *     降级链；buildTiandituImagery / buildTiandituLabels 保留，待用户提供「浏览器端」
 *     Key（并在天地图控制台绑定授权域名）后再启用。
 */

/**
 * 天地图 token（国家地理信息公共服务平台）。
 * 优先从环境变量读取，缺失时回退到内置值。
 *
 * ⚠️ 当前内置 token 是「服务器端」Key：浏览器端携带 UA 调用会返回
 *    {"msg":"权限类型错误","code":301013}（curl 不带 UA 时才 200，是假象），
 *    因此浏览器永远拿不到瓦片，不能作为浏览器底图。
 *    若要恢复天地图：需在天地图控制台新建「浏览器端」Key 并绑定授权域名，
 *    再经 VITE_TIANDITU_TOKEN 注入，然后把 buildBaseLayer() 改回
 *    buildTiandituImagery()。
 */
const TIANDITU_TOKEN =
  (import.meta.env && import.meta.env.VITE_TIANDITU_TOKEN) ||
  '5ca1282d53249d3b0ac07f6b68c9c38b'

/**
 * 天地图影像底图。
 * 注：需「浏览器端」Key；当前内置为服务器端 Key，会返回 301013，暂不可用。
 * 保留此函数，待用户提供浏览器端 Key 后可按需启用。
 */
function buildTiandituImagery() {
  return new Cesium.UrlTemplateImageryProvider({
    url: `https://t0.tianditu.gov.cn/DataServer?T=img_w&x={x}&y={y}&l={z}&tk=${TIANDITU_TOKEN}`,
    maximumLevel: 18,
    credit: '天地图 GS(2023)332号',
  })
}

/** 天地图影像注记（路名/地名，可叠加在影像之上）。同样需「浏览器端」Key。*/
function buildTiandituLabels() {
  return new Cesium.UrlTemplateImageryProvider({
    url: `https://t0.tianditu.gov.cn/DataServer?T=cia_w&x={x}&y={y}&l={z}&tk=${TIANDITU_TOKEN}`,
    maximumLevel: 18,
    credit: '天地图注记',
  })
}

/** ArcGIS World Imagery（全球最稳定免费卫星源，无需 token，作为首选底图）*/
function buildArcGISImagery() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    maximumLevel: 19,
    credit: 'Esri World Imagery',
  })
}

/**
 * 高德卫星影像（国内可达的首选兜底，无需 token）。
 * 注：中国境内为 GCJ-02 偏移坐标系（与 WGS84 卫星影像存在整体偏移），
 *     作降级兜底可接受；境外覆盖弱。
 */
function buildGaodeImagery() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
    subdomains: ['1', '2', '3', '4'],
    maximumLevel: 18,
    credit: '高德地图卫星影像',
  })
}

/**
 * 默认底图 —— ArcGIS World Imagery（全球 CDN 卫星影像，无需 token）。
 * 天地图当前内置 token 是「服务器端」Key，浏览器端返回 301013 权限错误，
 * 故不作默认；若用户提供「浏览器端」Key，可将此处改回 buildTiandituImagery()。
 */
function buildBaseLayer() {
  return buildArcGISImagery()
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

  // 默认使用 ArcGIS World Imagery（全球最稳定的免费卫星底图，无需 token）；
  // 若调用方显式传 baseLayer:false 则退化为纯椭球。
  const options = {
    ...DEFAULT_VIEWER_OPTIONS,
    baseLayer: new Cesium.ImageryLayer(buildBaseLayer()),
    ...overrides,
  }
  if (overrides.baseLayer === false) delete options.baseLayer

  const viewer = new Cesium.Viewer(container, options)

  // ── 底图健康检测 + 多级自动降级链 ──
  // 首选 ArcGIS World Imagery → 高德卫星 → CartoDB Positron → Natural Earth II(离线)
  // 健康判据不能依赖 readyPromise：UrlTemplateImageryProvider.readyPromise 构造时即
  // resolve，真实瓦片常在回调执行前就加载完（本机 ArcGIS 单瓦片约 1.6s、首屏数十片），
  // 会导致"队列清空时 tilesLoaded 仍为 0"的竞态误判，进而把好底图误降级。
  // 改为只看 globe.tileLoadProgressEvent：只要「队列曾非空(remaining>0) 且随后清空
  // (remaining===0)」即证明确有瓦片成功出图（sawQueue && remaining===0）。
  // 触发策略：错误驱动优先（累积瓦片错误达阈值即降级），超时兜底（避免慢网误降级）。
  const layer = viewer.imageryLayers.get(0)
  if (layer) {
    const PRIMARY_TIMEOUT_MS = 10000     // 首选底图观察窗（放宽，避免慢网误降级）
    const TILE_ERROR_THRESHOLD = 6       // 累积瓦片错误达阈值 → 判定该级失败
    const FALLBACK_DELAY_MS = 8000       // 降级链每一级的观察窗

    let sawQueue = false       // 是否曾出现 remaining > 0（确有瓦片入队）
    let settled = false        // 已确认当前底图正常 → 停止降级
    let chainStarted = false   // 降级链已启动
    let tileErrors = 0         // 首选层累积瓦片错误数

    // 降级链：卫星优先（ArcGIS 已是首选），末尾为永不失败的离线兜底
    const FALLBACK_CHAIN = [
      { name: '高德卫星影像', build: buildGaodeImagery },
      { name: 'CartoDB Positron', build: buildCartoDBLayer },
      { name: 'Natural Earth II(离线)', build: buildOfflineFallback },
    ]

    // 逐级降级：每一级独立观察窗，窗口内未确认健康则继续降级。
    function applyLevel(levelIndex, currentLayer) {
      if (settled || levelIndex >= FALLBACK_CHAIN.length) return
      const step = FALLBACK_CHAIN[levelIndex]
      if (currentLayer) viewer.imageryLayers.remove(currentLayer, false)
      console.warn(`[Cesium] 降级到 ${step.name}`)
      const nextLayer = viewer.imageryLayers.addImageryProvider(step.build(), 0)

      let levelSawQueue = false
      let levelErrors = 0

      function cleanupLevel() {
        clearTimeout(levelTimer)
        if (removeLevelListener) removeLevelListener()
        if (removeLevelErrorListener) removeLevelErrorListener()
      }

      const removeLevelListener = viewer.scene.globe.tileLoadProgressEvent.addEventListener(
        (remaining) => {
          if (settled) return
          if (remaining > 0) {
            levelSawQueue = true
          } else if (levelSawQueue) {
            settled = true      // 该级确有瓦片成功出图
            cleanupLevel()
          }
        }
      )
      const removeLevelErrorListener = nextLayer.imageryProvider.errorEvent
        ? nextLayer.imageryProvider.errorEvent.addEventListener(() => {
            if (settled) return
            levelErrors++
            if (levelErrors >= TILE_ERROR_THRESHOLD) {
              cleanupLevel()
              applyLevel(levelIndex + 1, nextLayer)
            }
          })
        : undefined
      const levelTimer = setTimeout(() => {
        cleanupLevel()
        if (settled) return
        applyLevel(levelIndex + 1, nextLayer)
      }, FALLBACK_DELAY_MS)
    }

    // 启动降级链（错误阈值触发 / 超时兜底共用）
    function startChain(reason) {
      if (settled || chainStarted) return
      chainStarted = true
      if (removeProgressListener) removeProgressListener()
      if (removeErrorListener) removeErrorListener()
      clearTimeout(fallbackTimer)
      const providerName = layer.imageryProvider.credit?.text || '底图'
      console.warn(`[Cesium] ${providerName} ${reason}，启动降级`)
      viewer.imageryLayers.remove(layer, false)
      applyLevel(0, null)
    }

    // 首选层健康判定（不依赖 readyPromise，消除竞态）
    const removeProgressListener = viewer.scene.globe.tileLoadProgressEvent.addEventListener(
      (remainingTilesToLoad) => {
        if (settled) return
        if (remainingTilesToLoad > 0) {
          sawQueue = true
        } else if (sawQueue) {
          settled = true        // 确实排过队且已排空 → 有瓦片成功出图
          clearTimeout(fallbackTimer)
          removeProgressListener()
          if (removeErrorListener) removeErrorListener()
        }
      }
    )

    // 错误计数：错误驱动优先触发降级
    const removeErrorListener = layer.imageryProvider.errorEvent
      ? layer.imageryProvider.errorEvent.addEventListener(() => {
          if (settled || chainStarted) return
          tileErrors++
          if (tileErrors >= TILE_ERROR_THRESHOLD) {
            startChain(`瓦片错误达 ${TILE_ERROR_THRESHOLD} 次`)
          }
        })
      : undefined

    // 超时兜底（最终安全网）：PRIMARY_TIMEOUT_MS 内未确认健康 → 启动降级链
    const fallbackTimer = setTimeout(() => {
      startChain(`${PRIMARY_TIMEOUT_MS}ms 内无有效瓦片`)
    }, PRIMARY_TIMEOUT_MS)
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
  buildGaodeImagery,
  buildCartoDBLayer,
  buildOSMLayer,
  buildOfflineFallback,
}
