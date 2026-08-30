// 正向智能规划设计算法 (纯 JS 复刻 qgis-plugin/ftth/planner.py)
// 从住户需求点反推箱位/容量/路由，对比真实竣工。无第三方依赖。

export const DEFAULT_PARAMS = {
  pboMaxHomes: 24, // 单 PBO 目标覆盖户数 → 决定 PBO 数量
  bpeFanout: 6, // 单 BPE 挂接的 PBO 数 → 决定 BPE 数量
  splitRatio: 8, // 汇聚比 → BPE 芯数 = 下级总户数 / splitRatio
  coverageRadius: 350, // PBO 覆盖半径(米) → 覆盖率判定
}

const EARTH_R = 6371000.0
const toRad = (d) => (d * Math.PI) / 180

export function haversine(a, b) {
  const dLat = toRad(b[1] - a[1])
  const dLon = toRad(b[0] - a[0])
  const lat1 = toRad(a[1])
  const lat2 = toRad(b[1])
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_R * Math.asin(Math.min(1, Math.sqrt(h)))
}

export function nearest(points, q) {
  let bi = 0
  let bd = Infinity
  for (let i = 0; i < points.length; i++) {
    const d = haversine(points[i], q)
    if (d < bd) {
      bd = d
      bi = i
    }
  }
  return [bi, bd]
}

// K-means (K-means++ 初始化)。coords: [[lon,lat],...]
export function kmeans(coords, k, seed = 7) {
  const n = coords.length
  k = Math.max(1, Math.min(k, n))
  const centers = [coords[seed % n].slice()]
  while (centers.length < k) {
    const d2 = coords.map((p) =>
      Math.min(...centers.map((c) => haversine(p, c) ** 2)),
    )
    const total = d2.reduce((a, b) => a + b, 0) || 1
    const r = (((seed * 2654435761) % 1000) / 1000) * total
    let acc = 0
    let chosen = n - 1
    for (let i = 0; i < n; i++) {
      acc += d2[i]
      if (acc >= r) {
        chosen = i
        break
      }
    }
    centers.push(coords[chosen].slice())
  }
  const labels = new Array(n).fill(0)
  for (let it = 0; it < 50; it++) {
    let changed = false
    for (let i = 0; i < n; i++) {
      const [bi] = nearest(centers, coords[i])
      if (labels[i] !== bi) {
        labels[i] = bi
        changed = true
      }
    }
    for (let c = 0; c < k; c++) {
      const xs = []
      const ys = []
      for (let i = 0; i < n; i++)
        if (labels[i] === c) {
          xs.push(coords[i][0])
          ys.push(coords[i][1])
        }
      if (xs.length)
        centers[c] = [
          xs.reduce((a, b) => a + b, 0) / xs.length,
          ys.reduce((a, b) => a + b, 0) / ys.length,
        ]
    }
    if (!changed && it > 0) break
  }
  return { centers, labels }
}

const PORT_TIERS = [10, 24, 48, 96]
const CORE_TIERS = [144, 288, 576]
function tier(v, tiers) {
  for (const t of tiers) if (v <= t) return t
  return tiers[tiers.length - 1]
}

// 核心规划：返回 {pboList, bpeList, siteList, cables}
export function runPlan(demand, sites, params) {
  const coords = demand.map((d) => [d.x, d.y])
  const totalHomes = demand.reduce((a, d) => a + d.homes, 0)

  // PBO 聚类
  let kPbo = Math.max(1, Math.ceil(totalHomes / Math.max(1, params.pboMaxHomes)))
  kPbo = Math.min(kPbo, demand.length)
  const { centers: pboC, labels: pboL } = kmeans(coords, kPbo)
  const pboByLabel = {}
  demand.forEach((d, i) => {
    (pboByLabel[pboL[i]] || (pboByLabel[pboL[i]] = [])).push(d)
  })
  const siteCoords = sites.map((s) => [s.x, s.y])
  const pboList = Object.entries(pboByLabel).map(([lbl, members]) => {
    const cx = pboC[lbl][0]
    const cy = pboC[lbl][1]
    const homes = members.reduce((a, m) => a + m.homes, 0)
    const [si] = nearest(siteCoords, [cx, cy])
    return {
      code: `PLAN-PBO-${+lbl + 1}`,
      type: 'PBO',
      x: cx,
      y: cy,
      homes,
      capacityPorts: tier(Math.max(homes, 1), PORT_TIERS),
      members: members.map((m) => m.code),
      parentSite: sites[si].code,
      parentBpe: null,
    }
  })

  // BPE 聚合
  const pboCoords = pboList.map((b) => [b.x, b.y])
  let kBpe = Math.max(1, Math.ceil(pboList.length / Math.max(1, params.bpeFanout)))
  kBpe = Math.min(kBpe, pboList.length)
  const { centers: bpeC, labels: bpeL } = kmeans(pboCoords, kBpe)
  const bpeByLabel = {}
  pboList.forEach((b, i) => {
    (bpeByLabel[bpeL[i]] || (bpeByLabel[bpeL[i]] = [])).push(b)
  })
  const bpeList = Object.entries(bpeByLabel).map(([lbl, children]) => {
    const cx = bpeC[lbl][0]
    const cy = bpeC[lbl][1]
    const homes = children.reduce((a, c) => a + c.homes, 0)
    const cores = Math.ceil(homes / Math.max(1, params.splitRatio))
    const [si] = nearest(siteCoords, [cx, cy])
    const code = `PLAN-BPE-${+lbl + 1}`
    children.forEach((c) => (c.parentBpe = code))
    return {
      code,
      type: 'BPE',
      x: cx,
      y: cy,
      homes,
      capacityCores: tier(cores, CORE_TIERS),
      children: children.map((c) => c.code),
      parentSite: sites[si].code,
    }
  })

  // 树形路由
  const bpeCoords = bpeList.map((c) => [c.x, c.y])
  const cables = []
  pboList.forEach((b) => {
    const [bi, d] = nearest(bpeCoords, [b.x, b.y])
    const t = bpeList[bi]
    cables.push({
      from: [b.x, b.y],
      to: [t.x, t.y],
      fromCode: b.code,
      toCode: t.code,
      type: 'DISTRIBUTION',
      lengthM: Math.round(d),
    })
  })
  bpeList.forEach((c) => {
    const [si, d] = nearest(siteCoords, [c.x, c.y])
    const t = sites[si]
    cables.push({
      from: [c.x, c.y],
      to: [t.x, t.y],
      fromCode: c.code,
      toCode: t.code,
      type: 'TRANSPORT',
      lengthM: Math.round(d),
    })
  })

  return { pboList, bpeList, siteList: sites, cables }
}

// 对比评估（实时）。realStats: {pboReal, bpeReal, cableLenReal}
export function evaluatePlan(plan, demand, realStats, params) {
  const plannedLen = plan.cables.reduce((a, c) => a + c.lengthM, 0)
  const pboCoords = plan.pboList.map((b) => [b.x, b.y])
  let covered = 0
  demand.forEach((d) => {
    const [, dist] = nearest(pboCoords, [d.x, d.y])
    if (dist <= params.coverageRadius) covered++
  })
  const coverageRate = demand.length ? covered / demand.length : 0

  // 聚类纯度：算法 PBO 簇内 IMB 的真实 PBO 归属多数一致度
  let correct = 0
  let totalLabeled = 0
  const byCode = {}
  demand.forEach((d) => (byCode[d.code] = d))
  plan.pboList.forEach((b) => {
    const votes = {}
    b.members.forEach((mc) => {
      const rb = byCode[mc]?.real_bpe
      if (rb) {
        votes[rb] = (votes[rb] || 0) + 1
        totalLabeled++
      }
    })
    if (Object.keys(votes).length)
      correct += Math.max(...Object.values(votes))
  })
  const purity = totalLabeled ? correct / totalLabeled : 0

  return {
    pboPlanned: plan.pboList.length,
    pboReal: realStats.pboReal,
    bpePlanned: plan.bpeList.length,
    bpeReal: realStats.bpeReal,
    cableLenPlannedM: Math.round(plannedLen),
    cableLenRealM: realStats.cableLenReal,
    coverageRate,
    clusterPurity: purity,
    demandCount: demand.length,
    totalHomes: demand.reduce((a, d) => a + d.homes, 0),
  }
}
