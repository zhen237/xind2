<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { getVerifyTasks } from '../api/s5'
import { fmt, fmtTime } from '../utils/labels'

const list = ref([])
const error = ref('')
let timer = null

async function load() {
  try {
    const data = await getVerifyTasks()
    list.value = Array.isArray(data) ? data : []
    error.value = ''
  } catch (e) {
    error.value = '无法获取 BOM 核验任务，请确认 S5 后端已启动在 http://localhost:8091'
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, 5000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div>
    <el-alert v-if="error" :title="error" type="error" show-icon closable />
    <el-empty v-else-if="!list.length" description="暂无 BOM 核验任务（S4 生成 BOM 后将自动推送至此）" />

    <template v-else>
      <el-alert type="success" :closable="false" show-icon style="margin-bottom:12px"
        :title="`已接收 ${list.length} 条 S4 推送的 BOM 施工指令`" />
      <el-table :data="list" stripe border size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="bomTaskId" label="BOM 任务 ID" min-width="130" show-overflow-tooltip />
        <el-table-column prop="designTaskId" label="设计任务 ID" min-width="130" show-overflow-tooltip />
        <el-table-column prop="projectName" label="项目" min-width="120" show-overflow-tooltip />
        <el-table-column label="主设备" width="90" align="right">
          <template #default="{ row }">{{ fmt(row.stats?.mainDeviceQty) }}</template>
        </el-table-column>
        <el-table-column label="辅材" width="80" align="right">
          <template #default="{ row }">{{ fmt(row.stats?.auxiliaryQty) }}</template>
        </el-table-column>
        <el-table-column label="线缆" width="80" align="right">
          <template #default="{ row }">{{ fmt(row.stats?.cableQty) }}</template>
        </el-table-column>
        <el-table-column label="条目数" width="90" align="right">
          <template #default="{ row }">{{ fmt(row.stats?.totalItems) }}</template>
        </el-table-column>
        <el-table-column label="品类数" width="90" align="right">
          <template #default="{ row }">{{ fmt(row.stats?.totalCategories) }}</template>
        </el-table-column>
        <el-table-column label="接收时间" min-width="160">
          <template #default="{ row }">{{ fmtTime(row.receivedTime) }}</template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>
