/**
 * 数据导出工具
 * 支持JSON、CSV、GeoJSON格式导出
 */

import { logger } from '@/utils/logger'

/**
 * 导出为JSON文件
 * @param {Object} data - 导出数据
 * @param {string} filename - 文件名
 */
export function exportAsJSON(data, filename = 'design-plan') {
  const json = JSON.stringify(data, null, 2)
  downloadFile(json, `${filename}.json`, 'application/json')
}

/**
 * 导出为CSV文件
 * @param {Array} sites - 站点数据
 * @param {string} filename - 文件名
 */
export function exportAsCSV(sites, filename = 'sites') {
  if (!sites || sites.length === 0) {
    logger.warn('ExportUtils', '没有数据可导出')
    return
  }

  const headers = ['站点ID', '经度', '纬度', '塔高(m)', 'RSRP(dBm)', '状态', '场景']
  const rows = sites.map(site => [
    site.siteId,
    site.longitude,
    site.latitude,
    site.towerHeight || 30,
    site.rsrp || 0,
    site.isValid ? '正常' : '故障',
    site.scenario || 'urban'
  ])

  const csv = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n')

  downloadFile(csv, `${filename}.csv`, 'text/csv;charset=utf-8')
}

/**
 * 导出为GeoJSON文件
 * @param {Object} data - 包含sites的数据
 * @param {string} filename - 文件名
 */
export function exportAsGeoJSON(data, filename = 'sites') {
  if (!data.sites || data.sites.length === 0) {
    logger.warn('ExportUtils', '没有数据可导出')
    return
  }

  const geojson = {
    type: 'FeatureCollection',
    features: data.sites.map(site => ({
      type: 'Feature',
      properties: {
        siteId: site.siteId,
        rsrp: site.rsrp,
        towerHeight: site.towerHeight,
        isValid: site.isValid,
        scenario: site.scenario
      },
      geometry: {
        type: 'Point',
        coordinates: [
          parseFloat(site.longitude),
          parseFloat(site.latitude)
        ]
      }
    }))
  }

  const geojsonStr = JSON.stringify(geojson, null, 2)
  downloadFile(geojsonStr, `${filename}.geojson`, 'application/geo+json')
}

/**
 * 下载文件
 * @param {string} content - 文件内容
 * @param {string} filename - 文件名
 * @param {string} mimeType - MIME类型
 */
function downloadFile(content, filename, mimeType) {
  const BOM = '\uFEFF'
  const blob = new Blob([BOM + content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  // 释放URL对象
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/**
 * 构建导出数据对象
 * @param {Object} params - 页面状态
 * @returns {Object}
 */
export function buildExportData(params) {
  return {
    metadata: {
      exportedAt: new Date().toISOString(),
      appName: 'M03 BIM+GIS Design Tool',
      version: '1.0'
    },
    location: params.location,
    params: params.generateParams,
    sites: params.sites,
    stats: params.stats
  }
}
