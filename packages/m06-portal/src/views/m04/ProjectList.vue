<template>
  <div class="page-container">
    <!-- 顶部标题区 -->
    <div class="header-section">
      <div class="title-box">
        <div class="title-icon">📁</div>
        <div class="title-text">
          <h2>数智化交付 - 文档管理</h2>
          <p>Digital Delivery Management</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button class="tech-btn tech-btn-primary" @click="addProject">
          <span class="btn-icon">+</span>
          新增项目
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选区 -->
    <el-card class="search-card" shadow="hover">
      <div class="search-wrapper">
        <div class="search-form">
          <el-input 
            v-model="searchForm.projectName" 
            placeholder="请输入项目名称" 
            class="search-input" 
            clearable
            @clear="clearSearch"
          >
            <template #prefix>🔍</template>
          </el-input>
          <el-input 
            v-model="searchForm.regionCode" 
            placeholder="请输入区域编码" 
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
        <el-table-column prop="projectName" label="项目名称" min-width="180" />
        <el-table-column prop="projectCode" label="项目编号" width="150" />
        <el-table-column prop="regionCode" label="区域编码" width="120" />
        <el-table-column prop="currentPhase" label="当前阶段" width="120">
          <template #default="scope">
            <el-tag class="tech-tag" :type="getPhaseType(scope.row.currentPhase)">{{ getPhaseLabel(scope.row.currentPhase) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalProgress" label="总进度" width="150">
          <template #default="scope">
            <el-progress :percentage="scope.row.totalProgress" :stroke-width="12" :show-text="true" />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag class="tech-tag" :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-info" @click="editProject(scope.row)">编辑</el-button>
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-danger" @click="deleteProject(scope.row.id)">删除</el-button>
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
            <el-form-item label="项目名称" prop="projectName">
              <el-input v-model="formData.projectName" placeholder="请输入项目名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="项目编号" prop="projectCode">
              <el-input v-model="formData.projectCode" placeholder="请输入项目编号" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="区域编码" prop="regionCode">
              <el-input v-model="formData.regionCode" placeholder="请输入区域编码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="当前阶段" prop="currentPhase">
              <el-select v-model="formData.currentPhase" placeholder="请选择阶段" style="width: 100%">
                <el-option label="规划" value="PLANNING" />
                <el-option label="设计" value="DESIGN" />
                <el-option label="施工" value="CONSTRUCTION" />
                <el-option label="验收" value="ACCEPTANCE" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="施工单位" prop="constructionUnit">
              <el-input v-model="formData.constructionUnit" placeholder="请输入施工单位" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设计单位" prop="designUnit">
              <el-input v-model="formData.designUnit" placeholder="请输入设计单位" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="监理单位" prop="supervisionUnit">
              <el-input v-model="formData.supervisionUnit" placeholder="请输入监理单位" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="建设单位" prop="ownerUnit">
              <el-input v-model="formData.ownerUnit" placeholder="请输入建设单位" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button class="tech-btn tech-btn-cancel" @click="closeDialog">取消</el-button>
        <el-button class="tech-btn tech-btn-confirm" @click="saveProject">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const searchForm = reactive({
  projectName: '',
  regionCode: ''
})

const hasSearched = ref(false)

const hasSearchCondition = computed(() => {
  return searchForm.projectName || searchForm.regionCode
})

const shouldShowSearchTip = computed(() => {
  return hasSearched.value && hasSearchCondition.value && tableData.value.length > 0
})

const searchConditionText = computed(() => {
  const conditions = []
  if (searchForm.projectName) {
    conditions.push(`项目名称: ${searchForm.projectName}`)
  }
  if (searchForm.regionCode) {
    conditions.push(`区域编码: ${searchForm.regionCode}`)
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
const dialogTitle = ref('新增项目')
const formData = reactive({
  id: null,
  projectName: '',
  projectCode: '',
  regionCode: '',
  currentPhase: 'PLANNING',
  constructionUnit: '',
  designUnit: '',
  supervisionUnit: '',
  ownerUnit: ''
})

const search = () => {
  pagination.pageNum = 1
  hasSearched.value = true
  loadData()
}

const reset = () => {
  searchForm.projectName = ''
  searchForm.regionCode = ''
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await request.get('/m04/project', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        projectName: searchForm.projectName,
        regionCode: searchForm.regionCode
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

const addProject = () => {
  dialogTitle.value = '新增项目'
  formData.id = null
  formData.projectName = ''
  formData.projectCode = ''
  formData.regionCode = ''
  formData.currentPhase = 'PLANNING'
  formData.constructionUnit = ''
  formData.designUnit = ''
  formData.supervisionUnit = ''
  formData.ownerUnit = ''
  dialogVisible.value = true
}

const editProject = (row) => {
  dialogTitle.value = '编辑项目'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
}

const saveProject = async () => {
  try {
    if (formData.id) {
      await request.put(`/m04/project/${formData.id}`, formData)
      ElMessage.success('编辑成功')
    } else {
      await request.post('/m04/project', formData)
      ElMessage.success('新增成功')
    }
    closeDialog()
    loadData()
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

const deleteProject = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该项目吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/m04/project/${id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const getPhaseType = (phase) => {
  const types = { PLANNING: 'info', DESIGN: 'primary', CONSTRUCTION: 'warning', ACCEPTANCE: 'success' }
  return types[phase] || 'info'
}

const getPhaseLabel = (phase) => {
  const labels = { PLANNING: '规划', DESIGN: '设计', CONSTRUCTION: '施工', ACCEPTANCE: '验收' }
  return labels[phase] || phase
}

const getStatusType = (status) => {
  const types = { 0: 'warning', 1: 'success', 2: 'info' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { 0: '在建', 1: '竣工', 2: '验收' }
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
  filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.5));
}

.title-text h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
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
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
}

.tech-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
}

.tech-btn-search {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
}

.tech-btn-search:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
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

.tech-btn-show-all {
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
  color: white;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}

.tech-btn-show-all:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
}

.tech-btn-show-all:disabled {
  background: linear-gradient(135deg, #475569, #64748b);
  color: #94a3b8;
  cursor: not-allowed;
  box-shadow: none;
}

.tech-btn-mini {
  padding: 6px 14px;
  font-size: 13px;
}

.tech-btn-info {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
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
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
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
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  margin-bottom: 20px;
}

.search-card :deep(.el-card__header),
.data-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  background: rgba(59, 130, 246, 0.05);
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

.search-input :deep(.el-input__wrapper) {
  background: rgba(30, 41, 59);
  border: 1px solid rgba(59, 130, 246, 0.3);
  box-shadow: none;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: rgba(59, 130, 246, 0.6);
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
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1));
}

.tech-table :deep(.el-table__header th) {
  background: transparent !important;
  color: #3b82f6;
  font-weight: 600;
  font-size: 14px;
}

.tech-table :deep(.el-table__row:hover td) {
  background: rgba(59, 130, 246, 0.05);
}

.tech-table :deep(.el-table__body tr) {
  transition: all 0.3s ease;
}

.tech-table :deep(.el-table__body tr:hover td) {
  background: rgba(59, 130, 246, 0.1);
}

.tech-table :deep(.el-table__body tr:hover) {
  transform: scale(1.01);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.2);
}

.tech-table :deep(.el-table--border td),
.tech-table :deep(.el-table--border th),
.tech-table :deep(.el-table__body-wrapper) {
  border-color: rgba(59, 130, 246, 0.2);
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
  --el-pagination-button-border-color: rgba(59, 130, 246, 0.3);
  --el-pagination-button-hover-bg-color: rgba(59, 130, 246, 0.2);
  --el-pagination-button-hover-color: #3b82f6;
}

.pagination-wrapper :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
}

/* 对话框 */
.tech-dialog :deep(.el-dialog) {
  background: linear-gradient(145deg, #1e293b, #0f172a);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
}

.tech-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.tech-dialog :deep(.el-dialog__title) {
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 600;
  font-size: 18px;
}

.tech-form :deep(.el-form-item__label) {
  color: #cbd5e1;
}

.tech-form :deep(.el-input__wrapper),
.tech-form :deep(.el-select__wrapper) {
  background: rgba(30, 41, 59);
  border: 1px solid rgba(59, 130, 246, 0.3);
  box-shadow: none;
}

.tech-form :deep(.el-input__wrapper:hover),
.tech-form :deep(.el-select__wrapper:hover) {
  border-color: rgba(59, 130, 246, 0.6);
}
</style>
