/**
 * useCoverageAnalysis — 覆盖分析、热力图、图层控制、动画
 *
 * 从 Design.vue 提取的覆盖分析和可视化逻辑。
 */

import { ref, computed } from 'vue'
import * as Cesium from 'cesium'
import { ElMessage, ElMessageBox } from 'element-plus'
import { calculateCoverageMetrics, detectCoverageGaps, generateCoverageReport } from '@/utils/coverageAnalyzer.js'
import { computeDesignRaster, rsrpToColor } from '@/utils/coverageRaster.js'

export function useCoverageAnalysis({ viewer, sites, coverageOpacity, frequencyMHz = 2100, coverageRadius = 500, environment = 'URBAN' }) {
  // 图层控制
  const showSiteMarkers = ref(true)
  const showTowers = ref(true)
  const showCoverage = ref(true)
  const showLabels = ref(true)
  const animationEnabled = ref(false)

  // 覆盖分析
  const coverageMetrics = computed(() => {
    return sites.value.length > 0 ? calculateCoverageMetrics(sites.value) : null
  })

  const coverageGaps = computed(() => {
    return sites.value.length > 0 ? detectCoverageGaps(sites.value, 300) : []
  })

  /** 显示覆盖报告 */
  function showCoverageReport() {
    if (!coverageMetrics.value) {
      ElMessage.warning('没有覆盖数据')
      return
    }
    const report = generateCoverageReport(coverageMetrics.value, coverageGaps.value)
    ElMessageBox.alert(report, '覆盖质量分析报告', {
      confirmButtonText: '确定',
      type: 'info',
      dangerouslyUseHTMLString: false,
    })
  }

  /** 生成热力图（T8：真实 RSRP 栅格，替换简化椭圆） */
  function generateHeatmap() {
    const v = viewer.value
    if (!v || sites.value.length === 0) {
      ElMessage.warning('请先生成基站方案')
      return
    }
    // 清除旧热力图
    if (v.heatmapLayer) {
      v.heatmapLayer.entities.forEach(entity => {
        if (entity && entity.id && entity.id.startsWith('heatmap_')) v.entities.remove(entity)
      })
      v.heatmapLayer = null
    }

    // 用与 QGIS 一致的 Okumura-Hata 模型计算真实 RSRP 栅格
    const { cells, resolutionM } = computeDesignRaster(sites.value, {
      frequencyMHz: Number(frequencyMHz) || 2100,
      antennaGainDbi: 18,
      environment: environment || 'URBAN',
      radiusKm: (Number(coverageRadius) || 500) / 1000,
      resolutionM: 80,
      maxCells: 9000,
    })

    if (!cells.length) {
      ElMessage.warning('未生成有效覆盖栅格')
      return
    }

    // 依据站点平均纬度推算每格经/纬跨度，绘制连续着色矩形
    const avgLat = sites.value.reduce((s, it) => s + Number(it.latitude), 0) / sites.value.length
    const lonPerKm = 1.0 / (111.0 * Math.cos((avgLat * Math.PI) / 180))
    const latPerKm = 1.0 / 111.0
    const halfLon = ((resolutionM / 1000.0) * lonPerKm) / 2
    const halfLat = ((resolutionM / 1000.0) * latPerKm) / 2
    const baseAlpha = (coverageOpacity.value || 15) / 100

    const heatmapEntities = []
    cells.forEach((cell, idx) => {
      const c = rsrpToColor(cell.rsrp)
      const a = Math.max(0, Math.min(255, Math.round(c.a * baseAlpha)))
      const entity = v.entities.add({
        id: `heatmap_${idx}`,
        rectangle: {
          coordinates: Cesium.Rectangle.fromDegrees(
            cell.lon - halfLon, cell.lat - halfLat,
            cell.lon + halfLon, cell.lat + halfLat
          ),
          material: Cesium.Color.fromBytes(c.r, c.g, c.b, a),
        },
      })
      entity._rsrpColor = c // 记录原始 RGBA 供透明度调节
      heatmapEntities.push(entity)
    })

    v.heatmapLayer = { entities: heatmapEntities }
    v.scene.render()
    ElMessage.success(`已生成真实 RSRP 覆盖热力图，共 ${heatmapEntities.length} 个栅格`)
  }

  /** 清除热力图 */
  function clearHeatmap() {
    const v = viewer.value
    if (!v || !v.heatmapLayer) return
    v.heatmapLayer.entities.forEach(entity => {
      if (entity && entity.id && entity.id.startsWith('heatmap_')) v.entities.remove(entity)
    })
    v.heatmapLayer = null
    v.scene.render()
    ElMessage.info('已清除热力图')
  }

  /** 导出地图截图 */
  function exportMapScreenshot() {
    const v = viewer.value
    if (!v) {
      ElMessage.warning('地图未初始化')
      return
    }
    try {
      const canvas = v.canvas
      const imageData = canvas.toDataURL('image/png', 1.0)
      const link = document.createElement('a')
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      link.download = `m03_map_screenshot_${timestamp}.png`
      link.href = imageData
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      ElMessage.success('地图截图已导出')
    } catch (error) {
      ElMessage.error('导出失败: ' + error.message)
    }
  }

  /** 切换图层可见性 */
  function toggleLayer(layerType, visible) {
    const v = viewer.value
    if (!v) return
    v.entities.values.forEach(entity => {
      if (entity.id?.startsWith(`${layerType}_`)) {
        entity.show = visible
      }
    })
  }

  /** 更新覆盖透明度 */
  function updateCoverageOpacity(opacity) {
    const v = viewer.value
    if (!v) return
    const ratio = (opacity || 0) / 100
    v.entities.values.forEach(entity => {
      if (entity.id?.startsWith('coverage_') && entity.ellipsoid) {
        entity.ellipsoid.material = entity.ellipsoid.material.color.getValue().withAlpha(ratio)
      }
      // T8: 真实 RSRP 栅格矩形 — 用记录的原始 RGBA 重新着色
      if (entity.id?.startsWith('heatmap_') && entity.rectangle && entity._rsrpColor) {
        const c = entity._rsrpColor
        const a = Math.max(0, Math.min(255, Math.round(c.a * ratio)))
        entity.rectangle.material = Cesium.Color.fromBytes(c.r, c.g, c.b, a)
      }
    })
  }

  /** 切换旋转动画 */
  function toggleAnimation() {
    const v = viewer.value
    if (!v) return
    animationEnabled.value = !animationEnabled.value
    if (animationEnabled.value) {
      v.clock.onTick.addEventListener(rotateCamera)
    } else {
      v.clock.onTick.removeEventListener(rotateCamera)
    }
  }

  /** 旋转相机 */
  function rotateCamera(clock) {
    const v = viewer.value
    if (!v) return
    v.scene.camera.rotateRight(0.01)
  }

  /** 清理动画事件 */
  function cleanupAnimation() {
    const v = viewer.value
    if (v && animationEnabled.value) {
      v.clock.onTick.removeEventListener(rotateCamera)
    }
  }

  return {
    showSiteMarkers,
    showTowers,
    showCoverage,
    showLabels,
    animationEnabled,
    coverageMetrics,
    coverageGaps,
    showCoverageReport,
    generateHeatmap,
    clearHeatmap,
    exportMapScreenshot,
    toggleLayer,
    updateCoverageOpacity,
    toggleAnimation,
    cleanupAnimation,
  }
}
