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
          <el-button
            type="primary"
            size="large"
            :disabled="!displayData"
            :loading="exporting"
            @click="onExportExcel"
          >
            {{ exporting ? '生成中...' : '导出工程量报表 Excel' }}
          </el-button>
        </div>
      </div>
      <div v-if="realId" class="source-line">
        <el-icon><Connection /></el-icon>
        <template v-if="fallback && !designReal">
          数据源：演示兜底数据 — 任务 #{{ realId }} 无真实设计成果
        </template>
        <template v-else>
          数据源：S1 设计任务 #{{ realId }}<span v-if="design?.taskNo">（{{ design.taskNo }}<span v-if="selectedTask">，保存于 {{ formatTime(selectedTask.createdAt) }}</span>）</span>
        </template>
        <el-tag v-if="fallback && !designReal" size="small" type="warning" style="margin-left:8px;">演示数据（真实服务不可用）</el-tag>
        <el-tag v-else-if="fallback" size="small" type="warning" style="margin-left:8px;">设备清单真实 · 审查部分为演示（本地未启动 S3）</el-tag>
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
            <el-descriptions-item label="辅材合计">¥ {{ fmt(cost?.summary?.auxiliaryCost) }}</el-descriptions-item>
            <el-descriptions-item label="直接费小计">¥ {{ fmt(cost?.summary?.directSubtotal) }}</el-descriptions-item>
            <el-descriptions-item :label="'管理费（' + (cost?.summary?.managementFeePct ?? MGMT_PCT) + '%)'">¥ {{ fmt(cost?.summary?.managementFee) }}</el-descriptions-item>
            <el-descriptions-item label="利润（{{ cost?.summary?.profitPct }}%）">¥ {{ fmt(cost?.summary?.profit) }}</el-descriptions-item>
            <el-descriptions-item label="税金（{{ cost?.summary?.taxPct }}%）">¥ {{ fmt(cost?.summary?.tax) }}</el-descriptions-item>
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
            <el-table-column prop="auxiliaryCost" label="辅材(元)" width="110" align="right" />
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
const designReal = ref(false)
const design = ref(null)
const cost = ref(null)
const bomItems = ref([])
const activeTab = ref('summary')
const exporting = ref(false)

const displayData = computed(() => design.value)

// 当前选中任务（数据源溯源：任务编号 + 保存时间）
const selectedTask = computed(() =>
  s1Tasks.value.find(t => String(t.id) === String(designTaskId.value)) || null
)

// ISO 时间 → 'YYYY-MM-DD HH:mm'
const formatTime = (iso) => {
  if (!iso) return '—'
  return String(iso).replace('T', ' ').slice(0, 16)
}

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
    designReal.value = !!r.data.designReal
    design.value = r.data.design
    bomItems.value = r.data.bomItems || []
    // 造价交给前端即时算（用同样的 cost_configs.json 镜像口径）—— 后端也已算，下游调用 export 时取
    cost.value = computeCostLocally(design.value?.pipelines || [])
  } catch (e) {
    console.error('加载工程量报表失败', e)
    design.value = null
    cost.value = null
    bomItems.value = []
  }
}

// 前端即时造价镜像（仅展示用，Excel 导出以后端为准）
const FALLBACK_FIBER_PRICE = { 'G.652D': 12, 'G.657A2': 18, 'G.655': 25, 'default': 12 }
const FALLBACK_CONSTR_PRICE = { '直埋': 45, '管道': 80, '架空': 35, '桥架': 30, 'default': 50 }
const MGMT_PCT = 5, PROFIT_PCT = 7, TAX_PCT = 9

function computeCostLocally(pipelines) {
  let sumMat = 0, sumConstr = 0, sumAux = 0, sumLen = 0
  const rows = pipelines.map((pl, i) => {
    const pt = (pl.pipelineType && pl.pipelineType !== '未知') ? pl.pipelineType : '管道'
    const fib = (pl.fiberType && pl.fiberType !== '未知') ? pl.fiberType : 'G.652D'
    const len = Number(pl.lengthM || 0)
    const fp = FALLBACK_FIBER_PRICE[fib] || 12
    const cp = FALLBACK_CONSTR_PRICE[pt] || 50
    const mat = round2(fp * len)
    const c = round2(cp * len)
    const aux = round2(0.30 * len * 50) // 简版土方
    sumMat += mat; sumConstr += c; sumAux += aux; sumLen += len
    return {
      idx: i + 1, pipelineId: pl.pipelineId, startSite: pl.startSite, endSite: pl.endSite,
      lengthM: len, pipelineType: pt, fiberType: fib,
      materialCost: mat, constructionCost: c, auxiliaryCost: aux,
      directCost: round2(mat + c + aux), priceTag: '概算 / 示意',
    }
  })
  const direct = round2(sumMat + sumConstr + sumAux)
  const mgmt = round2(direct * MGMT_PCT / 100)
  const profitBase = round2(direct + mgmt)
  const profit = round2(profitBase * PROFIT_PCT / 100)
  const taxBase = round2(profitBase + profit)
  const tax = round2(taxBase * TAX_PCT / 100)
  const total = round2(taxBase + tax)
  return {
    rows,
    summary: {
      materialCost: round2(sumMat), constructionCost: sumConstr, auxiliaryCost: sumAux,
      directSubtotal: direct,
      managementFeePct: MGMT_PCT, managementFee: mgmt,
      profitPct: PROFIT_PCT, profit,
      taxPct: TAX_PCT, tax,
      totalCost: total, totalLengthM: round2(sumLen),
      costPerMeter: sumLen > 0 ? round2(total / sumLen) : 0,
      currencyUnit: '元', priceTag: '概算 / 示意',
    },
    warning: '本造价为「概算 / 示意」级别，源自挑战杯演示场景参数。不得作为行业基准单价，工程预算请用本地造价口径校准。',
    currencyUnit: '元',
  }
}

function round2(v) { return Math.round(v * 100) / 100 }
function fmt(v) {
  if (v == null) return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'
}

async function onExportExcel() {
  if (!designTaskId.value) return
  exporting.value = true
  try {
    const url = `/api/s4/bom/${designTaskId.value}/volume-report/export`
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
.source-line { margin-top: 12px; color: #909399; font-size: 13px; display: flex; align-items: center; gap: 4px; }
.report-tabs { background: white; padding: 12px; border-radius: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.empty-hint { padding: 24px; text-align: center; color: #909399; }
.total-cost { font-size: 20px; font-weight: bold; color: #F56C6C; }
</style>