<template>
  <div class="ftth-page">
    <el-card class="header-card">
      <div class="header-row">
        <div>
          <h1>FTTH 交付物（光路由表 + 光交箱汇总 + 机柜熔接盘图 + 系统图）</h1>
          <p class="subtitle">
            上传含 8 个 .dbf 的 Shapefile 目录（IMB / SITE / BOITE / CABLE / PTECH / INFRASTRUCTURE / ZNRO / ZPM），
            自动生成合并 Excel 工作簿。复用 QGIS 插件
            <code>qgis-plugin/ftth.export_runner.export_from_dbf_single_workbook</code> 口径。
          </p>
        </div>
      </div>
      <el-alert
        v-if="!isMock"
        type="info"
        :closable="false"
        show-icon
        style="margin-top:12px;"
      >
        真实模式：上传文件经 Spring Boot 代理转发到 Python 引擎（端口 8100），使用 dbfread 解析，
        不依赖 PyQGIS。
      </el-alert>
    </el-card>

    <!-- 1. 8 层 .dbf 上传表单 -->
    <el-card class="upload-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><b>① 上传 8 层 .dbf 文件</b></span>
          <el-tag size="small">字段名已截断到 10 字符（dBASE 历史限制）</el-tag>
        </div>
      </template>

      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col v-for="layer in DBF_LAYERS" :key="layer" :xs="24" :sm="12" :md="8" :lg="6">
            <el-form-item :label="`${layer}.dbf`">
              <el-upload
                :ref="el => bindUploadRef(el, layer)"
                :auto-upload="false"
                :limit="1"
                :on-change="(file) => onFileSelected(layer, file)"
                :on-remove="() => onFileRemoved(layer)"
                :show-file-list="true"
                accept=".dbf,.DBF"
                drag
              >
                <el-icon style="font-size: 28px; color: #909399;"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  <em>点击 / 拖拽</em> {{ layer }}.dbf
                </div>
                <template #tip>
                  <div class="el-upload__tip">{{ layerHint(layer) }}</div>
                </template>
              </el-upload>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <el-divider />

      <div class="upload-actions">
        <el-button
          type="primary"
          size="large"
          :loading="uploading"
          :disabled="!allSelected || uploading"
          @click="onUpload"
        >
          {{ uploading ? '解析中…（可能 5-10 秒）' : '生成 FTTH 交付物' }}
        </el-button>
        <el-button :disabled="uploading" @click="clearAll">清空</el-button>
        <el-tag v-if="readyCount < 8" type="warning" size="small">
          已选 {{ readyCount }} / 8 层
        </el-tag>
        <el-tag v-else type="success" size="small">8 层齐全，可上传</el-tag>
      </div>
    </el-card>

    <!-- 2. 解析结果 -->
    <el-card v-if="result" class="result-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><b>② 解析结果（task {{ result.taskId }}）</b></span>
          <el-tag size="small" type="success">耗时 {{ result.elapsedMs }} ms</el-tag>
        </div>
      </template>

      <el-descriptions :column="4" border style="margin-bottom:16px;">
        <el-descriptions-item v-for="(count, layer) in result.layerCounts" :key="layer" :label="layer">
          <b>{{ count }}</b> 条记录
        </el-descriptions-item>
      </el-descriptions>

      <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px;">
        合并工作簿共 <b>{{ result.sheetCount }}</b> 个 sheet：
        1 个「光路由表」 + 1 个「光交箱汇总」 + 每个 PM 各 1 个「机柜熔接盘图」+「系统图」。
        自检报告 + JSON 数据可单独下载。
      </el-alert>

      <el-table :data="sheetRows" stripe size="small" :max-height="400" style="width:100%;">
        <el-table-column prop="idx" label="#" width="50" />
        <el-table-column prop="name" label="Sheet 名称" show-overflow-tooltip />
        <el-table-column label="类型" width="180">
          <template #default="{ row }">
            <el-tag size="small" :type="tagType(row.category)">{{ row.categoryLabel }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <div class="download-actions">
        <el-button
          type="primary"
          size="large"
          :loading="downloading === 'xlsx'"
          @click="onDownload('xlsx')"
        >
          下载合并工作簿 .xlsx
        </el-button>
        <el-button @click="onDownload('validation')" :loading="downloading === 'validation'">
          下载自检报告 .json
        </el-button>
        <el-button @click="onDownload('json')" :loading="downloading === 'json'">
          下载 ftth-data .json
        </el-button>
      </div>
    </el-card>

    <!-- 错误提示 -->
    <el-alert v-if="errorMsg" type="error" :title="errorMsg" :closable="true" show-icon
              @close="errorMsg = ''" style="margin-top:16px;" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

// ── 8 层 .dbf 清单（与 qgis-plugin/ftth/field_map.LAYER_FILE_PREFIX 对齐） ──
const DBF_LAYERS = ['IMB', 'SITE', 'BOITE', 'CABLE', 'PTECH', 'INFRASTRUCTURE', 'ZNRO', 'ZPM']

const LAYER_HINTS = {
  IMB: '楼栋/住户（点）',
  SITE: '技术站点 NRO/PM（点）',
  BOITE: '光箱 BPE/PBO（点）',
  CABLE: '光缆（线）',
  PTECH: '杆/井技术点（点）',
  INFRASTRUCTURE: '管道/杆路（线）',
  ZNRO: 'OLT 覆盖范围（面）',
  ZPM: 'PM/SRO 范围（面）',
}
function layerHint(layer) { return LAYER_HINTS[layer] || '' }

// 文件引用（按 layer 名索引到原生 File 对象）
const fileMap = ref({})           // { IMB: File, ... }
const uploadRefs = ref({})        // { IMB: UploadInstance, ... }

function bindUploadRef(el, layer) {
  if (el) uploadRefs.value[layer] = el
}

function onFileSelected(layer, file) {
  if (file?.raw) fileMap.value[layer] = file.raw
}
function onFileRemoved(layer) {
  delete fileMap.value[layer]
}

const readyCount = computed(() => Object.keys(fileMap.value).length)
const allSelected = computed(() => readyCount.value === DBF_LAYERS.length)

function clearAll() {
  fileMap.value = {}
  for (const ref of Object.values(uploadRefs.value)) {
    try { ref?.clear?.() } catch (_) { /* noop */ }
  }
}

// ── 上传 → 解析 ──────────────────────────────────────────────
const uploading = ref(false)
const result = ref(null)
const errorMsg = ref('')

async function onUpload() {
  if (!allSelected.value) return
  uploading.value = true
  errorMsg.value = ''
  result.value = null
  try {
    const form = new FormData()
    for (const layer of DBF_LAYERS) {
      form.append('files', fileMap.value[layer], `${layer}.dbf`)
    }
    const url = '/api/s4/ftth/upload'
    const r = await axios.post(url, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60_000,
    })
    result.value = r.data
    ElMessage.success(`FTTH 交付物生成成功：${r.data.sheetCount} 个 sheet`)
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || String(e)
    errorMsg.value = `上传/解析失败：${detail}`
    console.error('FTTH upload failed', e)
  } finally {
    uploading.value = false
  }
}

// ── sheet 列表（按类型分组展示） ──────────────────────────────
const sheetRows = computed(() => {
  if (!result.value?.sheetNames) return []
  return result.value.sheetNames.map((name, i) => ({
    idx: i + 1,
    name,
    category: classifySheet(name),
    categoryLabel: classifySheetLabel(name),
  }))
})
function classifySheet(name) {
  if (name === '光路由表') return 'routes'
  if (name === '光交箱汇总') return 'boite'
  if (name.startsWith('Plan_Baie_')) return 'plan_de_baie'
  if (name.startsWith('Syno_')) return 'synoptique'
  return 'other'
}
function classifySheetLabel(cat) {
  return ({
    routes: '光路由表',
    boite: '光交箱汇总',
    plan_de_baie: '机柜熔接盘图',
    synoptique: '系统图',
    other: '其他',
  })[cat] || cat
}
function tagType(cat) {
  return ({ routes: 'primary', boite: 'success', plan_de_baie: 'warning', synoptique: 'info', other: '' })[cat] || ''
}

// ── 下载 ──────────────────────────────────────────────────────
const downloading = ref('')
async function onDownload(kind) {
  if (!result.value) return
  downloading.value = kind
  try {
    let url, filename, mime
    if (kind === 'xlsx') {
      url = `/api/s4/ftth/${result.value.taskId}/download`
      filename = `${result.value.taskId}_FTTH_Deliverables.xlsx`
      mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    } else if (kind === 'validation') {
      url = `/api/s4/ftth/${result.value.taskId}/validation`
      filename = `${result.value.taskId}_ftth-validation.json`
      mime = 'application/json'
    } else {
      url = `/api/s4/ftth/${result.value.taskId}/json`
      filename = `${result.value.taskId}_ftth-data.json`
      mime = 'application/json'
    }
    const r = await axios.get(url, { responseType: 'blob' })
    const blob = new Blob([r.data], { type: mime })
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
  } catch (e) {
    ElMessage.error(`下载失败：${e?.message || e}`)
  } finally {
    downloading.value = ''
  }
}

// 是否 mock 模式（前端 VITE_USE_MOCK=true 时，axios adapter 走 mock）
const isMock = computed(() => {
  try {
    return import.meta.env?.VITE_USE_MOCK === 'true' || import.meta.env?.VITE_USE_MOCK === true
  } catch { return false }
})

onMounted(() => {
  // 初始无操作
})
</script>

<style scoped>
.ftth-page { max-width: 1280px; margin: 0 auto; padding: 20px; }
.header-card { margin-bottom: 20px; }
.header-row { display: flex; justify-content: space-between; align-items: flex-start; }
.header-row h1 { font-size: 22px; margin: 0 0 6px 0; color: #303133; }
.subtitle { color: #606266; margin: 0; font-size: 13px; line-height: 1.6; }
.subtitle code { background: #f0f9ff; padding: 1px 6px; border-radius: 3px; color: #409eff; font-size: 12px; }
.upload-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.upload-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.result-card { margin-bottom: 20px; }
.download-actions { display: flex; gap: 12px; flex-wrap: wrap; }
</style>
