/**
 * useCoverageAnalysis — 覆盖分析、热力图、图层控制、动画
 *
 * 从 Design.vue 提取的覆盖分析和可视化逻辑。
 */

import { ref, computed } from 'vue'
import * as Cesium from 'cesium'
import { ElMessage, ElMessageBox } from 'element-plus'
import { calculateCoverageMetrics, detectCoverageGaps, generateCoverageReportHtml } from '@/utils/coverageAnalyzer.js'
import { computeDesignRaster, rsrpToColor } from '@/utils/coverageRaster.js'

/**
 * 将 HTML 报告导出为 Word 文档（.doc）
 * 纯前端实现：Blob + application/msword，无需后端
 * @param {string} bodyHtml 报告 HTML（来自 generateCoverageReportHtml）
 * @param {string} [filename] 导出文件名
 */
function exportReportAsWord(bodyHtml, filename = '覆盖质量分析报告.doc') {
  const header = "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><title>覆盖质量分析报告</title><style>body{font-family:'Microsoft YaHei','Source Han Sans SC',sans-serif;margin:24px;}</style></head><body>"
  const footer = '</body></html>'
  const fullHtml = header + bodyHtml + footer
  const blob = new Blob(['﻿' + fullHtml], { type: 'application/msword' })
  // 注：'﻿' 为 UTF-8 BOM，确保 Word 正确识别编码
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  ElMessage.success('报告已导出为 Word 文档')
}

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

  /** 显示覆盖报告（HTML 弹窗预览 + 一键导出 Word）
   *  弹窗定位在左上区域，避免遮挡地图和底部面板 */
  function showCoverageReport() {
    if (!coverageMetrics.value) {
      ElMessage.warning('没有覆盖数据')
      return
    }
    const html = generateCoverageReportHtml(coverageMetrics.value, coverageGaps.value)
    ElMessageBox.confirm(html, '覆盖质量分析报告', {
      confirmButtonText: '导出 Word (.doc)',
      cancelButtonText: '关闭',
      dangerouslyUseHTMLString: true,
      customClass: 'coverage-report-box',
      closeOnClickModal: false,
      // 定位到左上区域：不遮挡地图中心、不盖底部面板
      customStyle: { marginTop: '8vh', marginLeft: '4vw' },
    }).then(() => {
      exportReportAsWord(html)
    }).catch(() => {})
  }

  /** 生成热力图（T8：真实 RSRP 栅格，替换简化椭圆）
   * @param {number} [radiusOverride] 覆盖半径覆盖值(m)，不传则用初始化时的 coverageRadius
   * @param {number} [freqOverride]   频段覆盖值(MHz)，不传则用初始化时的 frequencyMHz
   */
  function generateHeatmap(radiusOverride, freqOverride) {
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
    const frequency = Number(freqOverride) || Number(frequencyMHz) || 2100
    const { cells, resolutionM } = computeDesignRaster(sites.value, {
      frequencyMHz: frequency,
      antennaGainDbi: 18,
      environment: environment || 'URBAN',
      radiusKm: (Number(radiusOverride) || Number(coverageRadius) || 500) / 1000,
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
    const baseAlpha = (coverageOpacity.value || 45) / 100   // 默认 45%（原 15%，卫星底图下太淡）

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

  /** 导出地图截图（含底图） */
  async function exportMapScreenshot() {
    const v = viewer.value
    if (!v) {
      ElMessage.warning('地图未初始化')
      return
    }
    try {
      ElMessage.info('正在渲染截图，请稍候…')

      // 多帧渲染确保所有瓦片写入帧缓冲
      for (let i = 0; i < 6; i++) {
        v.scene.render()
        await new Promise(r => requestAnimationFrame(r))
      }
      // 额外等 300ms 让 GPU 合成完成
      await new Promise(r => setTimeout(r, 300))

      const canvas = v.canvas

      // 尝试导出 — OSM 瓦片支持 CORS 时不报错，高德瓦片会抛 SecurityError
      let dataUrl
      try {
        dataUrl = canvas.toDataURL('image/png', 1.0)
      } catch (securityErr) {
        // 跨域瓦片导致 tainted canvas → 给用户明确提示
        console.warn('[截图] Canvas 被跨域瓦片污染 (tainted)，降级为仅矢量层导出')
        ElMessage.warning(
          '底图瓦片来自跨域源（高德），浏览器禁止读取其像素。' +
          '开发环境已自动切换为 OSM 底图解决此问题。请刷新页面后重试。'
        )
        // 仍然尝试导出矢量部分（底图区域会是透明/黑色）
        dataUrl = canvas.toDataURL('image/png', 1.0)
      }

      const link = document.createElement('a')
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      link.download = `m03_map_screenshot_${timestamp}.png`
      link.href = dataUrl
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      ElMessage.success('地图截图已导出')

      // ⚠️ toDataURL() 会破坏 WebGL 帧缓冲状态，必须强制重新渲染
      // 否则底图瓦片纹理丢失 → 页面变成蓝底/黑底
      v.scene.render()
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
