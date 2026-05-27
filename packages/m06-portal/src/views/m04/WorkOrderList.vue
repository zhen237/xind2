<template>
  <div class="page-container">
    <!-- 顶部标题区 -->
    <div class="header-section">
      <div class="title-box">
        <div class="title-icon">📋</div>
        <div class="title-text">
          <h2>数智化交付 - 工单管理</h2>
          <p>Work Order Management</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button class="tech-btn tech-btn-primary" @click="addOrder">
          <span class="btn-icon">+</span>
          新增工单
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选区 -->
    <el-card class="search-card" shadow="hover">
      <div class="search-wrapper">
        <div class="search-form">
          <el-input 
            v-model="searchForm.title" 
            placeholder="请输入工单标题" 
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
            <el-option label="待处理" :value="0" />
            <el-option label="处理中" :value="1" />
            <el-option label="已完成" :value="2" />
            <el-option label="已关闭" :value="3" />
          </el-select>
          <el-input 
            v-model="searchForm.type" 
            placeholder="请输入工单类型" 
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
      <el-table :data="tableData" border stripe class="tech-table" v-loading="loading">
        <el-table-column type="index" label="序号" width="80" align="center" />
        <el-table-column prop="orderNo" label="工单编号" width="150" />
        <el-table-column prop="title" label="工单标题" min-width="200" />
        <el-table-column prop="type" label="工单类型" width="120" />
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="scope">
            <el-tag class="tech-tag" :type="getPriorityType(scope.row.priority)">{{ getPriorityLabel(scope.row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag class="tech-tag" :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stationCode" label="站点编码" width="120" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="260" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-info" @click="editOrder(scope.row)">编辑</el-button>
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-warning" @click="updateOrderStatus(scope.row)">改状态</el-button>
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-danger" @click="deleteOrder(scope.row.id)">删除</el-button>
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
            <el-form-item label="工单标题" prop="title">
              <el-input v-model="formData.title" placeholder="请输入工单标题" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工单类型" prop="type">
              <el-input v-model="formData.type" placeholder="请输入工单类型" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-select v-model="formData.priority" placeholder="请选择优先级" style="width: 100%">
                <el-option label="低" :value="1" />
                <el-option label="中" :value="2" />
                <el-option label="高" :value="3" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="站点编码" prop="stationCode">
              <el-input v-model="formData.stationCode" placeholder="请输入站点编码" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="设备编码" prop="deviceCode">
              <el-input v-model="formData.deviceCode" placeholder="请输入设备编码" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="工单描述" prop="description">
              <el-input v-model="formData.description" type="textarea" :rows="4" placeholder="请输入工单描述" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button class="tech-btn tech-btn-cancel" @click="closeDialog">取消</el-button>
        <el-button class="tech-btn tech-btn-confirm" @click="saveOrder">确定</el-button>
      </template>
    </el-dialog>

    <!-- 修改状态对话框 -->
    <el-dialog title="修改工单状态" v-model="statusDialogVisible" width="500px" class="tech-dialog">
      <el-form :model="statusForm" label-width="100px" class="tech-form">
        <el-form-item label="当前状态">
          <el-tag class="tech-tag" :type="getStatusType(statusForm.status)">{{ getStatusLabel(statusForm.status) }}</el-tag>
        </el-form-item>
        <el-form-item label="目标状态">
          <el-select v-model="statusForm.newStatus" placeholder="请选择新状态" style="width: 100%">
            <el-option label="待处理" :value="0" />
            <el-option label="处理中" :value="1" />
            <el-option label="已完成" :value="2" />
            <el-option label="已关闭" :value="3" />
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
  title: '',
  status: null,
  type: ''
})

const hasSearched = ref(false)

const hasSearchCondition = computed(() => {
  return searchForm.title || searchForm.status !== null || searchForm.type
})

const shouldShowSearchTip = computed(() => {
  return hasSearched.value && hasSearchCondition.value && tableData.value.length > 0
})

const searchConditionText = computed(() => {
  const conditions = []
  if (searchForm.title) {
    conditions.push(`工单标题: ${searchForm.title}`)
  }
  if (searchForm.status !== null) {
    const statusLabels = { 0: '待处理', 1: '处理中', 2: '已完成', 3: '已关闭' }
    conditions.push(`状态: ${statusLabels[searchForm.status]}`)
  }
  if (searchForm.type) {
    conditions.push(`工单类型: ${searchForm.type}`)
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

const dialogVisible = ref(false)
const dialogTitle = ref('新增工单')
const formData = reactive({
  id: null,
  orderNo: '',
  title: '',
  type: '',
  priority: 1,
  status: 0,
  stationCode: '',
  deviceCode: '',
  description: ''
})

const statusDialogVisible = ref(false)
const statusForm = reactive({
  orderId: null,
  status: 0,
  newStatus: 0
})

const search = () => {
  pagination.pageNum = 1
  hasSearched.value = true
  loadData()
}

const reset = () => {
  searchForm.title = ''
  searchForm.status = null
  searchForm.type = ''
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await request.get('/m04/work-order', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        title: searchForm.title,
        status: searchForm.status,
        type: searchForm.type
      }
    })
    tableData.value = res.data?.records || []
    pagination.total = res.data?.total || res.data?.records?.length || 0
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
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

const addOrder = () => {
  dialogTitle.value = '新增工单'
  formData.id = null
  formData.orderNo = ''
  formData.title = ''
  formData.type = ''
  formData.priority = 1
  formData.status = 0
  formData.stationCode = ''
  formData.deviceCode = ''
  formData.description = ''
  dialogVisible.value = true
}

const editOrder = (row) => {
  dialogTitle.value = '编辑工单'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const updateOrderStatus = (row) => {
  statusForm.orderId = row.id
  statusForm.status = row.status
  statusForm.newStatus = row.status
  statusDialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
}

const saveOrder = async () => {
  try {
    if (formData.id) {
      await request.put(`/m04/work-order/${formData.id}`, formData)
      ElMessage.success('编辑成功')
    } else {
      await request.post('/m04/work-order', formData)
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
    await request.put(`/m04/work-order/${statusForm.orderId}/status`, { status: statusForm.newStatus })
    statusDialogVisible.value = false
    ElMessage.success('更新状态成功')
    loadData()
  } catch (error) {
    console.error('更新状态失败:', error)
    ElMessage.error('更新状态失败')
  }
}

const deleteOrder = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该工单吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/m04/work-order/${id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const getPriorityType = (priority) => {
  const types = { 1: 'success', 2: 'warning', 3: 'danger' }
  return types[priority] || 'info'
}

const getPriorityLabel = (priority) => {
  const labels = { 1: '低', 2: '中', 3: '高' }
  return labels[priority] || priority
}

const getStatusType = (status) => {
  const types = { 0: 'warning', 1: 'primary', 2: 'success', 3: 'info' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { 0: '待处理', 1: '处理中', 2: '已完成', 3: '已关闭' }
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

/* 科技感表格 */
.tech-table {
  background: transparent;
}

.tech-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.tech-table :deep(.el-table--border::after),
.tech-table :deep(.el-table--group::after) {
  display: none;
}

.tech-table :deep(.el-table__header-wrapper) {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1));
}

.tech-table :deep(.el-table__header th) {
  background: transparent !important;
  color: #10b981;
  font-weight: 600;
  font-size: 14px;
}

.tech-table :deep(.el-table__body tr) {
  transition: all 0.3s ease;
}

.tech-table :deep(.el-table__body tr:hover td) {
  background: rgba(16, 185, 129, 0.1);
}

.tech-table :deep(.el-table__body tr:hover) {
  transform: scale(1.01);
  box-shadow: 0 4px 20px rgba(16, 185, 129, 0.2);
}

.tech-table :deep(.el-table--border td),
.tech-table :deep(.el-table--border th),
.tech-table :deep(.el-table__body-wrapper) {
  border-color: rgba(16, 185, 129, 0.2);
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
