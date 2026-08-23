<template>
  <div class="bom-home">
    <!-- 状态概览卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>总任务数</span></template>
          <div class="stat-value">{{ total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>已完成</span></template>
          <div class="stat-value c-green">{{ doneCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>运行中</span></template>
          <div class="stat-value c-orange">{{ runningCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>失败</span></template>
          <div class="stat-value c-red">{{ failedCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作区 -->
    <el-card class="action-card">
      <template #header><span>BOM 生成</span></template>
      <el-alert type="info" show-icon :closable="false" style="margin-bottom:16px">
        当前使用运城样例数据驱动（mock 模式），设计任务 ID 不影响结果。
      </el-alert>
      <el-form :inline="true">
        <el-form-item label="设计任务 ID">
          <el-input v-model="designTaskId" placeholder="S1 设计任务 UUID" style="width: 280px" />
        </el-form-item>
        <el-form-item label="项目 ID">
          <el-input v-model="projectId" placeholder="项目标识" style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doGenerate" :loading="genLoading" :disabled="polling">
            生成 BOM
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 生成进度条（异步模式下展示） -->
      <div v-if="polling" class="progress-section">
        <el-divider />
        <div class="progress-info">
          <el-tag type="warning" size="large">
            <el-icon class="is-loading"><Loading /></el-icon>
            BOM 正在生成中...
          </el-tag>
          <span class="progress-taskid">任务 ID: {{ pollingTaskId }}</span>
          <span class="progress-elapsed">已等待 {{ elapsed }}s</span>
        </div>
        <el-progress :percentage="pollProgress" :stroke-width="12" :show-text="true"
          :status="pollProgress >= 100 ? 'success' : undefined" />
      </div>
    </el-card>

    <!-- 历史任务列表 -->
    <el-card class="history-card">
      <template #header>
        <div class="card-header">
          <span>历史 BOM 任务</span>
          <el-button size="small" @click="loadHistory">刷新</el-button>
        </div>
      </template>
      <el-table :data="historyList" v-loading="loading" stripe>
        <el-table-column prop="taskId" label="任务 ID" width="280" show-overflow-tooltip />
        <el-table-column prop="designTaskId" label="设计任务" width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalQty" label="物料总数" width="90" />
        <el-table-column prop="mainDeviceQty" label="主设备" width="80" />
        <el-table-column prop="auxiliaryQty" label="辅材" width="80" />
        <el-table-column prop="cableQty" label="线缆" width="80" />
        <el-table-column prop="totalCategories" label="类目数" width="80" />
        <el-table-column prop="createdAt" label="创建时间" width="170" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="$router.push(`/detail/${row.taskId}`)">
              详情
            </el-button>
            <el-button size="small" type="success" @click="doExport(row.taskId)"
              :disabled="row.status !== 'done'">
              导出
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && historyList.length === 0" description="暂无 BOM 任务" />
      <el-pagination
        v-if="total > 0"
        class="pagination"
        v-model:current-page="page"
        :page-size="size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadHistory"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { generateBom, getTaskStatus, listHistory, getExportUrl } from '../api/bom'

const $router = useRouter()

const designTaskId = ref('mock-yuncheng-A001')
const projectId = ref('yuncheng-5g')
const historyList = ref([])
const loading = ref(false)
const genLoading = ref(false)
const page = ref(1)
const size = ref(20)
const total = ref(0)

const polling = ref(false)
const pollingTaskId = ref('')
const pollProgress = ref(0)
const elapsed = ref(0)
let pollTimer = null
let elapsedTimer = null

const doneCount = computed(() => historyList.value.filter(r => r.status === 'done').length)
const runningCount = computed(() => historyList.value.filter(r => r.status === 'running').length)
const failedCount = computed(() => historyList.value.filter(r => r.status === 'failed').length)

const doGenerate = async () => {
  genLoading.value = true
  try {
    // 异步生成 → 立即返回 taskId (status=running)
    const data = await generateBom(designTaskId.value, projectId.value)
    const taskId = data.taskId
    pollingTaskId.value = taskId
    polling.value = true
    genLoading.value = false
    pollProgress.value = 10  // 初始进度
    elapsed.value = 0

    // 启动倒计时
    elapsedTimer = setInterval(() => { elapsed.value++ }, 1000)

    // 启动轮询
    startPolling(taskId)

    ElMessage.success(`BOM 任务已创建: ${taskId}`)
    loadHistory()
  } catch (e) {
    genLoading.value = false
    ElMessage.error('创建任务失败: ' + (e.response?.data?.message || e.message))
  }
}

const startPolling = (taskId) => {
  let attempts = 0
  const maxAttempts = 60  // 最长等 90s
  pollTimer = setInterval(async () => {
    attempts++
    try {
      const status = await getTaskStatus(taskId)
      // 线性模拟进度：每次 +5，最多到 95
      pollProgress.value = Math.min(10 + attempts * 5, 95)

      if (status.status === 'done') {
        pollProgress.value = 100
        clearTimers()
        ElMessage.success(`BOM 生成完成，共 ${status.totalItems || 0} 条物料`)
        loadHistory()
        // 1s 后跳转详情
        setTimeout(() => {
          polling.value = false
          $router.push(`/detail/${taskId}`)
        }, 1000)
      } else if (status.status === 'failed') {
        pollProgress.value = 0
        clearTimers()
        ElMessage.error('BOM 生成失败: ' + (status.error || '请重试'))
        loadHistory()
        polling.value = false
      }
      // running → 继续轮询
    } catch (e) {
      if (attempts >= maxAttempts) {
        clearTimers()
        ElMessage.warning('轮询超时，请手动刷新查看结果')
        loadHistory()
        polling.value = false
      }
    }
  }, 1500)
}

const clearTimers = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null }
}

const loadHistory = async () => {
  loading.value = true
  try {
    const data = await listHistory(page.value, size.value)
    historyList.value = data.records || []
    total.value = data.total || 0
  } catch (e) {
    console.error('加载历史失败', e)
  } finally {
    loading.value = false
  }
}

const doExport = (taskId) => {
  window.open(getExportUrl(taskId), '_blank')
}

const statusType = (s) =>
  ({ pending: 'info', running: 'warning', done: 'success', failed: 'danger' })[s] || 'info'

onMounted(loadHistory)
onUnmounted(clearTimers)
</script>

<style scoped>
.bom-home { padding: 0; }
.stats-row { margin-bottom: 20px; }
.stat-value { font-size: 32px; font-weight: 700; color: #1f3a5f; }
.c-green  { color: #27ae60; }
.c-orange { color: #e67e22; }
.c-red    { color: #e74c3c; }
.action-card { margin-bottom: 20px; }
.history-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }

/* progress section */
.progress-section { margin-top: 8px; }
.progress-info {
  display: flex; align-items: center; gap: 16px; margin-bottom: 12px;
}
.progress-taskid { font-size: 13px; color: #666; }
.progress-elapsed { font-size: 13px; color: #999; margin-left: auto; }
</style>
