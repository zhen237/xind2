<template>
  <div class="task-kanban">
    <!-- Header -->
    <div class="board-header">
      <div class="header-left">
        <h2>任务看板</h2>
        <p class="subtitle">任务主线 S1 → S3 → S4 实时状态（数据来源：S1 设计 / S3 审查 / S4 BOM）</p>
      </div>
      <div class="header-right">
        <el-tag size="large" :type="loading ? 'info' : 'success'">
          更新于 {{ updatedAt }}
        </el-tag>
        <el-button text :loading="loading" @click="loadKanban">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <el-row :gutter="16" class="summary-row" v-if="summary">
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-label">S1 设计任务</div>
          <div class="summary-value">{{ summary.s1Completed }} / {{ summary.s1Total }}</div>
          <div class="summary-sub">已完成 / 总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-label">S3 审查任务</div>
          <div class="summary-value">{{ summary.s3MatchedByTaskNo }} / {{ summary.s1Total }}</div>
          <div class="summary-sub">已与 S1 taskNo  对齐</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-label">S4 BOM 任务</div>
          <div class="summary-value">{{ summary.s4Total }}</div>
          <div class="summary-sub">已生成 BOM 的设计任务</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-label">链路完整率</div>
          <div class="summary-value">{{ pipelineRate }}%</div>
          <div class="summary-sub">S1 完成 + S3 匹配 + S4 已生成</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 看板：行 = S1 任务，列 = S1 / S3 / S4 三段状态 -->
    <el-card shadow="never" class="kanban-card">
      <template #header>
        <div class="kanban-header">
          <span><el-icon><Tickets /></el-icon> S1 → S3 → S4 任务主线</span>
          <span class="row-count">共 {{ rows.length }} 行</span>
        </div>
      </template>

      <div v-if="loading && rows.length === 0" class="loading-box">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon> 加载中...
      </div>
      <div v-else-if="rows.length === 0" class="empty-hint">暂无 S1 任务，请先在 S1 智能设计中创建任务</div>

      <el-table
        v-else
        :data="rows"
        size="small"
        stripe
        border
        :max-height="tableMaxHeight"
      >
        <el-table-column label="任务" min-width="220" fixed>
          <template #default="{ row }">
            <div class="task-cell">
              <div class="task-title">
                <span class="task-id">#{{ row.id }}</span>
                <span class="task-name">{{ row.taskName || row.taskNo || '未命名任务' }}</span>
              </div>
              <div class="task-no" :title="row.taskNo">{{ row.taskNo }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="S1 设计" min-width="160">
          <template #default="{ row }">
            <el-tag :type="s1TagType(row.s1.status)" size="small" effect="light">
              {{ s1StatusText(row.s1.status) }}
            </el-tag>
            <div class="cell-time">{{ formatTime(row.updatedAt) }}</div>
          </template>
        </el-table-column>

        <el-table-column label="S3 审查" min-width="200">
          <template #default="{ row }">
            <template v-if="row.s3 && row.s3.taskName">
              <div class="s3-cell">
                <el-tag
                  :type="s3TagType(row.s3)"
                  size="small"
                  effect="light"
                  class="s3-status-tag"
                >
                  {{ s3StatusText(row.s3) }}
                </el-tag>
                <el-tag v-if="row.s3.coverageRate != null" size="small" effect="plain" type="info">
                  覆盖率 {{ row.s3.coverageRate }}%
                </el-tag>
              </div>
              <div class="s3-detail">
                <span class="badge badge-error" v-if="row.s3.criticalCount">{{ row.s3.criticalCount }}严重</span>
                <span class="badge badge-error" v-if="row.s3.errorCount">{{ row.s3.errorCount }}错误</span>
                <span class="badge badge-warn" v-if="row.s3.warningCount">{{ row.s3.warningCount }}警告</span>
                <span class="cell-muted">共 {{ row.s3.totalCount || 0 }} 项</span>
              </div>
              <div class="s3-task-name" :title="row.s3.taskName">{{ row.s3.taskName }}</div>
            </template>
            <span v-else class="cell-muted">未送审</span>
          </template>
        </el-table-column>

        <el-table-column label="S4 BOM" min-width="180">
          <template #default="{ row }">
            <template v-if="row.s4 && row.s4.taskId">
              <el-tag :type="s4TagType(row.s4.status)" size="small" effect="light">
                {{ s4StatusText(row.s4.status) }}
              </el-tag>
              <div class="cell-time">
                {{ row.s4.totalQty || 0 }} 件物料 · {{ formatTime(row.s4.createTime) }}
              </div>
              <div v-if="row.s4.bomCount > 1" class="cell-muted">
                共生成 {{ row.s4.bomCount }} 次
              </div>
            </template>
            <span v-else class="cell-muted">未生成</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <p class="source-note">
      数据从 S4 /api/s4/bom/kanban 聚合而来（S1 任务 + S3 审查 + S4 BOM 三段按 taskNo/designTaskId 串联）。
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Refresh, Loading, Tickets } from '@element-plus/icons-vue'
import axios from 'axios'

const rows = ref([])
const summary = ref(null)
const loading = ref(false)
const updatedAt = ref('--')
const tableMaxHeight = ref(window.innerHeight - 320)

let pollTimer = null

async function loadKanban() {
  loading.value = true
  try {
    const r = await axios.get('/api/s4/bom/kanban')
    const data = r.data || {}
    rows.value = Array.isArray(data.rows) ? data.rows : []
    summary.value = data.summary || null
    const now = new Date()
    updatedAt.value = `${now.toTimeString().slice(0, 19)}`
  } catch (e) {
    console.error('任务看板加载失败', e)
  } finally {
    loading.value = false
  }
}

const pipelineRate = computed(() => {
  if (!summary.value || !summary.value.s1Total) return 0
  // 完整链路 = S1 已完成 且 S3 已匹配 且 S4 已生成
  const complete = rows.value.filter((r) => {
    const s1ok = String(r.s1?.status || '').toLowerCase() === 'completed'
    const s3ok = !!r.s3?.taskName
    const s4ok = !!r.s4?.taskId
    return s1ok && s3ok && s4ok
  }).length
  return Math.round((complete * 1000) / summary.value.s1Total) / 10
})

const S1_STATUS = {
  draft: { label: '草稿', type: 'info' },
  generating: { label: '生成中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}
function s1StatusText(s) { return (S1_STATUS[s] || { label: s || '—' }).label }
function s1TagType(s) { return (S1_STATUS[s] || { type: 'info' }).type }

function s3TagType(s3) {
  const c = Number(s3.criticalCount || 0) + Number(s3.errorCount || 0)
  if (c > 0) return 'danger'
  if (Number(s3.warningCount || 0) > 0) return 'warning'
  if (s3.taskStatus === 'COMPLETED') return 'success'
  return 'info'
}
function s3StatusText(s3) {
  const c = Number(s3.criticalCount || 0) + Number(s3.errorCount || 0)
  if (c > 0) return `${c} 违规`
  if (Number(s3.warningCount || 0) > 0) return `${s3.warningCount} 警告`
  return '已审查'
}

const S4_STATUS = {
  done: { label: '已生成', type: 'success' },
  running: { label: '生成中', type: 'warning' },
  failed: { label: '失败', type: 'danger' },
  pending: { label: '待生成', type: 'info' }
}
function s4StatusText(s) { return (S4_STATUS[s] || { label: s || '未生成' }).label }
function s4TagType(s) { return (S4_STATUS[s] || { type: 'info' }).type }

function formatTime(t) {
  if (!t) return ''
  const s = String(t)
  return s.length > 16 ? s.slice(0, 16).replace('T', ' ') : s.replace('T', ' ')
}

function onResize() {
  tableMaxHeight.value = window.innerHeight - 320
}

onMounted(() => {
  loadKanban()
  pollTimer = setInterval(loadKanban, 30000)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.task-kanban {
  padding: 24px;
  min-height: 100%;
  background: #f8fafc;
}

.board-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.board-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 4px 0;
}
.subtitle {
  color: #64748b;
  font-size: 14px;
  margin: 0;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.summary-row {
  margin-bottom: 20px;
}
.summary-card {
  text-align: center;
  padding: 16px 0;
}
.summary-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 6px;
}
.summary-value {
  font-size: 28px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1.2;
}
.summary-sub {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

.kanban-card {
  background: white;
  border-radius: 12px;
}
.kanban-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.row-count {
  font-weight: 400;
  font-size: 12px;
  color: #94a3b8;
}

.task-cell { padding: 4px 0; }
.task-title { display: flex; gap: 6px; align-items: baseline; }
.task-id { font-weight: 700; color: #2563eb; }
.task-name { color: #1e293b; }
.task-no {
  font-size: 11px;
  color: #64748b;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  margin-top: 2px;
}

.s3-cell { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin-bottom: 2px; }
.s3-status-tag { margin-right: 2px; }
.s3-detail { display: flex; gap: 6px; flex-wrap: wrap; font-size: 11px; margin: 2px 0; }
.s3-task-name {
  font-size: 11px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
}
.badge-error { background: #fef2f2; color: #dc2626; }
.badge-warn { background: #fffbeb; color: #d97706; }

.cell-time { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.cell-muted { font-size: 11px; color: #cbd5e1; }

.loading-box, .empty-hint {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
}
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; }

.source-note {
  margin-top: 16px;
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
}
</style>