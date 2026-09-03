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
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <span class="muted">{{ formatTime(row.createTime) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'COMPLETED' ? 'success' : row.status === 'FAILED' ? 'danger' : 'info'">{{ row.statusText || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="errorMessage" label="错误信息" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.status === 'FAILED'" style="color:#f56c6c">{{ row.errorMessage || '未知错误（请查看后端日志）' }}</span>
            <span v-else class="muted">-</span>
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
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button size="small" type="primary" link :disabled="row.status !== 'COMPLETED'" @click="viewGeoJson(row)">查看 GeoJSON</el-button>
            <el-button size="small" type="success" link :disabled="row.status !== 'COMPLETED'" :loading="exportingTaskId === row.taskId" @click="exportGeoJson(row)">导出 GeoJSON</el-button>
            <el-button size="small" type="danger" link :loading="deletingTaskId === row.taskId" @click="onDeleteTask(row)">删除</el-button>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCadFiles, getFusionTasks, autoFuse, getFusionGeoJson, deleteFusionTask } from '../api'

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
const exportingTaskId = ref(null)
const deletingTaskId = ref(null)

// 将后端 LocalDateTime.toString() 的 "2026-09-02T12:50:44" 格式化为可读形式；
// 兼容 null/无效值。
const formatTime = (v) => {
  if (!v) return '-'
  const s = String(v).replace('T', ' ')
  return s.length >= 19 ? s.slice(0, 19) : s
}

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
    const data = res?.data || {}
    if (data.status === 'COMPLETED') ElMessage.success(`融合完成：生成 ${data.featureCount ?? 0} 个 GIS 要素`)
    else if (data.status === 'FAILED') ElMessage.error(`融合失败：${data.errorMessage || '未知错误（请查看后端日志）'}`)
    else ElMessage.warning(`融合任务已提交，当前状态：${data.statusText || data.status}`)
    await loadTasks()
  } finally {
    fusing.value = false
  }
}

const viewGeoJson = async (row) => {
  if (row.status !== 'COMPLETED') {
    ElMessage.warning('该任务尚未成功融合，无 GeoJSON 可查看')
    return
  }
  const res = await getFusionGeoJson(row.taskId)
  geojson.value = typeof res === 'string' ? res : JSON.stringify(res, null, 2)
  dialogVisible.value = true
}

const exportGeoJson = async (row) => {
  if (row.status !== 'COMPLETED') {
    ElMessage.warning('该任务尚未成功融合，无 GeoJSON 可导出')
    return
  }
  exportingTaskId.value = row.taskId
  try {
    const res = await getFusionGeoJson(row.taskId)
    const text = typeof res === 'string' ? res : JSON.stringify(res, null, 2)
    const blob = new Blob([text], { type: 'application/geo+json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // 可读文件名：任务名_日期.geojson（任务名做路径安全清洗）
    const date = String(row.createTime || '').slice(0, 10).replace(/-/g, '')
    const safeName = String(row.taskName || `融合任务${row.taskId}`)
      .replace(/[\\/:*?"<>|\s]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 40)
    a.download = `${safeName}${date ? '_' + date : ''}.geojson`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('GeoJSON 已导出')
  } catch (e) {
    ElMessage.error('导出失败，请重试')
  } finally {
    exportingTaskId.value = null
  }
}

const onDeleteTask = async (row) => {
  const name = row.taskName || `任务 #${row.taskId}`
  try {
    await ElMessageBox.confirm(`确认删除融合任务「${name}」？融合结果与记录将一并删除，不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return // 用户取消
  }
  deletingTaskId.value = row.taskId
  try {
    await deleteFusionTask(row.taskId)
    ElMessage.success('已删除')
    await loadTasks()
  } catch (e) {
    ElMessage.error('删除失败：' + (e?.message || '未知错误'))
  } finally {
    deletingTaskId.value = null
  }
}

onMounted(() => {
  loadFiles()
  loadTasks()
})
</script>

<style scoped>
.page { max-width: 1000px; }
.muted { color: #c0c4cc; }
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
