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

    <!-- 3D 地球点位 -->
    <el-card shadow="never" class="block-card">
      <template #header><span>3D 地球点位（真实经纬度）</span></template>
      <FtthMap :boites="data ? data.boites : []" />
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

const data = ref(null)
const typeFilter = ref('all')
const searchText = ref('')
const barEl = ref(null)
const pieEl = ref(null)

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
    const url = import.meta.env.BASE_URL + 'ftth-data.json'
    const res = await fetch(url)
    if (!res.ok) throw new Error('HTTP ' + res.status)
    data.value = await res.json()
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
</style>
