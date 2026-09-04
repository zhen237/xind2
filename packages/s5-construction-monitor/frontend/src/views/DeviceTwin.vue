<script setup>
import { ref, onMounted } from 'vue'
import { getDevices, getDevice } from '../api/s5'
import { deviceStatusLabel, deviceStatusType, fmt, fmtTime } from '../utils/labels'

const devices = ref([])
const error = ref('')
const loading = ref(false)
const drawer = ref(false)
const current = ref(null)

async function load() {
  loading.value = true
  try {
    devices.value = await getDevices()
  } catch (e) {
    error.value = '无法连接后端 /api/s5/devices，请确认 S5 后端已启动在 http://localhost:8091'
  } finally {
    loading.value = false
  }
}

async function openDetail(code) {
  try {
    current.value = await getDevice(code)
    drawer.value = true
  } catch (e) {
    error.value = '获取设备孪生详情失败'
  }
}

onMounted(load)
</script>

<template>
  <div v-if="error"><el-alert :title="error" type="error" show-icon closable /></div>

  <el-card shadow="hover">
    <el-table :data="devices" v-loading="loading" stripe @row-click="(r) => openDetail(r.deviceCode)" row-style="cursor:pointer">
      <el-table-column prop="deviceCode" label="设备编码" width="110" />
      <el-table-column prop="deviceName" label="名称" width="130" />
      <el-table-column prop="deviceType" label="类型" width="100" />
      <el-table-column prop="stationCode" label="站点" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="deviceStatusType(row.status)" size="small">{{ deviceStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="温度(℃)" width="100">
        <template #default="{ row }">{{ fmt(row.twin?.temperature) }}</template>
      </el-table-column>
      <el-table-column label="负载(%)" width="100">
        <template #default="{ row }">{{ fmt(row.twin?.load) }}</template>
      </el-table-column>
      <el-table-column label="健康度" width="100">
        <template #default="{ row }">
          <el-progress :percentage="row.twin?.health ?? 0" :stroke-width="10" />
        </template>
      </el-table-column>
      <el-table-column label="最后同步" min-width="160">
        <template #default="{ row }">{{ fmtTime(row.twin?.lastSync) }}</template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-drawer v-model="drawer" title="设备孪生状态" size="420px" v-if="current">
    <el-descriptions :column="1" border>
      <el-descriptions-item label="设备编码">{{ current.deviceCode }}</el-descriptions-item>
      <el-descriptions-item label="名称">{{ current.deviceName }}</el-descriptions-item>
      <el-descriptions-item label="类型">{{ current.deviceType }}</el-descriptions-item>
      <el-descriptions-item label="站点">{{ current.stationCode }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="deviceStatusType(current.status)" size="small">{{ deviceStatusLabel(current.status) }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="厂商">{{ fmt(current.manufacturer) }}</el-descriptions-item>
      <el-descriptions-item label="型号">{{ fmt(current.model) }}</el-descriptions-item>
      <el-descriptions-item label="当前温度(℃)">{{ fmt(current.twin?.temperature) }}</el-descriptions-item>
      <el-descriptions-item label="负载(%)">{{ fmt(current.twin?.load) }}</el-descriptions-item>
      <el-descriptions-item label="累计运行(分钟)">{{ fmt(current.twin?.runtimeMinutes) }}</el-descriptions-item>
      <el-descriptions-item label="健康度">{{ fmt(current.twin?.health) }}</el-descriptions-item>
      <el-descriptions-item label="最后同步">{{ fmtTime(current.twin?.lastSync) }}</el-descriptions-item>
    </el-descriptions>
  </el-drawer>
</template>
