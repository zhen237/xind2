<template>
  <div class="pipeline-page">
    <el-card class="header-card">
      <div class="header-row">
        <div>
          <h1>XA-202610 通信基建工程数智化设计与交付</h1>
          <p class="subtitle">全流水线概览 — S1 设计 → S3 审查 → S4 BOM转化 → S5 施工监管</p>
        </div>
        <el-tag type="success" size="large">系统运行中</el-tag>
      </div>
    </el-card>

    <!-- 流水线进度条 -->
    <div class="pipeline-bar">
      <div
        v-for="stage in stages"
        :key="stage.id"
        class="stage-node"
        :class="{ active: stage.id === 'S4', current: stage.id === 'S4' }"
        @click="goStage(stage)"
      >
        <div class="stage-dot">
          <el-icon v-if="stage.status === 'online'" :size="20"><CircleCheckFilled /></el-icon>
          <el-icon v-else :size="20"><Clock /></el-icon>
        </div>
        <div class="stage-label">{{ stage.id }}</div>
        <div class="stage-name">{{ stage.shortName }}</div>
        <div class="stage-count">{{ stage.taskCount }} 任务</div>
      </div>
    </div>

    <!-- 真实任务选择（来自 S1，任务主线贯穿） -->
    <el-row :gutter="20" class="section-row">
      <el-col v-for="t in s1Tasks" :key="t.id" :span="8">
        <el-card
          shadow="hover"
          class="scene-card"
          :class="{ selected: selectedDesignId === String(t.id) }"
          @click="selectScene(String(t.id))"
        >
          <div class="scene-icon">{{ t.status === 'completed' ? '✅' : '⏳' }}</div>
          <h3>#{{ t.id }} {{ t.taskName || t.taskNo }}</h3>
          <p>{{ t.taskNo }}</p>
          <el-tag size="small" :type="taskStatusType(t.status)">{{ taskStatusText(t.status) }}</el-tag>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="s1Tasks.length === 0">
        <el-card shadow="hover" class="scene-card">
          <div class="scene-icon">🔄</div>
          <h3>{{ s1TasksLoading ? '加载任务中...' : '暂无 S1 任务' }}</h3>
          <p>请先在 S1 智能设计中创建并执行任务</p>
          <el-button size="small" text type="primary" :loading="s1TasksLoading" @click="loadS1Tasks">刷新</el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 设计→审查 联动区 -->
    <el-row :gutter="20" class="section-row">
      <el-col :span="12">
        <el-card shadow="hover" class="link-card" @click="openS1">
          <template #header>
            <div class="card-header">
              <span>S1 智能设计 — 设备清单</span>
              <el-tag size="small" type="info">点击跳转</el-tag>
            </div>
          </template>
          <div v-if="designLoading" class="loading-box"><el-icon class="is-loading" :size="24"><Loading /></el-icon> 加载中...</div>
          <div v-else-if="designData">
            <div class="source-label">
              <el-icon><Connection /></el-icon>
              数据源：S1 设计任务 #{{ realId }}（真实执行设计产出）
            </div>
            <el-descriptions :column="2" border size="small" style="margin-top:6px;">
              <el-descriptions-item label="方案">{{ designData.projectName }}</el-descriptions-item>
              <el-descriptions-item label="站点类型">{{ siteTypeText(designData.siteType) }}</el-descriptions-item>
              <el-descriptions-item label="设备种类">{{ designData.devices?.length || 0 }}</el-descriptions-item>
              <el-descriptions-item label="设计状态">
                <el-tag type="success" size="small">已生成</el-tag>
              </el-descriptions-item>
            </el-descriptions>
            <div style="margin-top:12px;">
              <h4>设备清单（按型号聚合）</h4>
              <el-table :data="designData.devices" size="small" stripe style="width: 100%" :max-height="240">
                <el-table-column prop="deviceId" label="编号" width="110" show-overflow-tooltip />
                <el-table-column prop="deviceName" label="设备名称" min-width="150" show-overflow-tooltip />
                <el-table-column prop="modelSpec" label="型号" min-width="110" show-overflow-tooltip />
                <el-table-column prop="deviceType" label="类型" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" type="info">{{ row.deviceType }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="qty" label="数量" width="60" align="right" />
              </el-table>
            </div>
            <div v-if="isFallback" style="margin-top:8px;">
              <el-tag size="small" type="warning">演示数据（真实服务不可用）</el-tag>
            </div>
          </div>
          <div v-else class="empty-hint">请选择一个场景查看设计数据</div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover" class="link-card" @click="openS3">
          <template #header>
            <div class="card-header">
              <span>S3 智能审查 — 审查报告</span>
              <el-tag size="small" type="info">点击跳转</el-tag>
            </div>
          </template>
          <div v-if="reviewLoading" class="loading-box"><el-icon class="is-loading" :size="24"><Loading /></el-icon> 加载中...</div>
          <div v-else-if="reviewData">
            <div class="source-label">
              <el-icon><Connection /></el-icon>
              数据源：S3 审查任务 #{{ realId }} · {{ reviewData.taskName || '—' }}
            </div>
            <el-descriptions :column="2" border size="small" style="margin-top:6px;">
              <el-descriptions-item label="审查结果">
                <el-tag :type="reviewTagType(reviewData.result)" size="small">{{ reviewResultText(reviewData.result) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="覆盖率">{{ reviewData.coverageRate != null ? reviewData.coverageRate + '%' : '—' }}</el-descriptions-item>
              <el-descriptions-item label="违规/错误项">{{ reviewData.violations || 0 }}</el-descriptions-item>
              <el-descriptions-item label="警告项">{{ reviewData.warnings || 0 }}</el-descriptions-item>
            </el-descriptions>
            <div style="margin-top:12px;">
              <h4>审查项明细（共 {{ reviewData.checks?.length || 0 }} 项）</h4>
              <el-table :data="reviewData.checks || []" size="small" stripe style="width: 100%" :max-height="240">
                <el-table-column label="等级" width="80">
                  <template #default="{ row }">
                    <el-tag :type="riskTagType(row.riskLevel)" size="small">{{ riskText(row.riskLevel) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="rule" label="规则" width="90" />
                <el-table-column prop="name" label="检查项" min-width="150" show-overflow-tooltip />
                <el-table-column prop="actualValue" label="实测值" min-width="90" show-overflow-tooltip />
                <el-table-column prop="standardValue" label="标准值" min-width="110" show-overflow-tooltip />
              </el-table>
            </div>
            <div v-if="isFallback" style="margin-top:8px;">
              <el-tag size="small" type="warning">演示数据（真实服务不可用）</el-tag>
            </div>
          </div>
          <div v-else class="empty-hint">审查结果将在设计数据加载后自动生成</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- S4 一键生成区 -->
    <el-row :gutter="20" class="section-row">
      <el-col :span="24">
        <el-card shadow="hover" class="s4-card">
          <template #header>
            <div class="card-header">
              <span>S4 施工指令转化 — BOM 生成</span>
              <el-tag size="small" type="danger">核心模块</el-tag>
            </div>
          </template>
          <div class="s4-actions">
            <div class="s4-info">
              <p>将 S1 设计输出的设备布局清单自动转化为可施工的 BOM 物料清单，包含主设备、辅材、线缆三类物料，同步生成关键工序工艺要求和纤芯分配表。</p>
              <p class="highlight-text">施工准备时间：2-4 小时 → <strong>&lt; 1 分钟</strong>（缩短 ≥95%）</p>
            </div>
            <div class="s4-buttons">
              <el-button
                type="primary"
                size="large"
                :loading="generating"
                :disabled="!selectedDesignId"
                @click="generateBOM"
              >
                {{ generating ? '生成中...' : '一键生成 BOM' }}
              </el-button>
              <el-button
                v-if="generatedTaskId"
                size="large"
                @click="goDetail"
              >
                查看详情 →
              </el-button>
            </div>
          </div>
          <!-- 进度条 -->
          <div v-if="generating" class="progress-area">
            <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="20" :text-inside="true">
              <span>{{ progressText }}</span>
            </el-progress>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近 BOM 记录 -->
    <el-card shadow="hover" v-if="recentTasks.length > 0">
      <template #header>
        <span>最近 BOM 生成记录</span>
      </template>
      <el-table :data="recentTasks" size="small" stripe>
        <el-table-column prop="taskId" label="任务 ID" width="200" show-overflow-tooltip />
        <el-table-column prop="designTaskId" label="设计任务" width="100" />
        <el-table-column prop="projectName" label="项目名称" min-width="160" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'done' ? 'success' : row.status === 'running' ? 'warning' : 'info'" size="small">
              {{ row.status === 'done' ? '已完成' : row.status === 'running' ? '运行中' : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalQty" label="物料数" width="80" />
        <el-table-column prop="createdAt" label="创建时间" width="170" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="$router.push(`/detail/${row.taskId}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { CircleCheckFilled, Clock, Loading, WarningFilled, Connection } from '@element-plus/icons-vue'
import { generateBom as apiGenerate, getTaskStatus, listHistory } from '@/api/bom'
import axios from 'axios'

const router = useRouter()

const stages = [
  { id: 'S1', shortName: '智能设计', status: 'online', taskCount: 3 },
  { id: 'S3', shortName: '智能审查', status: 'online', taskCount: 3 },
  { id: 'S4', shortName: 'BOM转化', status: 'online', taskCount: 0, highlight: true },
  { id: 'S5', shortName: '施工监管', status: 'pending', taskCount: 0 },
]

const selectedDesignId = ref('')
const designData = ref(null)
const designLoading = ref(false)
const reviewData = ref(null)
const reviewLoading = ref(false)
const generating = ref(false)
const generatedTaskId = ref('')
const progressPercent = ref(0)
const progressStatus = ref('')
const progressText = ref('')
const recentTasks = ref([])
const realId = ref('')
const isFallback = ref(false)
const s1Tasks = ref([])
const s1TasksLoading = ref(false)

const TASK_STATUS_MAP = {
  draft: { label: '草稿', type: 'info' },
  generating: { label: '生成中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}
const taskStatusText = (s) => (TASK_STATUS_MAP[s] || { label: s || '未知' }).label
const taskStatusType = (s) => (TASK_STATUS_MAP[s] || { type: 'info' }).type

async function loadS1Tasks() {
  s1TasksLoading.value = true
  try {
    const r = await axios.get('/api/s4/bom/s1-tasks')
    const list = Array.isArray(r.data) ? r.data : (r.data?.data || [])
    // 取最近 3 条已完成/执行中的任务
    s1Tasks.value = list.slice(0, 3)
  } catch {
    s1Tasks.value = []
  } finally {
    s1TasksLoading.value = false
  }
}

let pollTimer = null

const deviceSummary = computed(() => {
  if (!designData.value?.devices) return {}
  const summary = {}
  designData.value.devices.forEach(d => {
    const t = d.deviceType || 'unknown'
    summary[t] = (summary[t] || 0) + (d.qty || 1)
  })
  return summary
})

async function selectScene(designId) {
  selectedDesignId.value = designId
  designLoading.value = true
  reviewLoading.value = true
  try {
    const r = await axios.get(`/api/s4/bom/design-review/${designId}`)
    const payload = r.data
    designData.value = payload.design || null
    reviewData.value = payload.review || null
    realId.value = payload.realId || designId
    isFallback.value = !!payload.fallback
  } catch (e) {
    designData.value = null
    reviewData.value = null
    console.error('加载设计审查数据失败', e)
  } finally {
    designLoading.value = false
    reviewLoading.value = false
  }
}

function siteTypeText(type) {
  const map = { macro: '宏站', indoor: '室分', micro: '微站', cable: '管线', site: '站点' }
  return map[type] || type || '未知'
}

function reviewTagType(result) {
  if (result === 'blocked') return 'danger'
  if (result === 'approved' || result === 'passed') return 'success'
  if (result === 'allowed_with_warnings') return 'warning'
  return 'info'
}

function reviewResultText(result) {
  if (result === 'blocked') return '拦截'
  if (result === 'approved' || result === 'passed') return '通过'
  if (result === 'allowed_with_warnings') return '通过(有提示)'
  return result || '未知'
}

function riskColor(level) {
  const map = { critical: '#F56C6C', error: '#E6A23C', warning: '#E6A23C', pending: '#909399' }
  return map[level] || '#67C23A'
}

function riskTagType(level) {
  if (level === 'critical' || level === 'error') return 'danger'
  if (level === 'warning') return 'warning'
  if (level === 'pending') return 'info'
  return 'success'
}

function riskText(level) {
  const map = { critical: '严重', error: '错误', warning: '警告', pending: '待定', approved: '通过', passed: '通过', ok: '通过' }
  return map[level] || '通过'
}

function isPass(level) {
  return !level || ['approved', 'passed', 'ok'].includes(level)
}

function formatTime(t) {
  if (!t) return '-'
  const s = String(t)
  return s.length > 19 ? s.slice(0, 19).replace('T', ' ') : s.replace('T', ' ')
}

async function generateBOM() {
  if (!selectedDesignId.value) return
  generating.value = true
  progressPercent.value = 10
  progressText.value = '正在提交 BOM 生成任务...'

  try {
    const r = await apiGenerate(selectedDesignId.value, designData.value?.projectId || '')
    const taskId = r.taskId
    generatedTaskId.value = taskId
    progressPercent.value = 30
    progressText.value = 'Python 引擎计算中...'
    startPolling(taskId)
  } catch (e) {
    generating.value = false
    progressStatus.value = 'exception'
    progressText.value = '生成失败'
  }
}

function startPolling(taskId) {
  let dots = 0
  pollTimer = setInterval(async () => {
    dots = (dots + 1) % 4
    const dotStr = '.'.repeat(dots)
    try {
      const r = await getTaskStatus(taskId)
      const s = r.status
      if (s === 'done') {
        clearInterval(pollTimer)
        progressPercent.value = 100
        progressStatus.value = 'success'
        progressText.value = `生成完成！${r.totalItems || 0} 条物料`
        generating.value = false
        loadRecentTasks()
      } else if (s === 'failed') {
        clearInterval(pollTimer)
        progressStatus.value = 'exception'
        progressText.value = r.error || '生成失败'
        generating.value = false
      } else {
        progressPercent.value = Math.min(90, progressPercent.value + 5)
        progressText.value = `BOM 引擎计算中${dotStr}`
      }
    } catch {
      progressPercent.value = Math.min(90, progressPercent.value + 2)
      progressText.value = `等待引擎响应${dotStr}`
    }
  }, 1500)
}

async function loadRecentTasks() {
  try {
    const r = await listHistory(1, 10)
    recentTasks.value = r.records || []
    stages[2].taskCount = r.total || 0
  } catch { /* ignore */ }
}

function goDetail() {
  if (generatedTaskId.value) {
    router.push(`/detail/${generatedTaskId.value}`)
  }
}

function goStage(stage) {
  if (stage.id === 'S4') {
    router.push('/')
  } else if (stage.id === 'S1') {
    openS1()
  } else if (stage.id === 'S3') {
    openS3()
  }
}

function openS1() {
  window.open('http://localhost:5174/modules/m03', '_blank')
}

function openS3() {
  window.open('http://localhost:5189/modules/s3', '_blank')
}

onMounted(async () => {
  loadRecentTasks()
  await loadS1Tasks()
  if (s1Tasks.value.length > 0) {
    selectScene(String(s1Tasks.value[0].id))
  } else {
    selectScene('D001')
  }
})
</script>

<style scoped>
.pipeline-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
.header-card {
  margin-bottom: 20px;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-row h1 {
  font-size: 22px;
  margin: 0 0 6px 0;
  color: #303133;
}
.subtitle {
  color: #909399;
  margin: 0;
}
.section-row {
  margin-bottom: 20px;
}

/* 流水线进度条 */
.pipeline-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 10px;
  margin-bottom: 20px;
  background: linear-gradient(90deg, #ecf5ff, #f0f9eb, #fdf6ec, #fef0f0);
  border-radius: 12px;
  position: relative;
}
.pipeline-bar::before {
  content: '';
  position: absolute;
  top: 46px;
  left: 50px;
  right: 50px;
  height: 3px;
  background: #dcdfe6;
  z-index: 0;
}
.stage-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  z-index: 1;
  padding: 0 15px;
  transition: transform 0.2s;
}
.stage-node:hover { transform: scale(1.1); }
.stage-node.active .stage-dot { color: #409eff; }
.stage-dot {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: white;
  border: 3px solid #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  margin-bottom: 8px;
  transition: all 0.3s;
}
.stage-node.active .stage-dot {
  border-color: #409eff;
  color: #409eff;
  box-shadow: 0 0 12px rgba(64,158,255,0.3);
}
.stage-node.current .stage-dot {
  border-color: #e6a23c;
  color: #e6a23c;
  box-shadow: 0 0 16px rgba(230,162,60,0.4);
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(230,162,60,0.3); }
  50% { box-shadow: 0 0 20px rgba(230,162,60,0.6); }
}
.stage-label {
  font-weight: 700;
  font-size: 14px;
  color: #303133;
}
.stage-name {
  font-size: 12px;
  color: #909399;
  margin: 2px 0;
}
.stage-count {
  font-size: 11px;
  color: #c0c4cc;
}

/* 场景卡片 */
.scene-card {
  cursor: pointer;
  text-align: center;
  transition: all 0.3s;
  border: 2px solid transparent;
}
.scene-card:hover {
  border-color: #409eff;
  transform: translateY(-3px);
}
.scene-card.selected {
  border-color: #409eff;
  background: #f5f7fa;
  box-shadow: 0 4px 12px rgba(64,158,255,0.15);
}
.scene-icon { font-size: 36px; margin-bottom: 8px; }
.scene-card h3 { margin: 0 0 6px 0; font-size: 16px; }
.scene-card p { color: #909399; font-size: 13px; margin: 0 0 8px 0; }

.card-header { display: flex; justify-content: space-between; align-items: center; }
.empty-hint { color: #c0c4cc; text-align: center; padding: 30px 0; }
.loading-box { text-align: center; padding: 30px 0; color: #909399; }

.device-tags { margin-top: 6px; }
.check-item { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 13px; color: #606266; }
.source-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  padding: 4px 8px;
}
.risk-critical { color: #f56c6c; font-weight: 600; }
.risk-error { color: #e6a23c; font-weight: 600; }
.risk-warning { color: #e6a23c; }
.risk-pending { color: #909399; }
.link-card { cursor: pointer; transition: all 0.2s; }
.link-card:hover { border-color: #409eff; box-shadow: 0 4px 12px rgba(64,158,255,0.15); }

/* S4 核心区 */
.s4-card { border: 2px solid #e6a23c; }
.s4-actions { display: flex; justify-content: space-between; align-items: center; gap: 24px; }
.s4-info p { margin: 0 0 6px 0; color: #606266; font-size: 14px; }
.highlight-text { color: #e6a23c !important; }
.s4-buttons { display: flex; gap: 12px; flex-shrink: 0; }
.progress-area { margin-top: 16px; }
</style>
