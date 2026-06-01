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

    <!-- 统计卡片区 -->
    <div class="stats-section">
      <div class="stat-card">
        <div class="stat-icon stat-icon-blue">📊</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.total }}</div>
          <div class="stat-label">项目总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-green">🔧</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.inProgress }}</div>
          <div class="stat-label">在建项目</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-purple">✅</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.completed }}</div>
          <div class="stat-label">竣工项目</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-orange">📈</div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.avgProgress }}%</div>
          <div class="stat-label">平均进度</div>
        </div>
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
          <el-select 
            v-model="searchForm.currentPhase" 
            placeholder="请选择阶段" 
            class="search-select" 
            clearable
            @clear="clearSearch"
          >
            <el-option label="规划" value="PLANNING" />
            <el-option label="设计" value="DESIGN" />
            <el-option label="施工" value="CONSTRUCTION" />
            <el-option label="验收" value="ACCEPTANCE" />
          </el-select>
          <el-select 
            v-model="searchForm.status" 
            placeholder="请选择状态" 
            class="search-select" 
            clearable
            @clear="clearSearch"
          >
            <el-option label="在建" :value="0" />
            <el-option label="竣工" :value="1" />
            <el-option label="验收" :value="2" />
          </el-select>
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
          <el-button 
            class="tech-btn tech-btn-show-all" 
            @click="archiveProjects"
            :disabled="selectedIds.length === 0"
          >
            📦 归档选中
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
        <el-table-column label="操作" width="280" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" class="tech-btn tech-btn-mini tech-btn-primary" @click="viewProject(scope.row)">详情</el-button>
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

    <!-- 项目详情对话框 -->
    <el-dialog title="项目详情" v-model="detailVisible" width="800px" class="tech-dialog">
      <div class="detail-content" v-if="detailData">
        <div class="detail-header">
          <h3 class="detail-title">{{ detailData.projectName }}</h3>
          <div class="detail-tags">
            <el-tag class="tech-tag" :type="getPhaseType(detailData.currentPhase)">{{ getPhaseLabel(detailData.currentPhase) }}</el-tag>
            <el-tag class="tech-tag" :type="getStatusType(detailData.status)">{{ getStatusLabel(detailData.status) }}</el-tag>
          </div>
        </div>
        <div class="detail-body">
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">项目编号</span>
              <span class="detail-value">{{ detailData.projectCode }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">区域编码</span>
              <span class="detail-value">{{ detailData.regionCode }}</span>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">施工单位</span>
              <span class="detail-value">{{ detailData.constructionUnit || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">设计单位</span>
              <span class="detail-value">{{ detailData.designUnit || '-' }}</span>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">监理单位</span>
              <span class="detail-value">{{ detailData.supervisionUnit || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">建设单位</span>
              <span class="detail-value">{{ detailData.ownerUnit || '-' }}</span>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-item full-width">
              <span class="detail-label">项目进度</span>
              <div class="progress-wrapper">
                <el-progress :percentage="detailData.totalProgress || 0" :stroke-width="16" :show-text="true" />
              </div>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">创建时间</span>
              <span class="detail-value">{{ detailData.createTime }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">更新时间</span>
              <span class="detail-value">{{ detailData.updateTime || '-' }}</span>
            </div>
          </div>
        </div>
        
        <!-- 附件管理 -->
        <div class="attachment-section">
          <div class="attachment-header">
            <h4>📎 项目附件</h4>
            <el-button size="small" class="tech-btn tech-btn-primary" @click="uploadFile">
              + 上传文件
            </el-button>
          </div>
          <div v-if="attachments.length === 0" class="empty-attachments">
            <div class="empty-icon">📁</div>
            <p>暂无附件，点击上方按钮上传</p>
          </div>
          <div v-else class="attachment-list">
            <div 
              v-for="file in attachments" 
              :key="file.id" 
              class="attachment-item"
            >
              <div class="file-icon">{{ getFileIcon(file.fileName) }}</div>
              <div class="file-info">
                <div class="file-name">{{ file.fileName }}</div>
                <div class="file-meta">{{ file.fileSize }} | {{ file.uploadTime }}</div>
              </div>
              <div class="file-actions">
                <el-button size="small" class="tech-btn tech-btn-mini tech-btn-info" @click="downloadFile(file)">
                  下载
                </el-button>
                <el-button size="small" class="tech-btn tech-btn-mini tech-btn-danger" @click="deleteFile(file.id)">
                  删除
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 文件上传对话框 -->
      <el-dialog title="上传附件" v-model="uploadVisible" width="500px" class="tech-dialog">
        <el-upload
          class="upload-demo"
          :action="`/m04/project/${detailData.id}/upload`"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          multiple
        >
          <el-button size="small" class="tech-btn tech-btn-primary">点击选择文件</el-button>
        </el-upload>
        <template #footer>
          <el-button class="tech-btn tech-btn-cancel" @click="uploadVisible = false">关闭</el-button>
        </template>
      </el-dialog>
      <template #footer>
        <el-button class="tech-btn tech-btn-cancel" @click="detailVisible = false">关闭</el-button>
        <el-button class="tech-btn tech-btn-confirm" @click="editFromDetail">编辑项目</el-button>
      </template>
    </el-dialog>

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
  regionCode: '',
  currentPhase: '',
  status: ''
})

const hasSearched = ref(false)

const hasSearchCondition = computed(() => {
  return searchForm.projectName || searchForm.regionCode || searchForm.currentPhase || searchForm.status !== ''
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
  if (searchForm.currentPhase) {
    conditions.push(`阶段: ${getPhaseLabel(searchForm.currentPhase)}`)
  }
  if (searchForm.status !== '') {
    conditions.push(`状态: ${getStatusLabel(searchForm.status)}`)
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
  inProgress: 0,
  completed: 0,
  avgProgress: 0
})

const selectedIds = ref([])
const attachments = ref([])
const uploadVisible = ref(false)

const handleSelectionChange = (val) => {
  selectedIds.value = val.map(item => item.id)
}

const loadAttachments = async (projectId) => {
  try {
    const res = await request.get(`/m04/project/${projectId}/files`)
    attachments.value = res.data || []
  } catch (error) {
    console.error('加载附件失败:', error)
    attachments.value = []
  }
}

const viewProject = (row) => {
  Object.assign(detailData, row)
  loadAttachments(row.id)
  detailVisible.value = true
}

const uploadFile = () => {
  uploadVisible.value = true
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  uploadVisible.value = false
  loadAttachments(detailData.id)
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const beforeUpload = (file) => {
  const fileSize = file.size / 1024 / 1024
  if (fileSize > 50) {
    ElMessage.error('文件大小不能超过50MB')
    return false
  }
  return true
}

const downloadFile = (file) => {
  window.open(`/m04/project/${detailData.id}/download/${file.id}`, '_blank')
}

const deleteFile = async (fileId) => {
  try {
    await ElMessageBox.confirm('确定要删除该文件吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/m04/project/${detailData.id}/file/${fileId}`)
    ElMessage.success('删除成功')
    loadAttachments(detailData.id)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文件失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const getFileIcon = (fileName) => {
  const ext = fileName.split('.').pop().toLowerCase()
  const icons = {
    'pdf': '📕',
    'doc': '📘',
    'docx': '📘',
    'xls': '📗',
    'xlsx': '📗',
    'ppt': '📙',
    'pptx': '📙',
    'txt': '📝',
    'jpg': '🖼️',
    'jpeg': '🖼️',
    'png': '🖼️',
    'zip': '📦',
    'rar': '📦'
  }
  return icons[ext] || '📄'
}

const calculateStatistics = () => {
  const data = tableData.value
  statistics.total = data.length
  statistics.inProgress = data.filter(item => item.status === 0).length
  statistics.completed = data.filter(item => item.status === 1).length
  if (data.length > 0) {
    statistics.avgProgress = Math.round(data.reduce((sum, item) => sum + (item.totalProgress || 0), 0) / data.length)
  } else {
    statistics.avgProgress = 0
  }
}

const dialogVisible = ref(false)
const dialogTitle = ref('新增项目')
const detailVisible = ref(false)
const detailData = reactive({})
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
  searchForm.currentPhase = ''
  searchForm.status = ''
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
        regionCode: searchForm.regionCode,
        currentPhase: searchForm.currentPhase,
        status: searchForm.status
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

const handlePageChange = (page) => {
  pagination.pageNum = page
  loadData()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.pageNum = 1
  loadData()
}

const editFromDetail = () => {
  detailVisible.value = false
  editProject(detailData)
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

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 个项目吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete('/m04/project/batch', {
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
  
  const headers = ['项目名称', '项目编号', '区域编码', '当前阶段', '总进度', '状态', '创建时间']
  const rows = data.map(item => [
    item.projectName,
    item.projectCode,
    item.regionCode,
    getPhaseLabel(item.currentPhase),
    `${item.totalProgress}%`,
    getStatusLabel(item.status),
    item.createTime
  ])
  
  const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `项目列表_${new Date().toISOString().split('T')[0]}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('导出成功')
}

const archiveProjects = async () => {
  try {
    await ElMessageBox.confirm(`确定要归档选中的 ${selectedIds.value.length} 个项目吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })
    await request.put('/m04/project/archive', selectedIds.value)
    ElMessage.success('归档成功')
    selectedIds.value = []
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('归档失败:', error)
      ElMessage.error('归档失败')
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
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
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

.stat-icon-blue {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.4));
}

.stat-icon-green {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.4));
}

.stat-icon-purple {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(139, 92, 246, 0.4));
}

.stat-icon-orange {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.4));
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
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

.search-select {
  width: 150px;
}

.search-select :deep(.el-select__wrapper) {
  background: rgba(30, 41, 59);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.search-select :deep(.el-select__wrapper:hover) {
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
  background: transparent !important;
  --el-table-bg-color: transparent !important;
  --el-table-row-hover-bg-color: rgba(59, 130, 246, 0.15) !important;
  --el-table-row-bg-color: rgba(30, 41, 59, 0.6) !important;
  --el-table-header-text-color: #60a5fa !important;
  --el-table-text-color: #e2e8f0 !important;
  --el-table-border-color: rgba(59, 130, 246, 0.15) !important;
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
  background: rgba(59, 130, 246, 0.12) !important;
  color: #60a5fa !important;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.25) !important;
  border-right: 1px solid rgba(59, 130, 246, 0.1) !important;
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
  border-bottom: 1px solid rgba(59, 130, 246, 0.08) !important;
  border-right: 1px solid rgba(59, 130, 246, 0.05) !important;
}

.tech-table :deep(.el-table__row td:last-child) {
  border-right: none !important;
}

.tech-table :deep(.el-table__row--striped) {
  background: rgba(59, 130, 246, 0.05) !important;
}

.tech-table :deep(.el-table__row--striped td) {
  background: rgba(59, 130, 246, 0.05) !important;
}

.tech-table :deep(.el-table__body tr) {
  transition: all 0.3s ease;
}

.tech-table :deep(.el-table__body tr:hover) {
  background: rgba(59, 130, 246, 0.15) !important;
}

.tech-table :deep(.el-table__body tr:hover td) {
  background: rgba(59, 130, 246, 0.15) !important;
}

.tech-table :deep(.el-table--border td),
.tech-table :deep(.el-table--border th),
.tech-table :deep(.el-table__body-wrapper) {
  border-color: rgba(59, 130, 246, 0.1) !important;
}

/* 科技感标签 */
.tech-tag {
  border: none;
  font-weight: 500;
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
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.detail-title {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
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

.progress-wrapper {
  margin-top: 8px;
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
  border: 1px solid rgba(59, 130, 246, 0.15);
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
  color: #3b82f6;
  font-weight: 600;
  font-size: 16px;
}

/* 附件管理样式 */
.attachment-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
}

.attachment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.attachment-header h4 {
  margin: 0;
  font-size: 16px;
  color: #e2e8f0;
}

.empty-attachments {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: rgba(15, 23, 42, 0.4);
  border-radius: 8px;
  border: 1px dashed rgba(59, 130, 246, 0.3);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-attachments p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  transition: all 0.3s ease;
}

.attachment-item:hover {
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.15);
}

.file-icon {
  font-size: 32px;
}

.file-info {
  flex: 1;
}

.file-name {
  font-size: 14px;
  color: #e2e8f0;
  font-weight: 500;
}

.file-meta {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.file-actions {
  display: flex;
  gap: 8px;
}

/* 分页 */
.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  padding: 16px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.15);
}

.pagination-wrapper :deep(.el-pagination) {
  --el-pagination-button-color: #94a3b8;
  --el-pagination-button-bg-color: rgba(30, 41, 59, 0.6);
  --el-pagination-button-disabled-bg-color: rgba(15, 23, 42, 0.8);
  --el-pagination-button-disabled-color: #475569;
  --el-pagination-button-border-color: rgba(59, 130, 246, 0.25);
  --el-pagination-button-hover-bg-color: rgba(59, 130, 246, 0.2);
  --el-pagination-button-hover-color: #60a5fa;
  --el-pagination-input-bg-color: rgba(30, 41, 59, 0.8);
  --el-pagination-input-border-color: rgba(59, 130, 246, 0.3);
  --el-pagination-input-color: #e2e8f0;
}

.pagination-wrapper :deep(.el-pager li) {
  border-radius: 6px;
  margin: 0 2px;
}

.pagination-wrapper :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
}

.pagination-wrapper :deep(.el-select__wrapper) {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.25);
}

.pagination-wrapper :deep(.el-select__wrapper:hover) {
  border-color: rgba(59, 130, 246, 0.5);
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
