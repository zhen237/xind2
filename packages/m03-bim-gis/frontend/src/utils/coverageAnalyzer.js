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

  // 判断站点是否自带 rsrp 字段（后端已计算）
  const hasNativeRsrp = sites.some(s => s.rsrp != null && Number(s.rsrp) !== 0)

  let rsrpValues
  if (hasNativeRsrp) {
    // 后端已提供 RSRP 数据，直接使用
    rsrpValues = sites.map(s => Number(s.rsrp) || 0)
  } else {
    // 站点无 rsrp 字段：用 Okumura-Hata 路径损耗模型逐站计算
    // 每站取距自身 500m 处的 RSRP 作为该站代表值（城区典型小区半径）
    rsrpValues = sites.map(s => {
      const towerH = Number(s.towerHeight) || 30
      // 距离 500m 处的路径损耗 → 代表性 RSRP
      return calculateRsrpFromDistance(500, towerH)
    })
  }
  
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

/**
 * 生成覆盖质量报告（HTML 形式）
 * 用于弹窗内 HTML 展示，也可整体包裹后导出为 Word（.doc）
 * 采用浅色文档风格（白底深字），在深色弹窗中作为"文档预览卡片"展示，
 * 同时可直接被 Word 打开，避免深色背景下黑/白字不可读的问题。
 * @param {Object} metrics - 覆盖指标
 * @param {Array} gaps - 盲区列表
 * @returns {string} HTML 字符串（body 片段）
 */
export function generateCoverageReportHtml(metrics, gaps) {
  if (!metrics) {
    return '<p style="color:#718096;">暂无覆盖数据</p>'
  }

  const now = new Date().toLocaleString('zh-CN', { hour12: false })
  const fmt = (v) => (v === undefined || v === null || v === '' ? '-' : v)

  const distRows = [
    { name: '优秀', std: '&gt; -80 dBm', val: metrics.excellent, color: '#16a34a' },
    { name: '良好', std: '-80 ~ -90 dBm', val: metrics.good, color: '#0891b2' },
    { name: '一般', std: '-90 ~ -100 dBm', val: metrics.fair, color: '#d97706' },
    { name: '较差', std: '&lt; -100 dBm', val: metrics.poor, color: '#dc2626' },
  ].map(r => `
        <tr>
          <td style="padding:6px 12px;border:1px solid #e2e8f0;color:${r.color};font-weight:600;">${r.name}</td>
          <td style="padding:6px 12px;border:1px solid #e2e8f0;color:#4a5568;">${r.std}</td>
          <td style="padding:6px 12px;border:1px solid #e2e8f0;color:#1a202c;text-align:right;font-weight:600;">${fmt(r.val)}%</td>
        </tr>`).join('')

  let gapsHtml
  if (gaps && gaps.length > 0) {
    const rows = gaps.slice(0, 20).map((g, i) => `
          <tr>
            <td style="padding:5px 10px;border:1px solid #e2e8f0;color:#4a5568;text-align:center;">${i + 1}</td>
            <td style="padding:5px 10px;border:1px solid #e2e8f0;color:#1a202c;">${Number(g.longitude).toFixed(6)}</td>
            <td style="padding:5px 10px;border:1px solid #e2e8f0;color:#1a202c;">${Number(g.latitude).toFixed(6)}</td>
            <td style="padding:5px 10px;border:1px solid #e2e8f0;color:#dc2626;font-weight:600;">${fmt(g.rsrp)} dBm</td>
            <td style="padding:5px 10px;border:1px solid #e2e8f0;color:#4a5568;text-align:right;">${fmt(g.distance)} m</td>
          </tr>`).join('')
    const more = gaps.length > 20
      ? `<p style="color:#d97706;font-size:12px;margin:6px 0 0;">（共 ${gaps.length} 个盲区，仅显示前 20 个）</p>`
      : ''
    gapsHtml = `
        <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px;">
          <thead>
            <tr style="background:#edf2f7;">
              <th style="padding:6px 10px;border:1px solid #e2e8f0;color:#2d3748;text-align:center;">#</th>
              <th style="padding:6px 10px;border:1px solid #e2e8f0;color:#2d3748;text-align:left;">经度</th>
              <th style="padding:6px 10px;border:1px solid #e2e8f0;color:#2d3748;text-align:left;">纬度</th>
              <th style="padding:6px 10px;border:1px solid #e2e8f0;color:#2d3748;text-align:left;">RSRP</th>
              <th style="padding:6px 10px;border:1px solid #e2e8f0;color:#2d3748;text-align:right;">距参考站</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
        ${more}
        <p style="color:#2d3748;font-size:13px;line-height:1.7;margin:12px 0 0;">
          <strong style="color:#1565c0;">优化建议：</strong><br/>
          1. 在盲区密集区域增补微基站或室分系统；<br/>
          2. 调整现有站点天线倾角与方位角；<br/>
          3. 适当提升边缘站点发射功率。
        </p>`
  } else {
    gapsHtml = '<p style="color:#16a34a;font-size:13px;margin:8px 0 0;">✓ 未发现明显盲区，整体覆盖良好。</p>'
  }

  return `
    <div style="font-family:'Microsoft YaHei','Source Han Sans SC','Noto Sans SC',sans-serif;color:#1a202c;font-size:14px;line-height:1.6;">
      <h2 style="margin:0 0 4px;font-size:18px;color:#0f172a;border-left:4px solid #1565c0;padding-left:10px;">通信基站覆盖质量分析报告</h2>
      <p style="margin:0 0 14px;color:#718096;font-size:12px;">生成时间：${now}</p>

      <h3 style="margin:0 0 8px;font-size:15px;color:#1565c0;">一、总体指标</h3>
      <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px;">
        <tbody>
          <tr><td style="padding:6px 12px;border:1px solid #e2e8f0;color:#4a5568;width:40%;">总站点数</td><td style="padding:6px 12px;border:1px solid #e2e8f0;color:#1a202c;font-weight:600;">${fmt(metrics.totalSites)}</td></tr>
          <tr><td style="padding:6px 12px;border:1px solid #e2e8f0;color:#4a5568;">平均 RSRP</td><td style="padding:6px 12px;border:1px solid #e2e8f0;color:#1a202c;font-weight:600;">${fmt(metrics.averageRsrp)} dBm</td></tr>
          <tr><td style="padding:6px 12px;border:1px solid #e2e8f0;color:#4a5568;">RSRP 范围</td><td style="padding:6px 12px;border:1px solid #e2e8f0;color:#1a202c;font-weight:600;">${fmt(metrics.minRsrp)} ~ ${fmt(metrics.maxRsrp)} dBm</td></tr>
        </tbody>
      </table>

      <h3 style="margin:16px 0 8px;font-size:15px;color:#1565c0;">二、覆盖质量分布</h3>
      <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px;">
        <thead>
          <tr style="background:#edf2f7;">
            <th style="padding:6px 12px;border:1px solid #e2e8f0;color:#2d3748;text-align:left;">等级</th>
            <th style="padding:6px 12px;border:1px solid #e2e8f0;color:#2d3748;text-align:left;">RSRP 标准</th>
            <th style="padding:6px 12px;border:1px solid #e2e8f0;color:#2d3748;text-align:right;">占比</th>
          </tr>
        </thead>
        <tbody>${distRows}</tbody>
      </table>

      <h3 style="margin:16px 0 8px;font-size:15px;color:#1565c0;">三、盲区分析${gaps && gaps.length ? `（${gaps.length} 处）` : ''}</h3>
      ${gapsHtml}
    </div>`
}
