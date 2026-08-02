/**
 * useSiteManager — 站点 CRUD、过滤、排序、Cesium 实体管理
 *
 * 从 Design.vue 提取的站点管理逻辑。
 */

import { ref, computed } from 'vue'
import * as Cesium from 'cesium'
import { ElMessage, ElMessageBox } from 'element-plus'
import { logger } from '@/utils/logger.js'

// 站点颜色循环
const COLORS = [
  Cesium.Color.fromCssColorString('#00ff00'),
  Cesium.Color.fromCssColorString('#0088ff'),
  Cesium.Color.fromCssColorString('#ffff00'),
  Cesium.Color.fromCssColorString('#ff8800'),
  Cesium.Color.fromCssColorString('#ff00ff'),
  Cesium.Color.fromCssColorString('#00ffff'),
  Cesium.Color.fromCssColorString('#ff0000'),
  Cesium.Color.fromCssColorString('#8800ff'),
]

const LEGEND_COLORS = [
  { color: '#00ff00', label: '站点 1-4' },
  { color: '#0088ff', label: '站点 5-8' },
  { color: '#ffff00', label: '站点 9-12' },
  { color: '#ff8800', label: '站点 13-16' },
]

export function useSiteManager({ viewer, coverageOpacity }) {
  const sites = ref([])
  let siteEntities = []
  let connectionEntities = []   // 管线连线实体
  let hubEntity = null          // 机房标记实体
  const externalHub = ref(null) // 后端同步过来的机房数据 { lon, lat, name }
  const selectedSite = ref(null)
  const siteCount = ref(0)
  const searchText = ref('')
  const filterValid = ref('all')
  const sortBy = ref('siteId')
  const showConnections = ref(true)  // 默认显示管线（匹配QGIS效果）

  /** 过滤+排序后的站点列表 */
  const filteredSites = computed(() => {
    let result = [...sites.value]
    if (searchText.value) {
      const keyword = searchText.value.toLowerCase()
      result = result.filter(s => s.siteId.toLowerCase().includes(keyword))
    }
    if (filterValid.value === 'valid') {
      result = result.filter(s => s.isValid === true || s.isValid === 1)
    } else if (filterValid.value === 'invalid') {
      result = result.filter(s => s.isValid !== true && s.isValid !== 1)
    }
    result.sort((a, b) => {
      if (sortBy.value === 'rsrp') return (b.rsrp || 0) - (a.rsrp || 0)
      if (sortBy.value === 'longitude') return Number(b.longitude) - Number(a.longitude)
      return (a.siteId || '').localeCompare(b.siteId || '')
    })
    return result
  })

  /** 统计信息 */
  const stats = computed(() => {
    const total = sites.value.length
    const valid = sites.value.filter(s => s.isValid === true || s.isValid === 1).length
    const invalid = total - valid
    const avgRsrp = total > 0 ? (sites.value.reduce((sum, s) => sum + (Number(s.rsrp) || 0), 0) / total).toFixed(2) : 0
    return { total, valid, invalid, avgRsrp }
  })

  /** 添加站点到地图 */
  function addSitesToMap() {
    const v = viewer.value
    if (!v) return

    // 清除旧实体
    if (siteEntities.length > 0) {
      siteEntities.forEach(entity => { if (entity) v.entities.remove(entity) })
      siteEntities = []
    }

    // 去重
    const uniqueSites = new Map()
    sites.value.forEach(site => {
      const key = `${site.siteId}_${site.longitude}_${site.latitude}`
      if (!uniqueSites.has(key)) uniqueSites.set(key, site)
    })

    Array.from(uniqueSites.values()).forEach((site, index) => {
      const color = COLORS[index % COLORS.length]
      const lon = Number(site.longitude)
      const lat = Number(site.latitude)
      const height = Number(site.towerHeight) || 45
      const isValid = site.isValid === true || site.isValid === 1
      if (isNaN(lon) || isNaN(lat)) return

      const markerColor = isValid ? color : Cesium.Color.RED

      siteEntities.push(v.entities.add({
        id: `site_${site.siteId}`,
        position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
        point: { pixelSize: 20, color: markerColor, outlineColor: Cesium.Color.WHITE, outlineWidth: 3 },
        description: `<div class="site-description"><h3>${site.siteId}</h3><p>坐标: ${lon.toFixed(4)}, ${lat.toFixed(4)}</p><p>塔高: ${height}m</p>${site.frequencyBand ? `<p>频段: ${site.frequencyBand}</p>` : ''}${site.sectorCount ? `<p>扇区: ${site.sectorCount}</p>` : ''}<p>RSRP: ${site.rsrp} dBm</p><p>状态: ${isValid ? '正常' : '故障'}</p></div>`
      }))

      siteEntities.push(v.entities.add({
        id: `label_${site.siteId}`,
        position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
        label: {
          text: site.siteId, font: '14px sans-serif', fillColor: Cesium.Color.WHITE,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE, outlineWidth: 2,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -30),
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      }))

      siteEntities.push(v.entities.add({
        id: `tower_${site.siteId}`,
        position: Cesium.Cartesian3.fromDegrees(lon, lat, height / 2),
        cylinder: { length: height, topRadius: 1.5, bottomRadius: 3, material: isValid ? Cesium.Color.GRAY.withAlpha(0.9) : Cesium.Color.RED.withAlpha(0.5) }
      }))

      siteEntities.push(v.entities.add({
        id: `coverage_${site.siteId}`,
        position: Cesium.Cartesian3.fromDegrees(lon, lat, height / 2),
        ellipsoid: {
          radii: new Cesium.Cartesian3(1500, 1500, 800),
          // 覆盖圆降低透明度，避免多站叠在一起像调色盘
          material: color.withAlpha(Math.max(0.04, (coverageOpacity?.value ?? 8) / 100)),
          outline: true, outlineColor: color.withAlpha(0.25)
        }
      }))

      siteEntities.push(v.entities.add({
        id: `coverage_ground_${site.siteId}`,
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray([
            lon, lat + 0.013, lon + 0.011, lat + 0.006,
            lon + 0.011, lat - 0.006, lon, lat - 0.013,
            lon - 0.011, lat - 0.006, lon - 0.011, lat + 0.006
          ]),
          material: isValid ? color.withAlpha(0.06) : Cesium.Color.RED.withAlpha(0.05),
          outline: true, outlineColor: isValid ? color.withAlpha(0.3) : Cesium.Color.RED.withAlpha(0.2), outlineWidth: 1
        }
      }))
    })

    bindClickHandler()
    // 自动绘制管线连线（基站→机房星型拓扑）
    if (showConnections.value) drawConnections()
  }

  /** 计算两点间距离（米，Haversine近似） */
  function calcDistanceM(lon1, lat1, lon2, lat2) {
    const R = 6371000
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLon = (lon2 - lon1) * Math.PI / 180
    const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLon/2)**2
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  }

  /**
   * 计算机房位置（优先用后端同步的机房坐标，fallback 用站点几何中心）
   * @returns {{ lon: number, lat: number, name: string, isReal: boolean }}
   */
  function getHubPoint(siteList) {
    // 优先使用后端同步的真实机房位置（QGIS 插件确定后上传的，含路由类型）
    if (externalHub.value && externalHub.value.lon != null && externalHub.value.lat != null) {
      return {
        lon: externalHub.value.lon,
        lat: externalHub.value.lat,
        name: externalHub.value.name || '机房',
        isReal: true,
        routeType: externalHub.value.routeType || 'manhattan',
      }
    }
    // fallback：所有站点的几何中心作为"虚拟机房"
    let sumLon = 0, sumLat = 0
    siteList.forEach(s => { sumLon += Number(s.longitude); sumLat += Number(s.latitude) })
    return {
      lon: sumLon / siteList.length,
      lat: sumLat / siteList.length,
      name: '机房（汇聚点）',
      isReal: false,
      routeType: 'manhattan',
    }
  }

  /**
   * 生成曼哈顿路径坐标（先水平后垂直，与 QGIS pipeline.generate_manhattan_route 一致）
   * @param {number} sLon 起点经度
   * @param {number} sLat 起点纬度
   * @param {number} eLon 终点经度(机房)
   * @param {number} eLat 终点纬度(机房)
   * @returns {Array<{lon:number, lat:number}>} 路径点列表 [起点, 拐点, 终点]
   */
  function manhattanPath(sLon, sLat, eLon, eLat) {
    // L 型：先水平移动到目标经度，再垂直移动到目标纬度
    return [
      { lon: sLon, lat: sLat },           // 起点（基站）
      { lon: eLon, lat: sLat },            // 拐点（水平到达机房经度）
      { lon: eLon, lat: eLat },            // 终点（机房）
    ]
  }

  /** 绘制管线连线（基站→机房 曼哈顿路由）
   *  与 QGIS 插件 pipeline.py 的 generate_manhattan_route 逻辑一致：
   *  每个基站沿 L 型路径连接到机房（先水平、后垂直）
   */
  function drawConnections() {
    const v = viewer.value
    if (!v || sites.value.length < 1) return

    // 先清除旧连线和旧机房标记
    clearConnections()
    clearHubMarker()

    // 确定机房位置（优先用后端同步的真实机房坐标）
    const hub = getHubPoint(sites.value)

    // ── 1. 在地图上绘制机房标记 ──
    hubEntity = v.entities.add({
      id: 'hub_machine_room',
      position: Cesium.Cartesian3.fromDegrees(hub.lon, hub.lat),
      billboard: {
        image: 'data:image/svg+xml;base64,' + btoa(`<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="%23a855f7" stroke="%23fff" stroke-width="0.5"><rect x="2" y="2" width="20" height="20" rx="3"/><path d="M9 2v20M15 2v20M2 9h20M2 15h20" stroke="%23fff" stroke-width="1" fill="none"/></svg>`),
        width: 32,
        height: 32,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: `机房 ${hub.name}`,
        font: 'bold 13px sans-serif',
        fillColor: Cesium.Color.WHITE,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        outlineWidth: 2,
        outlineColor: Cesium.Color.fromCssColorString('#a855f7').withAlpha(0.8),
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        pixelOffset: new Cesium.Cartesian2(0, 8),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString('#a855f7').withAlpha(0.85),
        backgroundPadding: new Cesium.Cartesian2(6, 3),
      },
      description: `<div style="padding:4px;font-size:12px"><b>${hub.name}</b><br/>经纬度: ${hub.lon.toFixed(6)}, ${hub.lat.toFixed(6)}<br/>类型: ${hub.isReal ? 'QGIS同步' : '几何中心(fallback)'}<br/>连接基站: ${sites.value.length}个</div>`,
    })

    // 管线颜色：橙棕色（与 QGIS 插件 pipeline_layer.py 的通信管线一致，卫星底图上清晰醒目）
    const lineColor = Cesium.Color.fromCssColorString('#E07020')

    // 路由类型：direct=直线, manhattan=L型（与 QGIS 插件 generate_manhattan_route 一致）
    const useManhattan = (hub.routeType || 'manhattan') !== 'direct'

    sites.value.forEach((site, idx) => {
      const sLon = Number(site.longitude)
      const sLat = Number(site.latitude)

      // 根据路由类型生成路径坐标
      const path = useManhattan
        ? manhattanPath(sLon, sLat, hub.lon, hub.lat)  // L 型：先水平后垂直
        : [{ lon: sLon, lat: sLat }, { lon: hub.lon, lat: hub.lat }]  // 直线
      const positions = []
      path.forEach(p => { positions.push(p.lon, p.lat) })

      // 计算实际管线路程长度
      let distM, dH = 0, dV = 0
      if (useManhattan) {
        dH = calcDistanceM(sLon, sLat, hub.lon, sLat)  // 水平段
        dV = calcDistanceM(hub.lon, sLat, hub.lon, hub.lat)  // 垂直段
        distM = dH + dV
      } else {
        distM = calcDistanceM(sLon, sLat, hub.lon, hub.lat)  // 直线欧氏距离
      }
      const distStr = distM >= 1000 ? `${(distM / 1000).toFixed(1)}km` : `${Math.round(distM)}m`

      const pipeId = `PL-${String(idx + 1).padStart(4, '0')}`
      const routeLabel = useManhattan ? '曼哈顿(L型)' : '直线'

      // 管线：2.5px 橙棕色实线、70%透明度、贴地（L型折线/直线由routeType决定）
      connectionEntities.push(v.entities.add({
        id: `conn_${pipeId}`,
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray(positions),
          width: 2.5,
          material: lineColor.withAlpha(0.75),
          clampToGround: true,
        },
        description: `<div style="padding:4px;font-size:12px"><b>${pipeId}</b><br/>长度: ${distStr}<br/>路由: ${routeLabel}<br/>方式: 直埋光缆<br/>起: ${site.siteId || site.siteName}<br/>终: ${hub.name}<br/>水平段: ${dH >= 1000 ? (dH/1000).toFixed(1)+'km' : Math.round(dH)+'m'}<br/>垂直段: ${dV >= 1000 ? (dV/1000).toFixed(1)+'km' : Math.round(dV)+'m'}</div>`,
      }))

      // 标签放在拐点处（更符合工程习惯——拐点标注桩号）
      if (distM > 300) {
        const corner = path[1] // L 型拐点
        connectionEntities.push(v.entities.add({
          id: `conn_label_${pipeId}`,
          position: Cesium.Cartesian3.fromDegrees(corner.lon, corner.lat, 15),
          label: {
            text: `${pipeId}  ${distStr}`,
            font: '10px sans-serif',
            fillColor: Cesium.Color.WHITE,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 1,
            outlineColor: Cesium.Color.BLACK.withAlpha(0.5),
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
            pixelOffset: new Cesium.Cartesian2(0, -10),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            showBackground: true,
            backgroundColor: Cesium.Color.fromCssColorString('#E07020').withAlpha(0.80),
            backgroundPadding: new Cesium.Cartesian2(4, 2),
          }
        }))
      }
    })
  }

  /** 设置后端同步的机房位置与路由类型（QGIS插件确定后上传的）
   * @param {number} lon 机房经度
   * @param {number} lat 机房纬度
   * @param {string} name 机房名称
   * @param {string} routeType 连线方式 direct=直线, manhattan=曼哈顿(L型)
   */
  function setHubPoint(lon, lat, name, routeType) {
    externalHub.value = {
      lon: Number(lon),
      lat: Number(lat),
      name: name || '机房',
      routeType: routeType || 'manhattan',  // 默认曼哈顿，与 QGIS 默认一致
    }
    // 如果已有连线，重绘以使用新的机房位置/路由类型
    if (connectionEntities.length > 0) {
      drawConnections()
    }
  }

  /** 清除机房标记 */
  function clearHubMarker() {
    const v = viewer.value
    if (v && hubEntity) {
      try { v.entities.remove(hubEntity) } catch (_) {}
      hubEntity = null
    }
  }

  /** 清除所有管线连线 + 机房标记 */
  function clearConnections() {
    const v = viewer.value
    if (v && connectionEntities.length > 0) {
      connectionEntities.forEach(entity => { try { v.entities.remove(entity) } catch (_) {} })
    }
    connectionEntities = []
    clearHubMarker()
  }

  /** 切换管线显示 */
  function toggleConnections(show) {
    showConnections.value = show
    const v = viewer.value
    if (!v) return
    connectionEntities.forEach(entity => { if (entity) entity.show = show })
    if (hubEntity) hubEntity.show = show
    if (show && connectionEntities.length === 0 && sites.value.length >= 2) {
      drawConnections()
    }
  }
  function bindClickHandler() {
    const v = viewer.value
    if (!v) return
    if (v._clickHandler) v._clickHandler.destroy()
    v._clickHandler = new Cesium.ScreenSpaceEventHandler(v.canvas)
    v._clickHandler.setInputAction((click) => {
      const picked = v.scene.pick(click.position)
      if (Cesium.defined(picked) && picked.id) {
        const entity = picked.id
        if (entity.id && entity.id.startsWith('site_')) {
          const siteId = entity.id.replace('site_', '')
          const site = sites.value.find(s => s.siteId === siteId)
          if (site) {
            selectSite(site)
            if (entity.description) v.infoBox.container.textContent = entity.description
          }
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
  }

  /** 删除站点 */
  function deleteSite(siteIndex) {
    if (siteIndex < 0 || siteIndex >= sites.value.length) {
      ElMessage.warning('请选择要删除的站点')
      return
    }
    const site = sites.value[siteIndex]
    const siteId = site.siteId
    ElMessageBox.confirm(`确定要删除站点 "${siteId}" 吗？`, '确认删除', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
    }).then(() => {
      sites.value.splice(siteIndex, 1)
      siteCount.value = sites.value.length
      removeSiteEntities(siteId)
      ElMessage.success(`已删除站点: ${siteId}`)
    }).catch(() => {})
  }

  /** 移除指定站点实体 */
  function removeSiteEntities(siteId) {
    const v = viewer.value
    if (!v) return
    const toRemove = siteEntities.filter(e => e && e.id && e.id.startsWith(`site_${siteId}`))
    toRemove.forEach(e => v.entities.remove(e))
    siteEntities = siteEntities.filter(e => !toRemove.includes(e))
    bindClickHandler()
  }

  /** 清除所有站点 */
  function clearSites() {
    const v = viewer.value
    if (v) {
      // 1) 移除已跟踪的实体
      siteEntities.forEach(entity => { if (entity) v.entities.remove(entity) })
      connectionEntities.forEach(entity => { if (entity) v.entities.remove(entity) })
      connectionEntities = []
      // 2) 兜底扫描：移除所有本工具绘制的实体，防止个别实体因异常未被跟踪而残留
      const prefix = /^(site_|label_|tower_|coverage_|conn_|hub_|machine_|heatmap_|gap_)/
      const toRemove = []
      const vals = v.entities.values
      for (let i = 0; i < vals.length; i++) {
        const e = vals[i]
        if (e && e.id && prefix.test(e.id)) toRemove.push(e)
      }
      toRemove.forEach(e => { try { v.entities.remove(e) } catch (_) {} })
      if (v._clickHandler) { v._clickHandler.destroy(); v._clickHandler = null }
      clearHubMarker()
    }
    siteEntities = []
    clearConnections() // 同时清除管线连线
    sites.value = []
    siteCount.value = 0
    selectedSite.value = null
    externalHub.value = null // 清除后端同步的机房位置，避免残留
  }

  /** 缩放到站点 */
  function zoomToSites() {
    const v = viewer.value
    if (!v || siteEntities.length === 0) return
    try {
      const entityCollection = new Cesium.EntityCollection()
      siteEntities.forEach(entity => entityCollection.add(entity))
      v.zoomTo(entityCollection)
    } catch (error) {
      logger.error('SiteManager', '缩放失败', error)
    }
  }

  /** 选择站点 */
  function selectSite(site) {
    selectedSite.value = site
    highlightSite(site.siteId)
  }

  /** 高亮站点 */
  function highlightSite(siteId) {
    siteEntities.forEach(entity => {
      if (entity.id?.startsWith('site_')) {
        entity.point.pixelSize = 20
        entity.point.outlineWidth = 3
      }
    })
    const target = siteEntities.find(e => e.id === `site_${siteId}`)
    if (target) {
      target.point.pixelSize = 30
      target.point.outlineWidth = 5
    }
  }

  /** 飞到站点 */
  function flyToSite(site) {
    const v = viewer.value
    if (!v) return
    v.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(Number(site.longitude), Number(site.latitude), 5000),
      duration: 2
    })
  }

  /** 显示站点覆盖 */
  function showSiteCoverage(site) {
    const v = viewer.value
    if (!v) return
    v.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(Number(site.longitude), Number(site.latitude), 10000),
      duration: 2
    })
  }

  /** 搜索站点 */
  function searchSite() {
    if (!searchText.value) {
      ElMessage.warning('请输入站点ID')
      return
    }
    const site = sites.value.find(s => s.siteId.toLowerCase().includes(searchText.value.toLowerCase()))
    if (site) {
      selectSite(site)
      flyToSite(site)
      ElMessage.success(`找到: ${site.siteId}`)
    } else {
      ElMessage.warning('未找到')
    }
  }

  /** RSRP 样式类 */
  function getRsrpClass(rsrp) {
    if (rsrp > -80) return 'rsrp-excellent'
    if (rsrp > -90) return 'rsrp-good'
    if (rsrp > -100) return 'rsrp-fair'
    return 'rsrp-poor'
  }

  /** 清理所有实体 (用于 onUnmounted) */
  function cleanupEntities() {
    const v = viewer.value
    if (v) {
      if (siteEntities.length > 0) {
        siteEntities.forEach(entity => { try { v.entities.remove(entity) } catch (_) {} })
        siteEntities = []
      }
      if (connectionEntities.length > 0) {
        connectionEntities.forEach(entity => { try { v.entities.remove(entity) } catch (_) {} })
        connectionEntities = []
      }
      clearHubMarker()
    }
  }

  return {
    sites,
    selectedSite,
    siteCount,
    searchText,
    filterValid,
    sortBy,
    filteredSites,
    stats,
    showConnections,       // 管线连线开关
    addSitesToMap,
    bindClickHandler,
    deleteSite,
    removeSiteEntities,
    clearSites,
    zoomToSites,
    selectSite,
    highlightSite,
    flyToSite,
    showSiteCoverage,
    searchSite,
    getRsrpClass,
    drawConnections,
    setHubPoint,            // 设置后端同步的机房位置
    clearConnections,
    toggleConnections,
    cleanupEntities,
  }
}

export { COLORS, LEGEND_COLORS }
