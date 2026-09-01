<template>
  <div class="page">
    <h2>融合结果</h2>
    <el-card shadow="never">
      <el-form inline>
        <el-form-item label="任务名">
          <el-input v-model="taskName" placeholder="例如：运城站区融合" style="width: 200px" />
        </el-form-item>
        <el-form-item label="源文件">
          <el-select v-model="sourceFileId" placeholder="选择已上传 CAD 文件" style="width: 220px">
            <el-option v-for="f in files" :key="f.id" :label="f.fileName" :value="f.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="源坐标系">
          <el-select v-model="sourceEpsg" style="width: 150px">
            <el-option label="EPSG:4490" value="EPSG:4490" />
            <el-option label="EPSG:4326" value="EPSG:4326" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标坐标系">
          <el-select v-model="targetEpsg" style="width: 150px">
            <el-option label="EPSG:4326" value="EPSG:4326" />
            <el-option label="EPSG:4490" value="EPSG:4490" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="fusing" :disabled="!sourceFileId" @click="onFuse">
            开始融合
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="margin-top: 20px">
      <template #header>融合任务列表</template>
      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column prop="taskId" label="任务ID" width="80" />
        <el-table-column prop="taskName" label="任务名" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'COMPLETED' ? 'success' : 'warning'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="统计" min-width="200">
          <template #default="{ row }">
            <span v-if="row.statistics">
              去重 {{ row.statistics.dedupCount ?? 0 }} ｜ 冲突 {{ row.statistics.conflictCount ?? 0 }} ｜
              融合 {{ row.statistics.fusedCount ?? 0 }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewGeoJson(row)">查看 GeoJSON</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="融合结果 GeoJSON" width="70%" top="5vh">
      <pre class="geojson-pre">{{ geojson }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCadFiles, getFusionTasks, autoFuse, getFusionGeoJson } from '../api'

const taskName = ref('')
const sourceFileId = ref(null)
const sourceEpsg = ref('EPSG:4490')
const targetEpsg = ref('EPSG:4326')
const fusing = ref(false)
const loading = ref(false)
const files = ref([])
const tasks = ref([])
const dialogVisible = ref(false)
const geojson = ref('')

const loadFiles = async () => {
  const res = await getCadFiles()
  files.value = res?.data || []
}

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await getFusionTasks()
    tasks.value = res?.data || []
  } finally {
    loading.value = false
  }
}

const onFuse = async () => {
  fusing.value = true
  try {
    const res = await autoFuse({
      taskName: taskName.value || `融合任务-${Date.now()}`,
      sourceFileId: sourceFileId.value,
      sourceEpsg: sourceEpsg.value,
      targetEpsg: targetEpsg.value,
    })
    ElMessage.success('融合完成')
    await loadTasks()
  } finally {
    fusing.value = false
  }
}

const viewGeoJson = async (row) => {
  const res = await getFusionGeoJson(row.taskId)
  geojson.value = typeof res === 'string' ? res : JSON.stringify(res, null, 2)
  dialogVisible.value = true
}

onMounted(() => {
  loadFiles()
  loadTasks()
})
</script>

<style scoped>
.page { max-width: 1000px; }
.geojson-pre {
  max-height: 65vh;
  overflow: auto;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
