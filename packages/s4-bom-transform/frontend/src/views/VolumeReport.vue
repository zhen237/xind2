<template>
  <div class="volume-page">
    <el-card class="header-card">
      <div class="header-row">
        <div>
          <h1>工程量报表（材料清单 + 造价估算）</h1>
          <p class="subtitle">从 S1 设计成果聚合：设备清单 + 管线明细 + BOM 物料 + 造价估算汇总</p>
        </div>
        <div class="header-actions">
          <el-select v-model="designTaskId" placeholder="选择 S1 设计任务" filterable style="width: 240px" @change="loadAll">
            <el-option
              v-for="t in s1Tasks"
              :key="t.id"
              :label="`#${t.id} ${t.taskName || t.taskNo || ''}`"
              :value="String(t.id)"
            />
          </el-select>
          <el-input-number
            v-model="fiberPrice"
            :min="0"
            :max="999"
            :step="1"
            :precision="2"
            controls-position="right"
            style="width: 140px"
            title="整体覆盖光缆基准单价（元/m），对应 QGIS「每米价格」设置"
            @change="recomputeCost"
          />
          <span class="price-unit">元/m</span>
          <el-button
            type="primary"
            size="large"
            :disabled="!displayData"
            :loading="exporting"
            @click="onExportExcel"
          >
            {{ exporting ? '生成中...' : '导出工程量报表 Excel' }}
          </el-button>
          <el-button
            size="large"
            :disabled="!displayData"
            @click="onExportTxt"
          >
            导出 TXT
          </el-button>
        </div>
      </div>
      <div v-if="realId" class="source-line">
        <el-icon><Connection /></el-icon>
        数据源：S1 设计任务 #{{ realId }}<span v-if="design?.taskNo">（{{ design.taskNo }}）</span>
        <el-tag v-if="fallback" size="small" type="warning" style="margin-left:8px;">演示数据（真实服务不可用）</el-tag>
      </div>
    </el-card>

    <el-tabs v-if="displayData" v-model="activeTab" class="report-tabs">
      <!-- Sheet 1：造价估算汇总（最重要的"汇报页面"） -->
      <el-tab-pane label="造价估算汇总" name="summary">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span><b>总成本与各项费用（人民币 元）</b></span>
              <el-tag size="small" type="warning">⚠ 概算 / 示意</el-tag>
            </div>
          </template>
          <el-alert
            v-if="cost?.warning"
            :title="cost.warning"
            type="warning"
            :closable="false"
            show-icon
            style="margin-bottom:16px;"
          />
          <el-descriptions :column="3" border>
            <el-descriptions-item label="材料费合计">¥ {{ fmt(cost?.summary?.materialCost) }}</el-descriptions-item>
            <el-descriptions-item label="施工费合计">¥ {{ fmt(cost?.summary?.constructionCost) }}</el-descriptions-item>
            <el-descriptions-item label="其中附属物合计">¥ {{ fmt(cost?.summary?.auxiliaryCost) }}</el-descriptions-item>
            <el-descriptions-item label="直接费小计">¥ {{ fmt(cost?.summary?.directSubtotal) }}</el-descriptions-item>
            <el-descriptions-item label="施工管理费（{{ cost?.summary?.managementFeePct }}%×直接费）">¥ {{ fmt(cost?.summary?.managementFee) }}</el-descriptions-item>
            <el-descriptions-item label="利润（{{ cost?.summary?.profitPct }}%×直接费）">¥ {{ fmt(cost?.summary?.profit) }}</el-descriptions-item>
            <el-descriptions-item label="税金（{{ cost?.summary?.taxPct }}%×直接费）">¥ {{ fmt(cost?.summary?.tax) }}</el-descriptions-item>
            <el-descriptions-item label="总成本"><span class="total-cost">¥ {{ fmt(cost?.summary?.totalCost) }}</span></el-descriptions-item>
            <el-descriptions-item label="管线总长度">{{ fmt(cost?.summary?.totalLengthM) }} m</el-descriptions-item>
            <el-descriptions-item label="每米成本">¥ {{ fmt(cost?.summary?.costPerMeter) }} / m</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- Sheet 2：管线明细 -->
      <el-tab-pane :label="`管线明细（${design?.pipelines?.length || 0}）`" name="pipeline">
        <el-card shadow="hover">
          <el-table :data="cost?.rows || []" stripe size="small" style="width:100%" :max-height="500">
            <el-table-column prop="idx" label="#" width="50" />
            <el-table-column prop="pipelineId" label="管线编号" width="130" show-overflow-tooltip />
            <el-table-column prop="startSite" label="起点" width="100" show-overflow-tooltip />
            <el-table-column prop="endSite" label="终点" width="100" show-overflow-tooltip />
            <el-table-column prop="lengthM" label="长度(m)" width="90" align="right" />
            <el-table-column prop="pipelineType" label="敷设方式" width="120" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.pipelineType }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="fiberType" label="光纤类型" width="130" show-overflow-tooltip />
            <el-table-column prop="materialCost" label="材料费(元)" width="110" align="right" />
            <el-table-column prop="constructionCost" label="施工费(元)" width="110" align="right" />
            <el-table-column prop="auxiliaryCost" label="其中附属物(元)" width="130" align="right" />
            <el-table-column prop="directCost" label="直接费(元)" width="110" align="right">
              <template #default="{ row }">
                <b>{{ row.directCost }}</b>
              </template>
            </el-table-column>
            <el-table-column prop="priceTag" label="备注" width="100">
              <template #default>
                <el-tag size="small" type="warning">概算 / 示意</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!cost?.rows?.length" class="empty-hint">
            该设计无管线数据。可能来源：S1 任务无管线设计 / 数据未落库 / fallback 演示场景
          </div>
        </el-card>
      </el-tab-pane>

      <!-- Sheet 3：设备清单 -->
      <el-tab-pane :label="`设备清单（${design?.devices?.length || 0}）`" name="device">
        <el-card shadow="hover">
          <el-table :data="design?.devices || []" stripe size="small" style="width:100%" :max-height="500">
            <el-table-column prop="deviceId" label="编号" width="110" show-overflow-tooltip />
            <el-table-column prop="deviceName" label="设备名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="modelSpec" label="型号" min-width="120" show-overflow-tooltip />
            <el-table-column prop="deviceType" label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.deviceType }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="qty" label="数量" width="80" align="right" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Sheet 4：BOM 物料 -->
      <el-tab-pane :label="`BOM 物料（${bomItems.length || 0}）`" name="bom">
        <el-card shadow="hover">
          <el-table :data="bomItems" stripe size="small" style="width:100%" :max-height="500">
            <el-table-column prop="siteId" label="站点ID" width="100" show-overflow-tooltip />
            <el-table-column prop="installMethod" label="安装方式" width="110" show-overflow-tooltip />
            <el-table-column prop="materialName" label="物料名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="spec" label="规格" min-width="120" show-overflow-tooltip />
            <el-table-column prop="qty" label="数量" width="80" align="right" />
            <el-table-column prop="unit" label="单位" width="80" />
          </el-table>
          <div v-if="!bomItems.length" class="empty-hint">
            该设计尚未生成 BOM。请先回到流水线首页点击"一键生成 BOM"，生成完成后物料会自动附挂到此报表。
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-empty v-else description="请选择 S1 设计任务" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Connection } from '@element-plus/icons-vue'
import axios from 'axios'

const route = useRoute()

const s1Tasks = ref([])
const designTaskId = ref('')
const realId = ref('')
const fallback = ref(false)
const design = ref(null)
const cost = ref(null)
const bomItems = ref([])
const activeTab = ref('summary')
const exporting = ref(false)
// [S4-S1-迁移 2026-09-27] 光缆单价整体覆盖（元/m）—— 对应 QGIS「每米价格」SpinBox（design_dock.py:1726，默认 15）
const fiberPrice = ref(15)

const displayData = computed(() => design.value)

async function loadS1Tasks() {
  try {
    const r = await axios.get('/api/s4/bom/s1-tasks')
    const list = Array.isArray(r.data) ? r.data : (r.data?.data || [])
    s1Tasks.value = list.slice(0, 12)
    if (s1Tasks.value.length > 0 && !designTaskId.value) {
      const q = String(route.query.designTaskId || '')
      designTaskId.value = q && s1Tasks.value.some(t => String(t.id) === q) ? q : String(s1Tasks.value[0].id)
      await loadAll()
    }
  } catch (e) {
    s1Tasks.value = []
  }
}

async function loadAll() {
  if (!designTaskId.value) return
  try {
    const r = await axios.get(`/api/s4/bom/${designTaskId.value}/volume-report`)
    realId.value = r.data.realId
    fallback.value = !!r.data.fallback
    design.value = r.data.design
    bomItems.value = r.data.bomItems || []
    // 造价交给前端即时算（用同样的 cost_configs.json 镜像口径，含每米价格覆盖）—— 后端也已算，下游调用 export 时取
    cost.value = computeCostLocally(design.value?.pipelines || [], fiberPrice.value)
  } catch (e) {
    console.error('加载工程量报表失败', e)
    design.value = null
    cost.value = null
    bomItems.value = []
  }
}

// 每米价格变动 → 仅重算本地造价镜像（数据不重拉）
function recomputeCost() {
  if (design.value) {
    cost.value = computeCostLocally(design.value?.pipelines || [], fiberPrice.value)
  }
}

// 前端即时造价镜像（仅展示用，Excel 导出以后端为准）
// v1.1 对齐 QGIS calculate_pipeline_cost 分项口径：直埋/管道/架空三分支 + 费率 15/5/9（均以直接费为基数）
const FALLBACK_FIBER_PRICE = { 'G.652D': 12, 'G.657A2': 18, 'G.655': 25, 'default': 12 }
const FALLBACK_CONSTR_PRICE = { '桥架': 30, 'default': 50 }
const TYPE_CONFIGS = {
  '直埋': { dig: 50, backfill: 30, stone: 80, stoneGap: 100, joint: 200, jointGap: 2000, extraW: 0.6, extraD: 0.1, depth: 1.2, diam: 110 },
  '管道': { duct: 45, dig: 60, backfill: 40, width: 0.6, extraD: 0.2, manhole: 3000, manholeGap: 100, joint: 200, jointGap: 2000, depth: 1.5, diam: 110 },
  '架空': { pole: 1500, poleGap: 50, guy: 500, guyRatio: 0.3, joint: 200, jointGap: 2000, depth: 0, diam: 50 },
}
const KNOWN_TYPES = new Set([...Object.keys(TYPE_CONFIGS), ...Object.keys(FALLBACK_CONSTR_PRICE)])
const MGMT_PCT = 15, PROFIT_PCT = 5, TAX_PCT = 9

function computeCostLocally(pipelines, priceOverride) {
  const overrideOn = Number(priceOverride) > 0
  let sumMat = 0, sumConstr = 0, sumAux = 0, sumLen = 0
  const rows = pipelines.map((pl, i) => {
    const rawPt = pl.pipelineType || ''
    const pt = (rawPt && rawPt !== '未知' && KNOWN_TYPES.has(rawPt)) ? rawPt : '管道'
    const fib = (pl.fiberType && pl.fiberType !== '未知') ? pl.fiberType : 'G.652D'
    const len = Number(pl.lengthM || 0)
    const fp = overrideOn ? Number(priceOverride) : (FALLBACK_FIBER_PRICE[fib] || 12)
    const depth = Number(pl.depthM) > 0 ? Number(pl.depthM) : (TYPE_CONFIGS[pt]?.depth ?? 1.2)
    const diam = Number(pl.diameterMm) > 0 ? Number(pl.diameterMm) : (TYPE_CONFIGS[pt]?.diam ?? 110)

    let mat = 0, con = 0, aux = 0
    const detail = {}
    if (len > 0) {
      mat += round2(fp * len); detail['光缆费(元)'] = round2(fp * len)
      const tc = TYPE_CONFIGS[pt]
      if (pt === '直埋') {
        const vol = len * (diam / 1000 + tc.extraW) * (depth + tc.extraD)
        const dig = round2(vol * tc.dig), backfill = round2(vol * tc.backfill)
        con += dig + backfill
        const stones = Math.floor(len / tc.stoneGap) + 1
        const stoneCost = round2(stones * tc.stone)
        mat += stoneCost; aux += stoneCost
        const joints = Math.max(1, Math.floor(len / tc.jointGap))
        const jointCost = round2(joints * tc.joint)
        mat += jointCost; aux += jointCost
      } else if (pt === '管道') {
        const ductCost = round2(len * tc.duct)
        mat += ductCost
        const vol = len * tc.width * (depth + tc.extraD)
        const dig = round2(vol * tc.dig), backfill = round2(vol * tc.backfill)
        con += dig + backfill
        const manholes = Math.max(1, Math.floor(len / tc.manholeGap))
        const manholeCost = round2(manholes * tc.manhole)
        con += manholeCost; aux += manholeCost
        const joints = Math.max(1, Math.floor(len / tc.jointGap))
        const jointCost = round2(joints * tc.joint)
        mat += jointCost; aux += jointCost
      } else if (pt === '架空') {
        const poles = Math.floor(len / tc.poleGap) + 1
        const poleCost = round2(poles * tc.pole)
        mat += poleCost; aux += poleCost
        const guys = Math.floor(len / 1000 * tc.guyRatio)
        const guyCost = round2(guys * tc.guy)
        mat += guyCost; aux += guyCost
        const joints = Math.max(1, Math.floor(len / tc.jointGap))
        const jointCost = round2(joints * tc.joint)
        mat += jointCost; aux += jointCost
      } else {
        // 桥架等无分项配置：综合价 + 接头盒
        const compCost = round2((FALLBACK_CONSTR_PRICE[pt] || 50) * len)
        con += compCost
        const joints = Math.max(1, Math.floor(len / 2000))
        const jointCost = round2(joints * 200)
        mat += jointCost; aux += jointCost
      }
    }
    mat = round2(mat); con = round2(con); aux = round2(aux)
    sumMat += mat; sumConstr += con; sumAux += aux; sumLen += len
    return {
      idx: i + 1, pipelineId: pl.pipelineId, startSite: pl.startSite, endSite: pl.endSite,
      lengthM: len, pipelineType: pt, fiberType: fib,
      materialCost: mat, constructionCost: con, accessoryCost: aux, auxiliaryCost: aux,
      directCost: round2(mat + con), priceTag: '概算 / 示意',
      unitPriceFiber: fp, costDetail: detail,
    }
  })
  // 费率对齐 QGIS：管理费/利润/税金均以直接费为基数（非级联）
  const direct = round2(sumMat + sumConstr)
  const mgmt = round2(direct * MGMT_PCT / 100)
  const profit = round2(direct * PROFIT_PCT / 100)
  const tax = round2(direct * TAX_PCT / 100)
  const total = round2(direct + mgmt + profit + tax)
  const summary = {
    materialCost: round2(sumMat), constructionCost: sumConstr, auxiliaryCost: sumAux,
    directSubtotal: direct,
    managementFeePct: MGMT_PCT, managementFee: mgmt,
    profitPct: PROFIT_PCT, profit,
    taxPct: TAX_PCT, tax,
    totalCost: total, totalLengthM: round2(sumLen),
    costPerMeter: sumLen > 0 ? round2(total / sumLen) : 0,
    currencyUnit: '元', priceTag: '概算 / 示意',
  }
  if (overrideOn) {
    summary.fiberPriceOverride = Number(priceOverride)
    summary.priceOverrideNote = `光缆单价已整体覆盖为 ${priceOverride} 元/m（概算/示意）`
  }
  return {
    rows,
    summary,
    warning: '本造价为「概算 / 示意」级别，源自平台演示场景参数。不得作为行业基准单价，工程预算请用本地造价口径校准。',
    currencyUnit: '元',
  }
}

function round2(v) { return Math.round(v * 100) / 100 }
function fmt(v) {
  if (v == null) return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'
}

// 价格覆盖参数：>0 时附加到导出/查询 URL（对应 QGIS「每米价格」SpinBox）
function priceQuery() {
  return Number(fiberPrice.value) > 0 ? `?fiberPricePerMeter=${fiberPrice.value}` : ''
}

async function onExportExcel() {
  if (!designTaskId.value) return
  exporting.value = true
  try {
    const url = `/api/s4/bom/${designTaskId.value}/volume-report/export${priceQuery()}`
    const r = await axios.get(url, { responseType: 'blob' })
    const blob = new Blob([r.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = `VolumeReport_${designTaskId.value}_${new Date().toISOString().slice(0,10)}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
  } catch (e) {
    console.error('导出失败', e)
  } finally {
    exporting.value = false
  }
}

// [S4-S1-迁移 2026-09-27] TXT 导出 — 对应 QGIS _export_report_txt 产物形态
async function onExportTxt() {
  if (!designTaskId.value) return
  try {
    const url = `/api/s4/bom/${designTaskId.value}/volume-report/export-txt${priceQuery()}`
    const r = await axios.get(url, { responseType: 'blob' })
    const blob = new Blob([r.data], { type: 'text/plain;charset=utf-8' })
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = `VolumeReport_${designTaskId.value}_${new Date().toISOString().slice(0,10)}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
  } catch (e) {
    console.error('TXT 导出失败', e)
  }
}

onMounted(async () => {
  await loadS1Tasks()
})
</script>

<style scoped>
.volume-page { max-width: 1280px; margin: 0 auto; padding: 20px; }
.header-card { margin-bottom: 20px; }
.header-row { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }
.header-row h1 { font-size: 22px; margin: 0 0 6px 0; color: #303133; }
.subtitle { color: #909399; margin: 0; }
.header-actions { display: flex; gap: 12px; align-items: center; }
.price-unit { color: #909399; font-size: 13px; white-space: nowrap; }
.source-line { margin-top: 12px; color: #909399; font-size: 13px; display: flex; align-items: center; gap: 4px; }
.report-tabs { background: white; padding: 12px; border-radius: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.empty-hint { padding: 24px; text-align: center; color: #909399; }
.total-cost { font-size: 20px; font-weight: bold; color: #F56C6C; }
</style>