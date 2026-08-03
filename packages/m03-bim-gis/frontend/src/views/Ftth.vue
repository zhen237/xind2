<template>
  <div class="ftth-page">
    <div class="page-header">
      <h2>FTTH 光交箱与光路交付物</h2>
      <p class="subtitle" v-if="data">
        数据源: {{ data.source }} ｜ 生成时间: {{ data.generated_at }}
      </p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row" v-if="data">
      <el-col :span="4" v-for="c in statCards" :key="c.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ c.value }}</div>
          <div class="stat-label">{{ c.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据自检 (行业标准校验规则, S3 复用) -->
    <el-card shadow="never" class="block-card" v-if="validation">
      <template #header>
        <span>数据自检 · 行业标准校验规则（S3 设计审查规则复用）</span>
      </template>
      <div class="check-summary">
        <el-progress
          type="dashboard"
          :percentage="validation.summary.passed_rate"
          :color="validation.summary.failed > 0 ? '#e6a23c' : '#67c23a'"
          :width="120"
        />
        <div class="check-meta">
          <div class="check-line">
            <b>通过率 {{ validation.summary.passed_rate }}%</b>
            ｜ 通过 <b>{{ validation.summary.passed }}</b> / 共 {{ validation.summary.total }}
            ｜ 失败 <b class="fail">{{ validation.summary.failed }}</b>
            ｜ 警告 <b class="warn">{{ validation.summary.warned }}</b>
            ｜ 跳过 {{ validation.summary.skipped }}
          </div>
          <div class="check-groups">
            <span
              v-for="(g, name) in validation.groups"
              :key="name"
              class="group-chip"
              :class="{ bad: g.fail > 0, warn: g.warn > 0 && g.fail === 0 }"
            >{{ name }}：{{ g.pass }}✓ / {{ g.fail }}✗ / {{ g.warn }}⚠</span>
          </div>
        </div>
      </div>
      <el-collapse v-if="issues.length" class="check-issues">
        <el-collapse-item v-for="r in issues" :key="r.id" :name="r.id">
          <template #title>
            <span class="issue-title">
              <el-tag size="small" :type="r.status === 'fail' ? 'danger' : 'warning'">
                {{ r.status === 'fail' ? '失败' : '警告' }}
              </el-tag>
              <b>{{ r.id }}</b> {{ r.name }}
            </span>
          </template>
          <div class="issue-detail">{{ r.detail }}</div>
          <div class="issue-samples" v-if="r.samples.length">
            <div v-for="(s, i) in r.samples" :key="i" class="sample">{{ s }}</div>
          </div>
        </el-collapse-item>
      </el-collapse>
      <div v-else class="all-pass">全部规则通过 ✓</div>
    </el-card>

    <el-row :gutter="16">
      <!-- 箱体清单 -->
      <el-col :span="14">
        <el-card shadow="never" class="block-card">
          <template #header><span>箱体清单</span></template>
          <div class="filter-bar">
            <el-radio-group v-model="typeFilter">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="BPE">BPE</el-radio-button>
              <el-radio-button label="PBO">PBO</el-radio-button>
            </el-radio-group>
            <el-input
              v-model="searchText"
              placeholder="搜索箱体编码"
              clearable
              size="small"
              class="search"
            />
          </div>
          <el-table :data="filteredBoites" height="430" size="small" stripe>
            <el-table-column prop="code" label="编码" width="180" />
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="capacite_fo" label="容量FO" width="90" />
            <el-table-column prop="fonction" label="功能" width="100" />
            <el-table-column prop="pm" label="归属PM" width="140" />
            <el-table-column prop="logements" label="户数" width="80" />
            <el-table-column prop="ptec" label="PTEC" width="120" />
          </el-table>
        </el-card>
      </el-col>

      <!-- 图表 -->
      <el-col :span="10">
        <el-card shadow="never" class="block-card">
          <template #header><span>按 PM 分布</span></template>
          <div ref="barEl" class="chart"></div>
        </el-card>
        <el-card shadow="never" class="block-card">
          <template #header><span>类型占比</span></template>
          <div ref="pieEl" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 3D 地球 + 智能规划 -->
    <el-card shadow="never" class="block-card">
      <template #header><span>3D 可视化</span></template>
      <el-tabs>
        <el-tab-pane label="3D 地球总览（真实竣工）">
          <FtthMap
            :boites="data ? data.boites : []"
            :cables="data ? data.cables : []"
            :sites="data ? data.sites : []"
          />
        </el-tab-pane>
        <el-tab-pane label="智能规划（AI 辅助设计）" lazy>
          <FtthPlanner />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 交付物说明 -->
    <el-card shadow="never" class="block-card">
      <template #header>
        <span>官方交付物（在 QGIS 插件「FTTH 官方交付物」按钮一键导出 xlsx）</span>
      </template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="d in deliverables" :key="d.title">
          <div class="deliver-item">
            <div class="deliver-title">{{ d.title }}</div>
            <div class="deliver-desc">{{ d.desc }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import FtthMap from '@/components/FtthMap.vue'
import FtthPlanner from '@/components/FtthPlanner.vue'

const data = ref(null)
const validation = ref(null)
const typeFilter = ref('all')
const searchText = ref('')
const barEl = ref(null)
const pieEl = ref(null)

// 数据自检：仅展示失败/警告项
const issues = computed(() => {
  if (!validation.value) return []
  return validation.value.rules.filter(
    (r) => r.status === 'fail' || r.status === 'warn',
  )
})

const statCards = computed(() => {
  if (!data.value) return []
  const s = data.value.summary
  const boites = data.value.boites
  const bpe = boites.filter((b) => b.type === 'BPE').length
  const pbo = boites.filter((b) => b.type === 'PBO').length
  const log = boites.reduce((a, b) => a + (b.logements || 0), 0)
  return [
    { label: '箱体', value: s.BOITE },
    { label: '住户', value: log },
    { label: 'BPE', value: bpe },
    { label: 'PBO', value: pbo },
    { label: 'IMB', value: s.IMB },
    { label: '缆段', value: s.CABLE },
  ]
})

const filteredBoites = computed(() => {
  if (!data.value) return []
  let list = data.value.boites
  if (typeFilter.value !== 'all') list = list.filter((b) => b.type === typeFilter.value)
  if (searchText.value) {
    list = list.filter((b) => b.code.includes(searchText.value))
  }
  return list
})

const deliverables = [
  { title: '光交箱汇总', desc: 'Sommaire + 每箱体明细 sheet（容量/功能/PTEC/经过缆段）' },
  { title: '光路由表', desc: 'Routes Optiques：PM→箱体逐段光缆与长度' },
  { title: '机柜熔接盘图', desc: 'Plan de Baie：24 芯位熔接盘占用矩阵' },
  { title: '系统图', desc: 'Synoptique：各 PM 光路系统图' },
]

async function loadData() {
  try {
    const base = import.meta.env.BASE_URL
    const [dRes, vRes] = await Promise.all([
      fetch(base + 'ftth-data.json'),
      fetch(base + 'ftth-validation.json'),
    ])
    if (!dRes.ok) throw new Error('HTTP ' + dRes.status)
    data.value = await dRes.json()
    if (vRes.ok) validation.value = await vRes.json()
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('FTTH 数据加载失败', e)
  }
}

function renderCharts() {
  if (!data.value) return
  const pmGroups = {}
  for (const b of data.value.boites) {
    pmGroups[b.pm] = pmGroups[b.pm] || { BPE: 0, PBO: 0 }
    pmGroups[b.pm][b.type] = (pmGroups[b.pm][b.type] || 0) + 1
  }
  const pms = Object.keys(pmGroups)
  if (barEl.value) {
    const bar = echarts.init(barEl.value)
    bar.setOption({
      tooltip: {},
      legend: { data: ['BPE', 'PBO'] },
      xAxis: { type: 'category', data: pms },
      yAxis: { type: 'value' },
      series: [
        { name: 'BPE', type: 'bar', data: pms.map((p) => pmGroups[p].BPE || 0) },
        { name: 'PBO', type: 'bar', data: pms.map((p) => pmGroups[p].PBO || 0) },
      ],
    })
  }
  const bpe = data.value.boites.filter((b) => b.type === 'BPE').length
  const pbo = data.value.boites.filter((b) => b.type === 'PBO').length
  if (pieEl.value) {
    const pie = echarts.init(pieEl.value)
    pie.setOption({
      tooltip: {},
      legend: { data: ['BPE', 'PBO'] },
      series: [
        {
          type: 'pie',
          radius: '60%',
          data: [
            { name: 'BPE', value: bpe },
            { name: 'PBO', value: pbo },
          ],
        },
      ],
    })
  }
}

onMounted(loadData)
</script>

<style scoped>
.ftth-page {
  padding: 16px;
}
.page-header h2 {
  margin: 0 0 4px;
}
.subtitle {
  color: #888;
  font-size: 12px;
  margin: 0 0 12px;
}
.stat-row {
  margin-bottom: 16px;
}
.stat-card {
  text-align: center;
}
.stat-value {
  font-size: 24px;
  font-weight: 600;
}
.stat-label {
  color: #888;
  font-size: 12px;
  margin-top: 4px;
}
.block-card {
  margin-bottom: 16px;
}
.chart {
  height: 240px;
}
.filter-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
.search {
  width: 200px;
}
.deliver-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
}
.deliver-title {
  font-weight: 600;
  margin-bottom: 6px;
}
.deliver-desc {
  font-size: 12px;
  color: #666;
}
.check-summary {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 12px;
}
.check-meta {
  flex: 1;
}
.check-line {
  font-size: 13px;
  margin-bottom: 10px;
}
.check-line .fail {
  color: #f56c6c;
}
.check-line .warn {
  color: #e6a23c;
}
.check-groups {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.group-chip {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  background: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}
.group-chip.bad {
  background: #fef0f0;
  color: #f56c6c;
  border-color: #fde2e2;
}
.group-chip.warn {
  background: #fdf6ec;
  color: #e6a23c;
  border-color: #faecd8;
}
.issue-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.issue-detail {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
.issue-samples {
  margin-top: 6px;
  max-height: 160px;
  overflow: auto;
  background: #fafafa;
  border-radius: 4px;
  padding: 6px 10px;
}
.issue-samples .sample {
  font-family: monospace;
  font-size: 12px;
  color: #909399;
  padding: 1px 0;
}
.all-pass {
  color: #67c23a;
  font-weight: 600;
}
</style>
