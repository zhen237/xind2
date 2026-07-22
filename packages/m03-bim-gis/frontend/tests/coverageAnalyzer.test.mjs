/**
 * coverageAnalyzer 单元测试（#187 可信度 / #189 补单测）
 * 纯 Node ESM 运行，无需测试框架依赖：
 *   node tests/coverageAnalyzer.test.mjs
 * 或通过 npm：npm test
 */
import {
  calculateSiteConfidence,
  calculateCoverageConfidence,
  RSRP_COVERAGE_THRESHOLD,
  calculateCoverageMetrics,
  detectCoverageGaps,
} from '../src/utils/coverageAnalyzer.js'

let passed = 0
let failed = 0
function assert(cond, msg) {
  if (cond) {
    passed++
    console.log('  ✓', msg)
  } else {
    failed++
    console.error('  ✗', msg)
  }
}
function approx(a, b, eps = 1) {
  return Math.abs(a - b) <= eps
}

console.log('— calculateSiteConfidence —')
// 实测 + 高裕量 → 接近 99 封顶
assert(calculateSiteConfidence({ rsrp: -75, rsrpSource: 'measured' }, true) === 99, '实测 RSRP=-75 → 置信度 99(封顶)')
// 仿真 + 边缘(裕量≈2dB) → 约 46
const edge = calculateSiteConfidence({ rsrp: -98, rsrpSource: 'simulated' }, true)
assert(approx(edge, 46, 2), `仿真 RSRP=-98(边缘) → 置信度≈46 (实得 ${edge})`)
// 仿真 + 低于门限 → 低于 50
const low = calculateSiteConfidence({ rsrp: -105, rsrpSource: 'simulated' }, true)
assert(low < 50, `仿真 RSRP=-105(低于门限) → 置信度<50 (实得 ${low})`)
// 实测相对同值仿真更高
assert(
  calculateSiteConfidence({ rsrp: -90, rsrpSource: 'measured' }, true) >
    calculateSiteConfidence({ rsrp: -90, rsrpSource: 'simulated' }, true),
  '相同 RSRP 下实测置信度 > 仿真'
)

console.log('— calculateCoverageConfidence —')
const sites = [
  { siteId: 'A', rsrp: -82, rsrpSource: 'simulated', towerHeight: 35 },
  { siteId: 'B', rsrp: -98, rsrpSource: 'simulated', towerHeight: 35 },
  { siteId: 'C', rsrp: -75, rsrpSource: 'measured', towerHeight: 35 },
  { siteId: 'D', rsrp: -105, rsrpSource: 'simulated', towerHeight: 35 },
]
const c = calculateCoverageConfidence(sites)
assert(c.overall === 64, `整体可信度=64 (实得 ${c.overall})`)
assert(c.level === '中', `等级=中 (实得 ${c.level})`)
assert(c.basis === '混合（仿真 + 实测）', `数据基底=混合 (实得 ${c.basis})`)
assert(c.measuredCount === 1 && c.simulatedCount === 3, 'measured=1 / simulated=3')
assert(c.perStation.length === 4, 'perStation 含 4 站')
assert(c.threshold === -100, '门限=-100 dBm')
assert(c.perStation[0].margin === 18 && c.perStation[0].confidence === 76, 'A: margin18/conf76')
assert(c.perStation[1].confidence === 46, 'B: conf46')
assert(c.perStation[2].confidence === 99, 'C: conf99(实测封顶)')
assert(c.perStation[3].confidence === 33, 'D: conf33(低于门限)')

console.log('— 边界：空 / 无 RSRP —')
assert(calculateCoverageConfidence([]) === null, '空站点 → null')
// 无原生 RSRP 时回退 500m 代表值（仿真），仍应给出可信度而非崩溃
const noRsrp = calculateCoverageConfidence([{ siteId: 'X', towerHeight: 35 }])
assert(noRsrp !== null && noRsrp.perStation.length === 1 && noRsrp.perStation[0].source === 'simulated',
  '无原生 RSRP → 回退仿真代表值，给出置信度(不崩溃)')

console.log('— 回归：原有指标函数仍可工作 —')
const m = calculateCoverageMetrics(sites)
assert(m && m.totalSites === 4, 'calculateCoverageMetrics 仍返回 4 站')
const gaps = detectCoverageGaps(sites, 50)
assert(Array.isArray(gaps), 'detectCoverageGaps 返回数组')

console.log(`\n结果: ${passed} 通过, ${failed} 失败`)
process.exit(failed === 0 ? 0 : 1)
