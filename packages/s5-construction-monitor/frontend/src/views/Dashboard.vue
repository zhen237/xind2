<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { getDashboard } from '../api/s5'
import { alertLevelLabel, alertLevelType, alertStatusLabel, alertStatusType, fmtTime } from '../utils/labels'

const data = ref(null)
const error = ref('')
const chartRef = ref(null)
let chart = null
let timer = null

function renderChart(dist) {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '65%'], center: ['50%', '45%'],
      data: Object.entries(dist || {}).map(([name, value]) => ({ name, value }))
    }]
  })
}

async function load() {
  try {
    data.value = await getDashboard()
    renderChart(data.value.deviceTypeDistribution)
    error.value = ''
  } catch (e) {
    error.value = '无法连接后端 /api/s5/dashboard，请确认 C# 后端已启动在 http://localhost:8092'
  }
}

// 实时刷新：首次加载 + 每 5 秒轮询（后端告警时间随当前时间滚动，形成实时效果）
onMounted(() => {
  load()
  timer = setInterval(load, 5000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  chart?.dispose()
})
</script>

<template>
  <div v-if="error"><el-alert :title="error" type="error" show-icon closable /></div>

  <template v-if="data">
    <el-row :gutter="16">
      <el-col :span="4"><el-card shadow="hover"><el-statistic title="设备总数" :value="data.totalDevices" /></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><el-statistic title="在线" :value="data.onlineCount" /></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><el-statistic title="离线" :value="data.offlineCount" /></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><el-statistic title="故障" :value="data.faultCount" value-color="#f56c6c" /></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><el-statistic title="告警总数" :value="data.alertTotal" /></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><el-statistic title="未处理告警" :value="data.alertActive" value-color="#e6a23c" /></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="10">
        <el-card shadow="hover" header="设备类型分布">
          <div ref="chartRef" style="height:300px"></div>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="hover" header="最近告警">
          <el-table :data="data.recentAlerts" stripe size="small">
            <el-table-column prop="deviceCode" label="设备编码" width="100" />
            <el-table-column prop="alertContent" label="内容" />
            <el-table-column label="级别" width="90">
              <template #default="{ row }">
                <el-tag :type="alertLevelType(row.level)" size="small">{{ alertLevelLabel(row.level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="alertStatusType(row.status)" size="small">{{ alertStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ fmtTime(row.createTime) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </template>
</template>
