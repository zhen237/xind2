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
  const selectedSite = ref(null)
  const siteCount = ref(0)
  const searchText = ref('')
  const filterValid = ref('all')
  const sortBy = ref('siteId')

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
        description: `<div class="site-description"><h3>${site.siteId}</h3><p>坐标: ${lon.toFixed(4)}, ${lat.toFixed(4)}</p><p>塔高: ${height}m</p><p>RSRP: ${site.rsrp} dBm</p><p>状态: ${isValid ? '正常' : '故障'}</p></div>`
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
          material: color.withAlpha((coverageOpacity?.value ?? 15) / 100),
          outline: true, outlineColor: color.withAlpha(0.5)
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
          material: isValid ? color.withAlpha(0.2) : Cesium.Color.RED.withAlpha(0.15),
          outline: true, outlineColor: isValid ? color.withAlpha(0.6) : Cesium.Color.RED.withAlpha(0.4), outlineWidth: 2
        }
      }))
    })

    bindClickHandler()
  }

  /** 绑定点击事件 */
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
      siteEntities.forEach(entity => { if (entity) v.entities.remove(entity) })
      if (v._clickHandler) { v._clickHandler.destroy(); v._clickHandler = null }
    }
    siteEntities = []
    sites.value = []
    siteCount.value = 0
    selectedSite.value = null
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
    if (v && siteEntities.length > 0) {
      siteEntities.forEach(entity => {
        try { v.entities.remove(entity) } catch (_) {}
      })
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
    cleanupEntities,
  }
}

export { COLORS, LEGEND_COLORS }
