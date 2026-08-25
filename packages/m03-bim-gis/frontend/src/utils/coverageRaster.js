/**
 * coverageRaster — 真实 RSRP 覆盖栅格计算（T8）
 *
 * 镜像 QGIS 插件 design_engine/coverage.py 的 Okumura-Hata 模型，
 * 使前端 3D 热力图与 QGIS 设计源使用同一套传播模型（强化 QGIS↔3D 同步）。
 *
 * 与旧 coverageAnalyzer.js 的区别：
 *  - 旧版用简化自由空间公式 + 固定 800m 椭圆（FR 点名短板）；
 *  - 本模块按距离变化的 Okumura-Hata 计算每格 RSRP，输出可被 Cesium 着色的栅格。
 *
 * 纯函数，无第三方依赖，可在 Node/Vitest 中单测。
 */

/**
 * 移动台天线高度修正因子 a(hr)
 */
function mobileHeightFactor(frequencyMHz, rxHeightM) {
  if (frequencyMHz <= 200) {
    return 8.29 * Math.pow(Math.log10(1.54 * rxHeightM), 2) - 1.1
  }
  return 3.2 * Math.pow(Math.log10(11.75 * rxHeightM), 2) - 4.97
}

/**
 * Okumura-Hata 路径损耗 (dB)
 * @param {number} frequencyMHz 载波频率 (MHz)
 * @param {number} distanceKm 距离 (km)
 * @param {number} txHeightM 发射天线有效高度 (m)
 * @param {number} rxHeightM 接收天线高度 (m)
 * @param {string} environment URBAN | SUBURBAN | RURAL
 */
export function okumuraHataPathLoss(
  frequencyMHz,
  distanceKm,
  txHeightM,
  rxHeightM = 1.5,
  environment = 'URBAN'
) {
  const aHr = mobileHeightFactor(frequencyMHz, rxHeightM)
  const d = Math.max(distanceKm, 0.01)

  const lUrban =
    69.55 +
    26.16 * Math.log10(frequencyMHz) -
    13.82 * Math.log10(txHeightM) +
    (44.9 - 6.55 * Math.log10(txHeightM)) * Math.log10(d) -
    aHr

  let pathLoss
  if (environment === 'SUBURBAN') {
    pathLoss = lUrban - 2 * Math.pow(Math.log10(frequencyMHz / 28.0), 2) - 5.4
  } else if (environment === 'RURAL') {
    pathLoss =
      lUrban -
      4.78 * Math.pow(Math.log10(frequencyMHz), 2) +
      18.33 * Math.log10(frequencyMHz) -
      40.94
  } else {
    pathLoss = lUrban
  }
  return pathLoss
}

/**
 * RSRP (dBm) = 发射功率 + 天线增益 - 路径损耗 - 阴影衰落
 */
export function calculateRsrp(
  txPowerDbm,
  txGainDbi,
  pathLossDb,
  rxGainDbi = 0,
  shadowFadeDb = 8
) {
  return txPowerDbm + txGainDbi - pathLossDb + rxGainDbi - shadowFadeDb
}

/**
 * 功率 W → dBm
 */
export function powerWToDbm(powerW) {
  if (powerW <= 0) return -999
  return 10 * Math.log10(powerW * 1000)
}

/**
 * RSRP → RGBA 颜色（对齐 QGIS 插件 5 级离散覆盖色阶）
 * 绿 -> 黄 -> 橙 -> 红，盲区暗红兜底
 * @param {number} rsrp RSRP (dBm)
 * @param {number} threshold 阈值（低于视为盲区）
 * @returns {{r:number,g:number,b:number,a:number}}
 */
export function rsrpToColor(rsrp, threshold = -110) {
  if (rsrp < threshold) return { r: 120, g: 0, b: 0, a: 200 }   // 盲区：暗红兜底
  // QGIS 插件 5 级离散色阶：绿 -> 黄 -> 橙 -> 红
  if (rsrp >= -50 && rsrp < -65) return { r: 0, g: 100, b: 0, a: 225 }      // 极好 #006400
  if (rsrp >= -65 && rsrp < -80) return { r: 34, g: 139, b: 34, a: 225 }    // 好 #228B22
  if (rsrp >= -80 && rsrp < -90) return { r: 255, g: 215, b: 0, a: 225 }    // 一般 #FFD700
  if (rsrp >= -90 && rsrp < -100) return { r: 255, g: 140, b: 0, a: 225 }   // 差 #FF8C00
  // -100 到 threshold
  return { r: 220, g: 20, b: 60, a: 225 }                                    // 很差 #DC143C
}

/**
 * 单站点覆盖栅格
 * @param {Object} site {lon,lat,towerHeight}
 * @param {Object} opts 射频参数
 * @returns {Array<{lon,lat,rsrp,distanceKm}>}
 */
export function computeSiteRaster(
  site,
  opts = {}
) {
  const {
    frequencyMHz = 2100,
    txPowerDbm = 43, // 对应 20W
    antennaGainDbi = 18,
    rxHeightM = 1.5,
    shadowFadeDb = 8,
    environment = 'URBAN',
    radiusKm = 2.0,
    resolutionM = 80,
  } = opts

  const lonPerKm = 1.0 / (111.0 * Math.cos((site.lat * Math.PI) / 180))
  const latPerKm = 1.0 / 111.0
  const stepLon = (resolutionM / 1000.0) * lonPerKm
  const stepLat = (resolutionM / 1000.0) * latPerKm
  const steps = Math.floor((radiusKm * 1000) / resolutionM)

  const cells = []
  for (let i = -steps; i <= steps; i++) {
    for (let j = -steps; j <= steps; j++) {
      const dKm = Math.sqrt(
        Math.pow((i * resolutionM) / 1000.0, 2) +
          Math.pow((j * resolutionM) / 1000.0, 2)
      )
      if (dKm > radiusKm) continue
      const lon = site.lon + i * stepLon
      const lat = site.lat + j * stepLat
      const pl = okumuraHataPathLoss(
        frequencyMHz,
        dKm,
        site.towerHeight || 30,
        rxHeightM,
        environment
      )
      const rsrp = calculateRsrp(txPowerDbm, antennaGainDbi, pl, 0, shadowFadeDb)
      cells.push({ lon, lat, rsrp: Math.round(rsrp * 10) / 10, distanceKm: Math.round(dKm * 1000) / 1000 })
    }
  }
  return cells
}

/**
 * 多站点合并栅格：每个网格取所有站点中的最大 RSRP
 * @param {Array} sites 站点 [{id,longitude,latitude,towerHeight,...}]
 * @param {Object} opts 射频参数 + 性能上限
 * @returns {Array<{lon,lat,rsrp,distanceKm}>}
 */
export function computeDesignRaster(sites, opts = {}) {
  const {
    frequencyMHz = 2100,
    antennaGainDbi = 18,
    rxHeightM = 1.5,
    shadowFadeDb = 8,
    environment = 'URBAN',
    radiusKm = 2.0,
    resolutionM = 80,
    maxCells = 9000,
  } = opts

  // 自适应分辨率：避免超大网格导致 Cesium 实体爆炸
  let effResolution = resolutionM
  const perSite = Math.pow((radiusKm * 1000) / effResolution, 2) * Math.PI
  if (perSite * sites.length > maxCells) {
    effResolution = Math.ceil(
      (radiusKm * 1000 * Math.sqrt(Math.PI * sites.length)) /
        Math.sqrt(maxCells)
    )
  }

  const grid = new Map()
  for (const s of sites) {
    const cells = computeSiteRaster(
      { lon: Number(s.longitude), lat: Number(s.latitude), towerHeight: Number(s.towerHeight) || 30 },
      { frequencyMHz, antennaGainDbi, rxHeightM, shadowFadeDb, environment, radiusKm, resolutionM: effResolution }
    )
    for (const c of cells) {
      const key = `${c.lon.toFixed(6)},${c.lat.toFixed(6)}`
      const prev = grid.get(key)
      if (!prev || c.rsrp > prev.rsrp) {
        grid.set(key, c)
      }
    }
  }
  return { cells: Array.from(grid.values()), resolutionM: effResolution }
}
