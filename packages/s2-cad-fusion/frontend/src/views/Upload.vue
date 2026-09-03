<template>
  <div class="page">
    <h2>图纸上传</h2>
    <el-card shadow="never">
      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        accept=".dxf,.dwg"
        :on-change="onFileChange"
        :on-remove="onFileRemove"
      >
        <div class="upload-hint">
          <p>📁 将 DWG/DXF 文件拖到此处，或点击选择</p>
          <p class="sub">支持 .dxf / .dwg 格式</p>
        </div>
      </el-upload>

      <el-form label-width="110px" style="margin-top: 20px; max-width: 480px">
        <el-form-item label="源坐标系">
          <el-select v-model="sourceEpsg" style="width: 100%">
            <el-option label="CGCS2000 高斯投影 (EPSG:4490)" value="EPSG:4490" />
            <el-option label="WGS84 (EPSG:4326)" value="EPSG:4326" />
            <el-option label="Web Mercator (EPSG:3857)" value="EPSG:3857" />
            <el-option label="北京54 (EPSG:4214)" value="EPSG:4214" />
            <el-option label="西安80 (EPSG:4610)" value="EPSG:4610" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标坐标系">
          <el-select v-model="targetEpsg" style="width: 100%">
            <el-option label="WGS84 (EPSG:4326)" value="EPSG:4326" />
            <el-option label="CGCS2000 (EPSG:4490)" value="EPSG:4490" />
            <el-option label="Web Mercator (EPSG:3857)" value="EPSG:3857" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="onUpload">
            上传并解析
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="margin-top: 20px">
      <template #header>已上传文件</template>
      <el-table :data="files" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="文件名" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span :title="row.fileName">{{ row.originalName || row.fileName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="90">
          <template #default="{ row }">
            {{ row.fileSizeReadable || (row.fileSize != null ? row.fileSize + ' B' : '-') }}
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">
            <span class="muted">{{ formatTime(row.uploadTime) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sourceEpsg" label="源坐标系" width="130" />
        <el-table-column prop="targetEpsg" label="目标坐标系" width="130" />
        <el-table-column prop="parseStatus" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.parseStatus === '已解析' ? 'success' : row.parseStatus === '解析失败' ? 'danger' : 'info'">{{ row.parseStatus || '待解析' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="onParse(row)">解析</el-button>
            <el-button size="small" type="success" link :loading="downloadingId === row.id" @click="onDownload(row)">下载</el-button>
            <el-button size="small" type="danger" link @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadCadFile, getCadFiles, parseCadFile, downloadCadFile, deleteCadFile } from '../api'

const selectedFile = ref(null)
const sourceEpsg = ref('EPSG:4490')
const targetEpsg = ref('EPSG:4326')
const uploading = ref(false)
const loading = ref(false)
const downloadingId = ref(null)
const files = ref([])

// 后端 LocalDateTime 形如 "2026-09-03T10:43:30"，转 "2026-09-03 10:43:30"；null/空则显示 '-'
const formatTime = (v) => {
  if (!v) return '-'
  const s = String(v).replace('T', ' ')
  return s.length >= 19 ? s.slice(0, 19) : s
}

// Blob 触发浏览器下载（filename 由调用方给出，含原始扩展名）
function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const onFileChange = (file) => {
  selectedFile.value = file.raw
}

const onFileRemove = () => {
  selectedFile.value = null
}

const loadFiles = async () => {
  loading.value = true
  try {
    const res = await getCadFiles()
    files.value = res?.data || []
  } finally {
    loading.value = false
  }
}

const onUpload = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    const res = await uploadCadFile(selectedFile.value, {
      sourceEpsg: sourceEpsg.value,
      targetEpsg: targetEpsg.value,
    })
    ElMessage.success('上传成功')
    const file = res?.data
    if (file?.id) await onParse(file)
    await loadFiles()
  } finally {
    uploading.value = false
  }
}

const onParse = async (row) => {
  const res = await parseCadFile(row.id)
  const payload = res?.data || {}
  if (payload.entityCount != null) ElMessage.success(`解析完成：识别 ${payload.entityCount} 个实体`)
  else ElMessage.success('解析完成')
  await loadFiles()
}

const onDownload = async (row) => {
  downloadingId.value = row.id
  try {
    const blob = await downloadCadFile(row.id)
    if (!blob || !blob.size) {
      ElMessage.warning('该文件内容为空，无法下载')
      return
    }
    saveBlob(blob, row.originalName || row.fileName || `cad_${row.id}.dxf`)
    ElMessage.success('已开始下载')
  } catch (e) {
    ElMessage.error('下载失败：' + (e?.message || '未知错误'))
  } finally {
    downloadingId.value = null
  }
}

const onDelete = async (row) => {
  const name = row.originalName || row.fileName
  try {
    await ElMessageBox.confirm(`确认删除文件「${name}」？删除后磁盘文件与记录均不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return // 用户取消
  }
  await deleteCadFile(row.id)
  ElMessage.success('已删除')
  await loadFiles()
}

onMounted(loadFiles)
</script>

<style scoped>
.page { max-width: 1180px; }
.muted { color: #c0c4cc; }
.upload-hint { padding: 20px 0; text-align: center; }
.upload-hint .sub { color: #999; font-size: 13px; }
</style>
