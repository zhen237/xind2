/**
 * 覆盖分析工具
 * 提供覆盖质量评估、盲区检测等功能
 */

/**
 * 计算覆盖质量指标
 * @param {Array} sites - 站点数据
 * @returns {Object} 覆盖指标
 */
export function calculateCoverageMetrics(sites) {
  if (!sites || sites.length === 0) {
    return null
  }

  const rsrpValues = sites.map(s => Number(s.rsrp) || 0)
  
  const excellent = rsrpValues.filter(r => r > -80).length
  const good = rsrpValues.filter(r => r > -90 && r <= -80).length
  const fair = rsrpValues.filter(r => r > -100 && r <= -90).length
  const poor = rsrpValues.filter(r => r <= -100).length
  
  const total = rsrpValues.length
  
  return {
    excellent: ((excellent / total) * 100).toFixed(1),
    good: ((good / total) * 100).toFixed(1),
    fair: ((fair / total) * 100).toFixed(1),
    poor: ((poor / total) * 100).toFixed(1),
    averageRsrp: (rsrpValues.reduce((a, b) => a + b, 0) / total).toFixed(2),
    minRsrp: Math.min(...rsrpValues).toFixed(2),
    maxRsrp: Math.max(...rsrpValues).toFixed(2),
    totalSites: total
  }
}

/**
 * 检测覆盖盲区
 * 使用蒙特卡洛采样方法
 * @param {Array} sites - 站点数据
 * @param {number} sampleCount - 采样点数
 * @returns {Array} 盲区列表
 */
export function detectCoverageGaps(sites, sampleCount = 500) {
  if (!sites || sites.length === 0) {
    return []
  }

  // 计算边界
  const lons = sites.map(s => Number(s.longitude))
  const lats = sites.map(s => Number(s.latitude))
  
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  
  const gaps = []
  
  for (let i = 0; i < sampleCount; i++) {
    // 随机采样点
    const randLon = minLon + Math.random() * (maxLon - minLon)
    const randLat = minLat + Math.random() * (maxLat - minLat)
    
    // 计算到最近站点的RSRP
    let minRsrp = -Infinity
    for (const site of sites) {
      const distance = calculateDistance(
        randLon, randLat,
        Number(site.longitude), Number(site.latitude)
      )
      const rsrp = calculateRsrpFromDistance(distance, Number(site.towerHeight) || 30)
      minRsrp = Math.max(minRsrp, rsrp)
    }
    
    // RSRP低于-100dBm视为盲区
    if (minRsrp < -100) {
      gaps.push({
        longitude: randLon,
        latitude: randLat,
        rsrp: minRsrp.toFixed(2),
        distance: (calculateDistance(
          randLon, randLat,
          Number(sites[0].longitude), Number(sites[0].latitude)
        )).toFixed(0)
      })
    }
  }
  
  return gaps
}

/**
 * 计算两点间距离（米）
 * @param {number} lon1
 * @param {number} lat1
 * @param {number} lon2
 * @param {number} lat2
 * @returns {number}
 */
function calculateDistance(lon1, lat1, lon2, lat2) {
  const R = 6371000 // 地球半径（米）
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  return R * c
}

/**
 * 基于距离估算RSRP
 * @param {number} distance - 距离（米）
 * @param {number} towerHeight - 塔高（米）
 * @returns {number} RSRP值
 */
function calculateRsrpFromDistance(distance, towerHeight) {
  // 简化的路径损耗模型
  const pl = 32.4 + 20 * Math.log10(distance / 1000) + 20 * Math.log10(2100 / 1000)
  const txPower = 46 // dBm
  const antennaGain = 18 // dBi
  const rsrp = txPower + antennaGain - pl - 10 * Math.log10(towerHeight / 30)
  return rsrp
}

/**
 * 生成覆盖质量报告
 * @param {Object} metrics - 覆盖指标
 * @param {Array} gaps - 盲区列表
 * @returns {string} 报告文本
 */
export function generateCoverageReport(metrics, gaps) {
  if (!metrics) {
    return '暂无覆盖数据'
  }
  
  let report = '=== 覆盖质量分析报告 ===\n\n'
  report += `总站点数: ${metrics.totalSites}\n`
  report += `平均RSRP: ${metrics.averageRsrp} dBm\n`
  report += `RSRP范围: ${metrics.minRsrp} ~ ${metrics.maxRsrp} dBm\n\n`
  
  report += '覆盖质量分布:\n'
  report += `  优秀(>-80): ${metrics.excellent}%\n`
  report += `  良好(-80~-90): ${metrics.good}%\n`
  report += `  一般(-90~-100): ${metrics.fair}%\n`
  report += `  较差(<-100): ${metrics.poor}%\n\n`
  
  if (gaps && gaps.length > 0) {
    report += `发现 ${gaps.length} 个潜在盲区\n`
    report += '建议:\n'
    report += '  1. 在盲区附近增加微基站\n'
    report += '  2. 调整现有站点天线倾角\n'
    report += '  3. 增加站点发射功率\n'
  } else {
    report += '未发现明显盲区，覆盖良好\n'
  }
  
  return report
}
