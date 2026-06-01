﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <div class="page-container">
    <!-- 顶部标题区 -->
    <div class="header-section">
      <div class="title-box">
        <div class="title-icon">✅</div>
        <div class="title-text">
          <h2>数智化交付 - 验收管理</h2>
          <p>Acceptance Management</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button class="tech-btn tech-btn-primary" @click="addTask">
          <span class="btn-icon">+</span>
          新增验收任务
        </el-button>
      </div>
    </div>

    <!-- 统计卡片区 -->
    <div class="stats-section">
      <div class="stat-card">
        <div class="stat-icon stat-icon-green">✅</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.total }}</div>
          <div class="stat-label">任务总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-orange">⏳</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.pending }}</div>
          <div class="stat-label">待验收</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-blue">🔄</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.processing }}</div>
          <div class="stat-label">验收中</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-purple">✅</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.passed }}</div>
          <div class="stat-label">已通过</div>
        </div>
      </div>
    </div>

    <!-- 搜索和筛选区 -->
    <el-card class="search-card" shadow="hover">
      <div class="search-wrapper">
        <div class="search-form">
          <el-input 
            v-model="searchForm.taskName" 
            placeholder="请输入任务名称" 
            class="search-input" 
            clearable
            @clear="clearSearch"
          >
            <template #prefix>🔍</template>
          </el-input>
          <el-select 
            v-model="searchForm.status" 
            placeholder="请选择状态" 
            class="search-input" 
            clearable
            @clear="clearSearch"
          >
            <el-option :label="全部" :value="null" />
            <el-option label="待验收" :value="0" />
            <el-option label="验收中" :value="1" />
            <el-option label="已通过" :value="2" />
            <el-option label="未通过" :value="3" />
          </el-select>
          <el-input 
            v-model="searchForm.taskType" 
            placeholder="请输入任务类型" 
            class="search-input" 
            clearable
            @clear="clearSearch"
          />
        </div>
        <el-button class="tech-btn tech-btn-search" @click="search">查询</el-button>
        <el-button 
          class="tech-btn tech-btn-show-all" 
          @click="reset" 
          :disabled="!hasSearchCondition"
        >
          显示全部
        </el-button>
        <el-button class="tech-btn tech-btn-reset" @click="reset">重置</el-button>
      </div>
      <div v-if="shouldShowSearchTip" class="search-tip">
        🔍 正在筛选：{{ searchConditionText }} | 共 {{ pagination.total }} 条匹配结果
      </div>
    </el-card>

    <!-- 数据表格区 -->
    <el-card class="data-card" shadow="hover">
      <div class="table-header">
        <div class="table-actions">
          <el-button 
            class="tech-btn tech-btn-danger" 
            @click="batchDelete" 
            :disabled="selectedIds.length === 0"
          >
            🗑️ 批量删除
          </el-button>
          <el-button 
            class="tech-btn tech-btn-primary" 
            @click="exportData"
          >
            📥 导出数据
          </el-button>
        </div>
        <div class="table-info">
          已选择 <span class="selected-count">{{ selectedIds.length }}</span> 条记录
        </div>
      </div>
      <el-table 
        :data="tableData" 
        border 
        stripe 
        class="tech-table" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="60" align="center" />
        <el-table-column type="index" label="序号" width="80" align="center" />
        <el-table-column prop="taskName" label="任务名称" min-width="180" />
        <el-table-column prop="taskType" label="任务类型" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag class="tech-tag" :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="problemCount" label="问题数量" width="100" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="320" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-primary" @click="viewTask(scope.row)">详情</el-button>
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-info" @click="editTask(scope.row)">编辑</el-button>
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-warning" @click="updateTaskStatus(scope.row)">改状态</el-button>
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-danger" @click="deleteTask(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.pageNum"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, prev, pager, next, sizes, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="700px" class="tech-dialog">
      <el-form :model="formData" label-width="120px" class="tech-form">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="项目ID" prop="projectId">
              <el-input v-model.number="formData.projectId" placeholder="请输入项目ID" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="任务名称" prop="taskName">
              <el-input v-model="formData.taskName" placeholder="请输入任务名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="任务类型" prop="taskType">
              <el-input v-model="formData.taskType" placeholder="请输入任务类型" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="formData.status" placeholder="请选择状态" style="width: 100%">
                <el-option label="待验收" :value="0" />
                <el-option label="验收中" :value="1" />
                <el-option label="已通过" :value="2" />
                <el-option label="未通过" :value="3" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="验收标准" prop="acceptanceStandard">
              <el-input type="textarea" v-model="formData.acceptanceStandard" :rows="4" placeholder="请输入验收标准" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="结果描述" prop="resultDescription">
              <el-input type="textarea" v-model="formData.resultDescription" :rows="3" placeholder="请输入结果描述（验收完成后填写）" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button class="tech-btn tech-btn-cancel" @click="closeDialog">取消</el-button>
        <el-button class="tech-btn tech-btn-confirm" @click="saveTask">确定</el-button>
      </template>
    </el-dialog>

    <!-- 验收任务详情对话框 -->
    <el-dialog title="验收任务详情" v-model="detailVisible" width="800px" class="tech-dialog">
      <div class="detail-content" v-if="detailData">
        <div class="detail-header">
          <h3 class="detail-title">{{ detailData.taskName }}</h3>
          <div class="detail-tags">
            <el-tag class="tech-tag" :type="getStatusType(detailData.status)">{{ getStatusLabel(detailData.status) }}</el-tag>
          </div>
        </div>
        <div class="detail-body">
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">任务类型</span>
              <span class="detail-value">{{ detailData.taskType || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">问题数量</span>
              <span class="detail-value">{{ detailData.problemCount || 0 }} 个</span>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">项目ID</span>
              <span class="detail-value">{{ detailData.projectId || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">创建时间</span>
              <span class="detail-value">{{ detailData.createTime }}</span>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-item full-width">
              <span class="detail-label">验收标准</span>
              <div class="detail-value text-area">{{ detailData.acceptanceStandard || '-' }}</div>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-item full-width">
              <span class="detail-label">结果描述</span>
              <div class="detail-value text-area">{{ detailData.resultDescription || '-' }}</div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button class="tech-btn tech-btn-cancel" @click="detailVisible = false">关闭</el-button>
        <el-button class="tech-btn tech-btn-confirm" @click="editFromDetail">编辑任务</el-button>
      </template>
    </el-dialog>

    <!-- 修改状态对话框 -->
    <el-dialog title="修改验收状态" v-model="statusDialogVisible" width="500px" class="tech-dialog">
      <el-form :model="statusForm" label-width="100px" class="tech-form">
        <el-form-item label="当前状态">
          <el-tag class="tech-tag" :type="getStatusType(statusForm.status)">{{ getStatusLabel(statusForm.status) }}</el-tag>
        </el-form-item>
        <el-form-item label="目标状态">
          <el-select v-model="statusForm.newStatus" placeholder="请选择新状态" style="width: 100%">
            <el-option label="待验收" :value="0" />
            <el-option label="验收中" :value="1" />
            <el-option label="已通过" :value="2" />
            <el-option label="未通过" :value="3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button class="tech-btn tech-btn-cancel" @click="statusDialogVisible = false">取消</el-button>
        <el-button class="tech-btn tech-btn-confirm" @click="saveStatus">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const searchForm = reactive({
  taskName: '',
  status: null,
  taskType: ''
})

const hasSearched = ref(false)

const hasSearchCondition = computed(() => {
  return searchForm.taskName || searchForm.status !== null || searchForm.taskType
})

const shouldShowSearchTip = computed(() => {
  return hasSearched.value && hasSearchCondition.value && tableData.value.length > 0
})

const searchConditionText = computed(() => {
  const conditions = []
  if (searchForm.taskName) {
    conditions.push(`任务名称: ${searchForm.taskName}`)
  }
  if (searchForm.status !== null) {
    const statusLabels = { 0: '待验收', 1: '验收中', 2: '已通过', 3: '未通过' }
    conditions.push(`状态: ${statusLabels[searchForm.status]}`)
  }
  if (searchForm.taskType) {
    conditions.push(`任务类型: ${searchForm.taskType}`)
  }
  return conditions.join(', ')
})

const clearSearch = () => {
  if (!hasSearchCondition.value) {
    hasSearched.value = false
    loadData()
  }
}

const tableData = ref([])
const loading = ref(false)
const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const statistics = reactive({
  total: 0,
  pending: 0,
  processing: 0,
  passed: 0
})

const selectedIds = ref([])
const detailVisible = ref(false)
const detailData = reactive({})

const handleSelectionChange = (val) => {
  selectedIds.value = val.map(item => item.id)
}

const calculateStatistics = () => {
  const data = tableData.value
  statistics.total = data.length
  statistics.pending = data.filter(item => item.status === 0).length
  statistics.processing = data.filter(item => item.status === 1).length
  statistics.passed = data.filter(item => item.status === 2).length
}

const dialogVisible = ref(false)
const dialogTitle = ref('新增验收任务')
const formData = reactive({
  id: null,
  projectId: null,
  taskName: '',
  taskType: '',
  status: 0,
  acceptanceStandard: '',
  resultDescription: ''
})

const statusDialogVisible = ref(false)
const statusForm = reactive({
  taskId: null,
  status: 0,
  newStatus: 0
})

const search = () => {
  pagination.pageNum = 1
  hasSearched.value = true
  loadData()
}

const reset = () => {
  searchForm.taskName = ''
  searchForm.status = null
  searchForm.taskType = ''
  hasSearched.value = false
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await request.get('/m04/acceptance/task', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        taskName: searchForm.taskName,
        status: searchForm.status,
        taskType: searchForm.taskType
      }
    })
    tableData.value = res.data?.records || []
    pagination.total = res.data?.total || res.data?.records?.length || 0
    calculateStatistics()
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const viewTask = (row) => {
  Object.assign(detailData, row)
  detailVisible.value = true
}

const editFromDetail = () => {
  detailVisible.value = false
  editTask(detailData)
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 个验收任务吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete('/m04/acceptance/task/batch', {
      data: selectedIds.value
    })
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

const exportData = () => {
  const data = tableData.value
  if (data.length === 0) {
    ElMessage.warning('没有数据可导出')
    return
  }
  
  const headers = ['任务名称', '任务类型', '状态', '问题数量', '创建时间']
  const rows = data.map(item => [
    item.taskName,
    item.taskType,
    getStatusLabel(item.status),
    item.problemCount || 0,
    item.createTime
  ])
  
  const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `验收任务列表_${new Date().toISOString().split('T')[0]}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('导出成功')
}

const handlePageChange = (page) => {
  pagination.pageNum = page
  loadData()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.pageNum = 1
  loadData()
}

const addTask = () => {
  dialogTitle.value = '新增验收任务'
  formData.id = null
  formData.projectId = null
  formData.taskName = ''
  formData.taskType = ''
  formData.status = 0
  formData.acceptanceStandard = ''
  formData.resultDescription = ''
  dialogVisible.value = true
}

const editTask = (row) => {
  dialogTitle.value = '编辑验收任务'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const updateTaskStatus = (row) => {
  statusForm.taskId = row.id
  statusForm.status = row.status
  statusForm.newStatus = row.status
  statusDialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
}

const saveTask = async () => {
  try {
    if (formData.id) {
      await request.put(`/m04/acceptance/task/${formData.id}`, formData)
      ElMessage.success('编辑成功')
    } else {
      await request.post('/m04/acceptance/task', formData)
      ElMessage.success('新增成功')
    }
    closeDialog()
    loadData()
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

const saveStatus = async () => {
  try {
    await request.put(`/m04/acceptance/task/${statusForm.taskId}/status`, { status: statusForm.newStatus })
    statusDialogVisible.value = false
    ElMessage.success('更新状态成功')
    loadData()
  } catch (error) {
    console.error('更新状态失败:', error)
    ElMessage.error('更新状态失败')
  }
}

const deleteTask = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该验收任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/m04/acceptance/task/${id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const getStatusType = (status) => {
  const types = { 0: 'warning', 1: 'primary', 2: 'success', 3: 'danger' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { 0: '待验收', 1: '验收中', 2: '已通过', 3: '未通过' }
  return labels[status] || status
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  min-height: 100vh;
}

/* 统计卡片区 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(145deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.4);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon-green {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.4));
}

.stat-icon-orange {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.4));
}

.stat-icon-blue {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.4));
}

.stat-icon-purple {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(139, 92, 246, 0.4));
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(90deg, #10b981, #34d399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-label {
  font-size: 14px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 顶部标题区 */
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.title-box {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-icon {
  font-size: 48px;
  filter: drop-shadow(0 0 10px rgba(16, 185, 129, 0.5));
}

.title-text h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(90deg, #10b981, #34d399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-text p {
  margin: 4px 0 0;
  font-size: 14px;
  color: #94a3b8;
  letter-spacing: 2px;
}

/* 科技感按钮 */
.tech-btn {
  position: relative;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.tech-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.tech-btn:hover::before {
  left: 100%;
}

.tech-btn-primary {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

.tech-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.6);
}

.tech-btn-search {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

.tech-btn-search:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
}

.tech-btn-reset {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  color: white;
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
}

.tech-btn-reset:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.5);
}

.tech-btn-mini {
  padding: 6px 14px;
  font-size: 13px;
}

.tech-btn-info {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
}

.tech-btn-warning {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  color: white;
}

.tech-btn-danger {
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: white;
}

.tech-btn-cancel {
  background: linear-gradient(135deg, #64748b, #94a3b8);
  color: white;
}

.tech-btn-confirm {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.btn-icon {
  font-size: 16px;
  font-weight: bold;
}

/* 卡片样式 */
.search-card,
.data-card {
  background: linear-gradient(145deg, #1e293b, #0f172a);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 12px;
  margin-bottom: 20px;
}

.search-card :deep(.el-card__header),
.data-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(16, 185, 129, 0.2);
  background: rgba(16, 185, 129, 0.05);
}

/* 搜索区 */
.search-wrapper {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-form {
  flex: 1;
  display: flex;
  gap: 12px;
}

.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper),
.search-input :deep(.el-select__wrapper) {
  background: rgba(30, 41, 59);
  border: 1px solid rgba(16, 185, 129, 0.3);
  box-shadow: none;
}

.search-input :deep(.el-input__wrapper:hover),
.search-input :deep(.el-select__wrapper:hover) {
  border-color: rgba(16, 185, 129, 0.6);
}

.search-tip {
  margin-top: 12px;
  padding: 8px 16px;
  background: rgba(139, 92, 246, 0.1);
  border-radius: 6px;
  font-size: 14px;
  color: #a78bfa;
  border: 1px solid rgba(139, 92, 246, 0.2);
}

/* 表格头部操作栏 */
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(16, 185, 129, 0.15);
}

.table-actions {
  display: flex;
  gap: 12px;
}

.table-info {
  font-size: 14px;
  color: #94a3b8;
}

.selected-count {
  color: #10b981;
  font-weight: 600;
  font-size: 16px;
}

/* 科技感表格 */
.tech-table {
  background: transparent !important;
  --el-table-bg-color: transparent !important;
  --el-table-row-hover-bg-color: rgba(16, 185, 129, 0.15) !important;
  --el-table-row-bg-color: rgba(30, 41, 59, 0.6) !important;
  --el-table-header-text-color: #10b981 !important;
  --el-table-text-color: #e2e8f0 !important;
  --el-table-border-color: rgba(16, 185, 129, 0.15) !important;
}

.tech-table :deep(.el-table) {
  background: transparent !important;
  border: none !important;
}

.tech-table :deep(.el-table__inner-wrapper) {
  background: rgba(15, 23, 42, 0.8) !important;
  border-radius: 8px;
  overflow: hidden;
}

.tech-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.tech-table :deep(.el-table--border::after),
.tech-table :deep(.el-table--group::after),
.tech-table :deep(.el-table::before) {
  display: none !important;
}

.tech-table :deep(.el-table__header-wrapper) {
  background: rgba(15, 23, 42, 0.95) !important;
  border-radius: 8px 8px 0 0;
}

.tech-table :deep(.el-table__header) {
  background: transparent !important;
}

.tech-table :deep(.el-table__header th) {
  background: rgba(16, 185, 129, 0.12) !important;
  color: #34d399 !important;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid rgba(16, 185, 129, 0.25) !important;
  border-right: 1px solid rgba(16, 185, 129, 0.1) !important;
}

.tech-table :deep(.el-table__header th:last-child) {
  border-right: none !important;
}

.tech-table :deep(.el-table__body) {
  background: rgba(15, 23, 42, 0.7) !important;
}

.tech-table :deep(.el-table__body-wrapper) {
  background: rgba(15, 23, 42, 0.7) !important;
}

.tech-table :deep(.el-table__row) {
  background: rgba(30, 41, 59, 0.5) !important;
}

.tech-table :deep(.el-table__row td) {
  background: transparent !important;
  color: #e2e8f0 !important;
  border-bottom: 1px solid rgba(16, 185, 129, 0.08) !important;
  border-right: 1px solid rgba(16, 185, 129, 0.05) !important;
}

.tech-table :deep(.el-table__row td:last-child) {
  border-right: none !important;
}

.tech-table :deep(.el-table__row--striped) {
  background: rgba(16, 185, 129, 0.05) !important;
}

.tech-table :deep(.el-table__row--striped td) {
  background: rgba(16, 185, 129, 0.05) !important;
}

.tech-table :deep(.el-table__body tr) {
  transition: all 0.3s ease;
}

.tech-table :deep(.el-table__body tr:hover) {
  background: rgba(16, 185, 129, 0.15) !important;
}

.tech-table :deep(.el-table__body tr:hover td) {
  background: rgba(16, 185, 129, 0.15) !important;
}

.tech-table :deep(.el-table--border td),
.tech-table :deep(.el-table--border th),
.tech-table :deep(.el-table__body-wrapper) {
  border-color: rgba(16, 185, 129, 0.1) !important;
}

/* 详情弹窗样式 */
.detail-content {
  padding: 8px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(16, 185, 129, 0.2);
}

.detail-title {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(90deg, #10b981, #34d399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.detail-tags {
  display: flex;
  gap: 8px;
}

.detail-body {
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  padding: 16px;
}

.detail-row {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-item {
  flex: 1;
}

.detail-item.full-width {
  flex: 100%;
}

.detail-label {
  display: block;
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.detail-value {
  font-size: 15px;
  color: #e2e8f0;
  font-weight: 500;
}

.detail-value.text-area {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.progress-wrapper {
  margin-top: 8px;
}

/* 科技感标签 */
.tech-tag {
  border: none;
  font-weight: 500;
}

/* 分页 */
.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.pagination-wrapper :deep(.el-pagination) {
  --el-pagination-button-color: #94a3b8;
  --el-pagination-button-bg-color: #1e293b;
  --el-pagination-button-disabled-bg-color: #0f172a;
  --el-pagination-button-disabled-color: #475569;
  --el-pagination-button-border-color: rgba(16, 185, 129, 0.3);
  --el-pagination-button-hover-bg-color: rgba(16, 185, 129, 0.2);
  --el-pagination-button-hover-color: #10b981;
}

.pagination-wrapper :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

/* 对话框 */
.tech-dialog :deep(.el-dialog) {
  background: linear-gradient(145deg, #1e293b, #0f172a);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 12px;
}

.tech-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(16, 185, 129, 0.2);
}

.tech-dialog :deep(.el-dialog__title) {
  background: linear-gradient(90deg, #10b981, #34d399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 600;
  font-size: 18px;
}

.tech-form :deep(.el-form-item__label) {
  color: #cbd5e1;
}

.tech-form :deep(.el-input__wrapper),
.tech-form :deep(.el-select__wrapper),
.tech-form :deep(.el-textarea__inner) {
  background: rgba(30, 41, 59);
  border: 1px solid rgba(16, 185, 129, 0.3);
  box-shadow: none;
}

.tech-form :deep(.el-input__wrapper:hover),
.tech-form :deep(.el-select__wrapper:hover),
.tech-form :deep(.el-textarea__inner:hover) {
  border-color: rgba(16, 185, 129, 0.6);
}
</style>