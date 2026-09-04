<script setup>
import { ref, onMounted, watch } from 'vue'
import { getAlerts } from '../api/s5'
import { alertLevelLabel, alertLevelType, alertStatusLabel, alertStatusType, fmtTime } from '../utils/labels'
import AlertDetailDialog from '../components/AlertDetailDialog.vue'

const alerts = ref([])
const error = ref('')
const loading = ref(false)
const filters = ref({ level: '', status: '' })
const detailVisible = ref(false)
const currentAlert = ref(null)

function openDetail(row) {
  currentAlert.value = row
  detailVisible.value = true
}

async function load() {
  loading.value = true
  const params = {}
  if (filters.value.level !== '') params.level = filters.value.level
  if (filters.value.status !== '') params.status = filters.value.status
  try {
    alerts.value = await getAlerts(params)
  } catch (e) {
    error.value = '无法连接后端 /api/s5/alerts，请确认 S5 后端已启动在 http://localhost:8091'
  } finally {
    loading.value = false
  }
}

watch(filters, load, { deep: true })
onMounted(load)
</script>

<template>
  <div v-if="error"><el-alert :title="error" type="error" show-icon closable /></div>

  <el-card shadow="hover">
    <template #header>
      <div style="display:flex;gap:12px;align-items:center">
        <span>筛选：</span>
        <el-select v-model="filters.level" placeholder="级别" clearable style="width:120px">
          <el-option :value="1" label="提示" />
          <el-option :value="2" label="警告" />
          <el-option :value="3" label="严重" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable style="width:120px">
          <el-option :value="0" label="未处理" />
          <el-option :value="1" label="已处理" />
        </el-select>
      </div>
    </template>

    <el-table :data="alerts" v-loading="loading" stripe @row-click="openDetail" style="cursor:pointer">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="deviceCode" label="设备编码" width="110" />
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
      <el-table-column prop="source" label="来源" width="140" />
      <el-table-column prop="orderNo" label="工单号" width="130" />
      <el-table-column label="创建时间" min-width="160">
        <template #default="{ row }">{{ fmtTime(row.createTime) }}</template>
      </el-table-column>
    </el-table>
  </el-card>

  <AlertDetailDialog v-model="detailVisible" :alert="currentAlert" />
</template>
