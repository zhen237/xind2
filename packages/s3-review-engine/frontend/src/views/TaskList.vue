<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="brand-section-title">审查任务列表</span>
          <div class="card-actions">
            <el-select v-model="filterStatus" placeholder="按状态筛选" style="width: 120px; margin-right: 10px">
              <el-option label="全部" value="" />
              <el-option label="待执行" value="PENDING" />
              <el-option label="审查中" value="PROCESSING" />
              <el-option label="已完成" value="COMPLETED" />
              <el-option label="失败" value="FAILED" />
            </el-select>
            <el-select v-model="filterRiskLevel" placeholder="按风险等级筛选" style="width: 120px; margin-right: 10px">
              <el-option label="全部" value="" />
              <el-option label="严重" value="critical" />
              <el-option label="错误" value="error" />
              <el-option label="警告" value="warning" />
            </el-select>
            <el-button type="primary" @click="showCreateDialog = true">发起审查</el-button>
          </div>
        </div>
      </template>
      <div class="page-content">
        <el-table :data="tableData" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="designTaskId" label="设计任务ID" width="150" />
          <el-table-column prop="taskName" label="任务名称" />
          <el-table-column prop="taskStatus" label="任务状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.taskStatus)">
                {{ getStatusText(scope.row.taskStatus) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="风险统计" width="200">
            <template #default="scope">
              <div class="risk-stats">
                <span v-if="scope.row.criticalCount > 0" class="risk-item critical">
                  严重 {{ scope.row.criticalCount }}
                </span>
                <span v-if="scope.row.errorCount > 0" class="risk-item error">
                  错误 {{ scope.row.errorCount }}
                </span>
                <span v-if="scope.row.warningCount > 0" class="risk-item warning">
                  警告 {{ scope.row.warningCount }}
                </span>
                <span v-if="!scope.row.criticalCount && !scope.row.errorCount && !scope.row.warningCount" class="risk-item none">
                  无违规
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="coverageRate" label="覆盖率(%)" width="120">
            <template #default="scope">
              {{ scope.row.coverageRate ? scope.row.coverageRate.toFixed(1) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="createTime" label="创建时间" width="180" />
          <el-table-column label="操作" width="260" align="center">
            <template #default="scope">
              <div class="action-btns">
                <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
                <el-button size="small" @click="viewReport(scope.row.id)">报告</el-button>
                <el-button
                  size="small"
                  type="warning"
                  @click="handleRecheck(scope.row)"
                  :disabled="scope.row.taskStatus === 'PROCESSING'"
                >重新复核</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="showCreateDialog" title="发起审查" width="400px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设计任务ID" required>
          <el-input v-model="form.designTaskId" placeholder="请输入设计任务ID" />
        </el-form-item>
        <el-form-item label="任务名称" required>
          <el-input v-model="form.taskName" placeholder="请输入任务名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确认创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetailDialog" title="任务详情" width="600px">
      <div v-if="taskDetail" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ taskDetail.task.id }}</el-descriptions-item>
          <el-descriptions-item label="设计任务ID">{{ taskDetail.task.designTaskId }}</el-descriptions-item>
          <el-descriptions-item label="任务名称">{{ taskDetail.task.taskName }}</el-descriptions-item>
          <el-descriptions-item label="任务状态">
            <el-tag :type="getStatusType(taskDetail.task.taskStatus)">
              {{ getStatusText(taskDetail.task.taskStatus) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ taskDetail.task.createTime }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ taskDetail.task.updateTime }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="statistics-section">
          <h4>审查统计</h4>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-label">规则总数</span>
              <span class="stat-value">{{ taskDetail.statistics.totalRules || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">违规总数</span>
              <span class="stat-value">{{ taskDetail.statistics.totalViolations || 0 }}</span>
            </div>
            <div class="stat-item critical">
              <span class="stat-label">严重</span>
              <span class="stat-value">{{ taskDetail.statistics.criticalCount || 0 }}</span>
            </div>
            <div class="stat-item error">
              <span class="stat-label">错误</span>
              <span class="stat-value">{{ taskDetail.statistics.errorCount || 0 }}</span>
            </div>
            <div class="stat-item warning">
              <span class="stat-label">警告</span>
              <span class="stat-value">{{ taskDetail.statistics.warningCount || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">覆盖率</span>
              <span class="stat-value">{{ taskDetail.statistics.coverageRate ? taskDetail.statistics.coverageRate.toFixed(1) + '%' : '-' }}</span>
            </div>
          </div>
        </div>

        <div v-if="taskDetail.results && taskDetail.results.length > 0" class="results-section">
          <h4>违规详情</h4>
          <el-table :data="taskDetail.results" style="width: 100%" max-height="300">
            <el-table-column prop="ruleCode" label="规则编号" width="100" />
            <el-table-column prop="ruleName" label="规则名称" />
            <el-table-column prop="riskLevel" label="风险等级" width="100">
              <template #default="scope">
                <el-tag :type="getRiskLevelType(scope.row.riskLevel)">
                  {{ getRiskLevelText(scope.row.riskLevel) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="actualValue" label="实际值" width="100" />
            <el-table-column prop="standardValue" label="标准值" width="120" />
          </el-table>
        </div>
        <div v-else class="empty-results">
          暂无违规记录
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button
          type="success"
          @click="handleForwardToS4(taskDetail.task)"
          :disabled="taskDetail?.task?.taskStatus === 'PROCESSING'"
        >生成施工指令(BOM)</el-button>
        <el-button 
          type="primary" 
          @click="handleRecheck(taskDetail.task)"
          :disabled="taskDetail?.task?.taskStatus === 'PROCESSING'"
        >重新复核</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taskApi } from '../api'

const router = useRouter()
const tableData = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const taskDetail = ref(null)

const filterStatus = ref('')
const filterRiskLevel = ref('')

const form = reactive({
  designTaskId: '',
  taskName: ''
})

const getStatusType = (status) => {
  const types = {
    PENDING: 'info',
    PROCESSING: 'warning',
    COMPLETED: 'success',
    FAILED: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    PENDING: '待执行',
    PROCESSING: '审查中',
    COMPLETED: '已完成',
    FAILED: '失败'
  }
  return texts[status] || status
}

const getRiskLevelType = (level) => {
  const types = {
    critical: 'danger',
    error: 'warning',
    warning: 'info'
  }
  return types[level] || 'info'
}

const getRiskLevelText = (level) => {
  const texts = {
    critical: '严重',
    error: '错误',
    warning: '警告'
  }
  return texts[level] || level
}

const viewReport = (taskId) => {
  router.push(`/report/${taskId}`)
}

const viewDetail = async (row) => {
  try {
    const res = await taskApi.get(row.id)
    taskDetail.value = res.data
    showDetailDialog.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

const loadTasks = async () => {
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (filterRiskLevel.value) params.riskLevel = filterRiskLevel.value
    
    const res = await taskApi.list(params)
    tableData.value = res.data || []
  } catch (error) {
    console.error('加载任务失败:', error)
  }
}

const handleCreate = async () => {
  if (!form.designTaskId) {
    ElMessage.warning('请输入设计任务ID')
    return
  }
  if (!form.taskName) {
    ElMessage.warning('请输入任务名称')
    return
  }
  try {
    await taskApi.create(form)
    ElMessage.success('创建成功，审查正在进行中')
    showCreateDialog.value = false
    form.designTaskId = ''
    form.taskName = ''
    loadTasks()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const handleRecheck = async (row) => {
  try {
    await ElMessageBox.confirm('确定要重新复核此任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await taskApi.recheck(row.id)
    ElMessage.success('重新复核已启动')
    showDetailDialog.value = false
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重新复核失败')
    }
  }
}

// S3 → S4 下游转发：将当前审查任务提交到 S4 生成施工指令(BOM)
const handleForwardToS4 = async (row) => {
  try {
    const res = await taskApi.forwardToS4(row.id)
    const data = res.data
    ElMessage.success('已提交 S4，施工指令(BOM)生成中')
    try {
      await ElMessageBox.confirm(
        `S4 任务已创建（taskId: ${data.s4TaskId}）。是否打开 S4 施工指令页面查看？`,
        '已提交 S4',
        { confirmButtonText: '打开 S4', cancelButtonText: '稍后', type: 'success' }
      )
      window.open(data.s4DetailUrl, '_blank')
    } catch (e) {
      // 用户选择「稍后」—— 不阻断
    }
    showDetailDialog.value = false
  } catch (error) {
    const msg = error?.response?.data?.message || error?.message || '未知错误'
    ElMessage.error('提交 S4 失败：' + msg)
  }
}

onMounted(() => {
  loadTasks()
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

.card-actions {
  display: flex;
  align-items: center;
}

.page-content {
  padding-top: 18px;
}

/* 风险统计徽标 */
.risk-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.risk-item {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 600;
}

.risk-item.critical {
  background-color: #fef2f2;
  color: #dc2626;
}

.risk-item.error {
  background-color: #fff7e8;
  color: #d97706;
}

.risk-item.warning {
  background-color: #eef5ff;
  color: #2563eb;
}

.risk-item.none {
  background-color: #f0fdf4;
  color: #16a34a;
}

/* 操作按钮容器：避免按钮紧贴 */
.action-btns {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

/* 详情弹窗内的统计网格 */
.detail-content {
  padding: 4px 0 10px;
}

.statistics-section {
  margin-top: 18px;
}

.statistics-section h4 {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: var(--brand-text);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  background: linear-gradient(180deg, #ffffff, #f5f8fc);
  padding: 14px 12px;
  border-radius: 10px;
  text-align: center;
  border: 1px solid var(--brand-border);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(16, 42, 82, 0.1);
}

.stat-item.critical {
  background: linear-gradient(180deg, #fff, #fef2f2);
  border-color: #fbd5d5;
}

.stat-item.error {
  background: linear-gradient(180deg, #fff, #fff7e8);
  border-color: #fbe6c4;
}

.stat-item.warning {
  background: linear-gradient(180deg, #fff, #eef5ff);
  border-color: #cfe0ff;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--brand-text-soft);
  margin-bottom: 6px;
}

.stat-value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: var(--brand-text);
}

.results-section {
  margin-top: 18px;
}

.results-section h4 {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: var(--brand-text);
}

.empty-results {
  margin-top: 18px;
  text-align: center;
  color: #999;
  padding: 24px;
  background: #fafcfe;
  border-radius: 10px;
  border: 1px dashed var(--brand-border);
}
</style>
