<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="brand-section-title">审查报告</span>
          <div class="header-actions">
            <el-select 
              v-model="selectedTaskId" 
              placeholder="请选择任务" 
              style="width: 200px; margin-right: 10px"
              @change="handleTaskChange"
            >
              <el-option 
                v-for="task in taskList" 
                :key="task.id" 
                :label="task.taskName" 
                :value="task.id" 
              />
            </el-select>
            <el-button type="primary" @click="exportPDF" :disabled="!taskId || !isAdmin">导出PDF</el-button>
          </div>
        </div>
      </template>
      <div class="page-content" v-if="taskId">
        <!-- 对接异常 / 任务失败提示 -->
        <el-alert
          v-if="taskDetail.taskStatus === 'FAILED'"
          type="error"
          :closable="false"
          show-icon
          class="fail-banner"
        >
          <template #title>
            <span>审查任务失败（FAILED）—— S1 / 引擎对接异常，未生成有效审查结果</span>
          </template>
          <div class="fail-reason">对接异常原因：{{ failureReason || '未记录具体原因' }}</div>
        </el-alert>

        <!-- 真实工程信息 -->
        <el-card class="info-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>真实工程信息</span>
              <el-tag v-if="taskDetail.designTaskId" type="info" effect="plain">{{ taskDetail.designTaskId }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="工程名称">{{ taskDetail.taskName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="工程区域">{{ designMeta.region || '-' }}</el-descriptions-item>
            <el-descriptions-item label="工程类型">{{ designMeta.designType || '-' }}</el-descriptions-item>
            <el-descriptions-item label="设备总数">{{ designMeta.totalDevices != null ? designMeta.totalDevices + ' 个' : '-' }}</el-descriptions-item>
            <el-descriptions-item v-if="designMeta && designMeta.designTaskId" label="数据来源">
              <el-tag :type="dataSourceTagType" effect="plain" size="small">
                {{ dataSourceLabel }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="规则覆盖率">{{ formatPercent(taskDetail.coverageRate) }}</el-descriptions-item>
            <el-descriptions-item label="审查规则总数">{{ taskDetail.totalCount || '-' }}</el-descriptions-item>
            <el-descriptions-item label="图层分布" :span="3">
              <el-tag v-for="(cnt, layer) in layerCounts" :key="layer" class="layer-tag" type="info" effect="plain">
                {{ layer }}: {{ cnt }}
              </el-tag>
              <span v-if="!layerCounts || !Object.keys(layerCounts).length" class="muted">-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 统计卡片 -->
        <el-row :gutter="16" class="stats-row">
          <el-col :span="4">
            <el-card class="stat-card">
              <div class="stat-item">
                <div class="stat-value">{{ (statistics.critical || 0) + (statistics.error || 0) + (statistics.warning || 0) }}</div>
                <div class="stat-label">违规总数</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="5">
            <el-card class="stat-card critical">
              <div class="stat-item">
                <div class="stat-value">{{ statistics.critical || 0 }}</div>
                <div class="stat-label">严重(critical)</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="5">
            <el-card class="stat-card error">
              <div class="stat-item">
                <div class="stat-value">{{ statistics.error || 0 }}</div>
                <div class="stat-label">错误(error)</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="5">
            <el-card class="stat-card warning">
              <div class="stat-item">
                <div class="stat-value">{{ statistics.warning || 0 }}</div>
                <div class="stat-label">警告(warning)</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="5">
            <el-card class="stat-card pending">
              <div class="stat-item">
                <div class="stat-value">{{ statistics.pending || 0 }}</div>
                <div class="stat-label">待核查(pending)</div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 筛选条件 -->
        <div class="filter-bar">
          <el-select 
            v-model="filterRiskLevel" 
            placeholder="风险等级筛选" 
            style="width: 150px"
            clearable
            @change="handleFilter"
          >
            <el-option label="严重" value="critical" />
            <el-option label="错误" value="error" />
            <el-option label="警告" value="warning" />
            <el-option label="待核查" value="pending" />
          </el-select>
          <el-input 
            v-model="filterKeyword" 
            placeholder="搜索规则编号或名称" 
            style="width: 200px; margin-left: 10px"
            clearable
            @clear="handleFilter"
            @keyup.enter="handleFilter"
          />
          <el-button type="primary" @click="handleFilter" style="margin-left: 10px">搜索</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </div>

        <div class="report-content">
          <el-table 
            :data="tableData" 
            style="width: 100%"
            :loading="loading"
            stripe
          >
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="ruleCode" label="规则编号" width="120" />
            <el-table-column prop="ruleName" label="规则名称" min-width="150" />
            <el-table-column prop="actualValue" label="实际值" width="100" />
            <el-table-column prop="standardValue" label="标准值" min-width="120" />
            <el-table-column label="国标阈值/依据" min-width="180">
              <template #default="scope">
                <span class="threshold-text">{{ getRuleThreshold(scope.row.ruleCode) || scope.row.standardValue || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="riskLevel" label="风险等级" width="100">
              <template #default="scope">
                <el-tag 
                  :type="getRiskLevelType(scope.row.riskLevel)"
                  :effect="'dark'"
                  class="risk-tag"
                  :class="scope.row.riskLevel === 'pending' ? 'risk-tag-pending' : ''"
                >
                  {{ getRiskLevelText(scope.row.riskLevel) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="整改建议" min-width="200">
              <template #default="scope">
                <span :class="'suggestion-text ' + getRiskLevelClass(scope.row.riskLevel)">
                  {{ scope.row.remark || '暂无建议' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="scope">
                <el-button type="primary" link @click="showDetail(scope.row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 分页 -->
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="pagination.pageNum"
              v-model:page-size="pagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <el-empty description="请从上方下拉框选择一个审查任务来查看报告" />
      </div>
    </el-card>

    <el-dialog v-model="showDetailDialog" title="违规详情" width="600px">
      <div v-if="selectedItem" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="规则编号">{{ selectedItem.ruleCode }}</el-descriptions-item>
          <el-descriptions-item label="规则名称">{{ selectedItem.ruleName }}</el-descriptions-item>
          <el-descriptions-item label="风险等级" :span="2">
            <el-tag 
              :type="getRiskLevelType(selectedItem.riskLevel)"
              :effect="'dark'"
              :class="selectedItem.riskLevel === 'pending' ? 'risk-tag-pending' : ''"
            >
              {{ getRiskLevelText(selectedItem.riskLevel) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="实际值">{{ selectedItem.actualValue }}</el-descriptions-item>
          <el-descriptions-item label="标准值">{{ selectedItem.standardValue }}</el-descriptions-item>
          <el-descriptions-item label="整改建议" :span="2">
            <span :class="'suggestion-text ' + getRiskLevelClass(selectedItem.riskLevel)">
              {{ selectedItem.remark || '暂无建议' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ formatTime(selectedItem.createTime) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { resultApi, taskApi, ruleApi } from '../api'
import { useAuth } from '../utils/auth'

const route = useRoute()
const router = useRouter()
const { isAdmin } = useAuth()
const tableData = ref([])
const showDetailDialog = ref(false)
const selectedItem = ref(null)
const taskList = ref([])
const selectedTaskId = ref(null)
const loading = ref(false)

// 真实工程信息（任务详情 + 设计元数据）
const taskDetail = ref({})
const designMeta = ref({})
const rulesMap = ref({})

// 筛选条件
const filterRiskLevel = ref('')
const filterKeyword = ref('')

// 分页
const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0
})

// 统计信息
const statistics = reactive({
  total: 0,
  critical: 0,
  error: 0,
  warning: 0,
  pending: 0
})

const taskId = computed(() => route.params.taskId || selectedTaskId.value)

// 任务失败时的对接异常原因：取自结果表中 SYSTEM 伪规则行的 remark（由后端 recordIntegrationFailure 写入）
const failureReason = computed(() => {
  const row = (tableData.value || []).find(r => r.ruleCode === 'SYSTEM')
  return row ? row.remark : ''
})

// 设计元数据中的图层分布（dict -> 对象），用于报告页展示真实工程图层构成
const layerCounts = computed(() => {
  const lc = designMeta.value && designMeta.value.layerCounts
  return lc && typeof lc === 'object' ? lc : {}
})

// 数据来源标签：依据后端 getDesignMeta 返回的 dataSource 字段展示（三级存储：Redis缓存 / 内存态 / 数据库恢复）
const dataSourceLabel = computed(() => {
  const ds = designMeta.value && designMeta.value.dataSource
  if (ds === 'database(数据库恢复)') return '【数据库恢复】'
  if (ds === 'Redis缓存(持久化)') return '缓存命中(持久化)'
  if (ds === '内存态(重启即丢)') return '内存态(未持久化)'
  return ds || '-'
})
const dataSourceTagType = computed(() => {
  const ds = designMeta.value && designMeta.value.dataSource
  if (ds === 'database(数据库恢复)') return 'primary'
  if (ds === 'Redis缓存(持久化)') return 'success'
  if (ds === '内存态(重启即丢)') return 'warning'
  return 'info'
})

const getRiskLevelType = (level) => {
  const types = {
    critical: 'danger',
    error: 'warning',
    warning: 'info',
    pending: 'info'
  }
  return types[level] || 'info'
}

const getRiskLevelText = (level) => {
  const texts = {
    critical: '严重',
    error: '错误',
    warning: '警告',
    pending: '待核查'
  }
  return texts[level] || level
}

const getRiskLevelClass = (level) => {
  return level || 'warning'
}

const formatPercent = (rate) => {
  if (rate == null) return '-'
  return Number(rate).toFixed(2) + '%'
}

// 依据规则编号查询其国标阈值文案（来自规则管理，真实行业规范条款）
const getRuleThreshold = (code) => {
  const r = rulesMap.value[code]
  return r ? r.threshold : ''
}

const formatTime = (time) => {
  if (!time) return '-'
  try {
    const date = new Date(time)
    return date.toLocaleString('zh-CN')
  } catch {
    return time
  }
}

const showDetail = (item) => {
  selectedItem.value = item
  showDetailDialog.value = true
}

const loadTasks = async () => {
  try {
    const res = await taskApi.list()
    taskList.value = res.data || []
  } catch (error) {
    console.error('加载任务列表失败:', error)
  }
}

// 加载任务详情（真实工程编号、名称、覆盖率、规则总数等）
const loadTaskDetail = async () => {
  if (!taskId.value) return
  try {
    const res = await taskApi.get(taskId.value)
    const payload = res.data || {}
    taskDetail.value = payload.task || {}
  } catch (error) {
    console.error('加载任务详情失败:', error)
  }
}

// 加载真实工程设计元数据（区域、图层分布、设备总数）
const loadDesignMeta = async () => {
  if (!taskId.value) return
  try {
    const res = await taskApi.designMeta(taskId.value)
    designMeta.value = res.data || {}
  } catch (error) {
    console.error('加载设计元数据失败:', error)
  }
}

// 加载规则库，建立 规则编号 -> 国标阈值 映射，供报告页"国标阈值/依据"列展示
const loadRules = async () => {
  try {
    const res = await ruleApi.list()
    const map = {}
    ;(res.data || []).forEach(r => { map[r.ruleCode || r.rule_code] = r })
    rulesMap.value = map
  } catch (error) {
    console.error('加载规则库失败:', error)
  }
}

const loadStatistics = async () => {
  if (!taskId.value) return
  try {
    const res = await resultApi.statistics({ taskId: taskId.value })
    Object.assign(statistics, res.data || {})
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

const loadResults = async () => {
  if (!taskId.value) return
  
  loading.value = true
  try {
    const params = {
      taskId: taskId.value,
      pageNum: pagination.pageNum,
      pageSize: pagination.pageSize
    }
    
    if (filterRiskLevel.value) {
      params.riskLevel = filterRiskLevel.value
    }
    
    const res = await resultApi.pageByTask(taskId.value, params)
    
    if (res.data) {
      tableData.value = res.data.list || []
      pagination.total = res.data.total || 0
      pagination.totalPages = res.data.totalPages || 0
    }
  } catch (error) {
    console.error('加载审查结果失败:', error)
    ElMessage.error('加载审查结果失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  pagination.pageNum = 1
  loadResults()
}

const resetFilter = () => {
  filterRiskLevel.value = ''
  filterKeyword.value = ''
  pagination.pageNum = 1
  loadResults()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.pageNum = 1
  loadResults()
}

const handleCurrentChange = (page) => {
  pagination.pageNum = page
  loadResults()
}

const handleTaskChange = (id) => {
  selectedTaskId.value = id
  filterRiskLevel.value = ''
  filterKeyword.value = ''
  pagination.pageNum = 1
  router.push(`/report/${id}`)
}

watch(taskId, () => {
  if (taskId.value) {
    selectedTaskId.value = taskId.value
    loadTaskDetail()
    loadDesignMeta()
    loadRules()
    loadStatistics()
    loadResults()
  }
})

const exportPDF = async () => {
  if (!taskId.value) return
  try {
    ElMessage.info('正在生成 PDF，请稍候…')
    const res = await taskApi.exportPdf(taskId.value)
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // 文件名取自响应头 Content-Disposition（后端已做 UTF-8 编码）
    let filename = `审查报告_${taskId.value}.pdf`
    const cd = (res.headers && (res.headers['content-disposition'] || res.headers['Content-Disposition'])) || ''
    const m = cd.match(/filename\*=UTF-8''([^;]+)/i) || cd.match(/filename="?([^";]+)"?/i)
    if (m) filename = decodeURIComponent(m[1])
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('审查报告 PDF 已生成并开始下载')
  } catch (e) {
    console.error('PDF 导出失败:', e)
    ElMessage.error('PDF 导出失败，请确认任务已完成且服务正常')
  }
}

onMounted(() => {
  loadTasks()
  if (taskId.value) {
    selectedTaskId.value = taskId.value
    loadTaskDetail()
    loadDesignMeta()
    loadRules()
    loadStatistics()
    loadResults()
  }
})
</script>

<style scoped>
.page-container {
  padding: 22px;
}

.page-card {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 4px;
}

.page-content {
  padding-top: 18px;
}

/* —— 真实工程信息卡（视觉焦点）—— */
.info-card {
  margin-bottom: 18px;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff, #f4f9ff);
  border: 1px solid #d6e6ff;
  overflow: hidden;
  box-shadow: 0 2px 16px rgba(16, 42, 82, 0.07);
}
.info-card :deep(.el-card__header) {
  background: linear-gradient(90deg, #e8f1ff, #eafbfb);
  border-bottom: 1px solid #d6e6ff;
}
.info-card :deep(.el-descriptions__label) {
  color: #2b3a4d;
  font-weight: 600;
  background: #f3f8fe;
}
.info-card :deep(.el-descriptions__cell) {
  padding: 11px 14px;
}

.layer-tag {
  margin-right: 8px;
  margin-bottom: 4px;
}

.threshold-text {
  color: #45556b;
  font-size: 13px;
  font-weight: 500;
}

.muted {
  color: #c0c4cc;
}

/* —— 统计卡 —— */
.stats-row {
  margin-bottom: 18px;
}

.stat-card {
  text-align: center;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff, #f6f9fc);
  border: 1px solid var(--brand-border);
  overflow: hidden;
}

.stat-card.critical {
  border-top: 3px solid #f56c6c;
  background: linear-gradient(180deg, #ffffff, #fef2f2);
}

.stat-card.error {
  border-top: 3px solid #e6a23c;
  background: linear-gradient(180deg, #ffffff, #fff7e8);
}

.stat-card.warning {
  border-top: 3px solid #f7ba1e;
  background: linear-gradient(180deg, #ffffff, #fef9ea);
}

.stat-card.pending {
  border-top: 3px solid #909399;
  background: linear-gradient(180deg, #ffffff, #f4f5f7);
}

.stat-card.pending .stat-value {
  color: #909399;
}

.stat-item {
  padding: 12px 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--brand-text);
}

.stat-card.critical .stat-value {
  color: #f56c6c;
}

.stat-card.error .stat-value {
  color: #e6a23c;
}

.stat-card.warning .stat-value {
  color: #f7ba1e;
}

.stat-label {
  font-size: 13px;
  color: var(--brand-text-soft);
  margin-top: 4px;
}

/* —— 筛选条 —— */
.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid var(--brand-border);
  border-radius: 10px;
  box-shadow: 0 1px 6px rgba(16, 42, 82, 0.04);
}

.report-content {
  min-height: 300px;
}

.risk-tag {
  font-weight: 700;
}

.risk-tag-pending {
  background: #f4f4f5 !important;
  border: 1px solid #dcdfe6 !important;
  color: #606266 !important;
}

.suggestion-text {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 5px;
  font-size: 13px;
  font-weight: 500;
}

.suggestion-text.critical {
  color: #f56c6c;
  background: #fef0f0;
}

.suggestion-text.error {
  color: #e6a23c;
  background: #fdf6ec;
}

.suggestion-text.warning {
  color: #b8820a;
  background: #fdf6ec;
}

.suggestion-text.pending {
  color: #606266;
  background: #f4f4f5;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-content {
  padding: 6px 4px 10px;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.header-actions {
  display: flex;
  align-items: center;
}
</style>
