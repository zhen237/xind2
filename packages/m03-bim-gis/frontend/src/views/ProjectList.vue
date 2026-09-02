<template>
  <div class="project-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-title">
        <h2>M03 BIM+GIS 三维孪生建模引擎</h2>
        <span class="subtitle">通信基础设施三维数字化设计与可视化</span>
      </div>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">新建项目</el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar panel">
      <el-input
        v-model="filters.projectName"
        placeholder="项目名称"
        clearable
        style="width: 200px"
        @keyup.enter="loadData"
      />
      <el-input
        v-model="filters.regionCode"
        placeholder="区域编码"
        clearable
        style="width: 150px"
        @keyup.enter="loadData"
      />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
        <el-option label="启用" :value="1" />
        <el-option label="禁用" :value="0" />
        <el-option label="归档" :value="2" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
      <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
    </div>

    <!-- 项目卡片列表 -->
    <div class="project-cards" v-loading="loading">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-card panel"
        @click="enterDesign(project)"
      >
        <div class="card-header">
          <span class="card-title">{{ project.projectName }}</span>
          <el-tag :type="statusTagType(project.status)" size="small">
            {{ statusLabel(project.status) }}
          </el-tag>
        </div>
        <div class="card-body">
          <div class="card-info">
            <span class="info-label">编码:</span>
            <span class="info-value">{{ project.projectCode || '--' }}</span>
          </div>
          <div class="card-info">
            <span class="info-label">区域:</span>
            <span class="info-value">{{ project.regionCode || '--' }}</span>
          </div>
          <div class="card-info">
            <span class="info-label">坐标:</span>
            <span class="info-value">{{ project.centerLng }}, {{ project.centerLat }}</span>
          </div>
          <div class="card-info" v-if="project.description">
            <span class="info-label">描述:</span>
            <span class="info-value text-ellipsis">{{ project.description }}</span>
          </div>
        </div>
        <div class="card-footer">
          <span class="card-time">{{ project.createTime }}</span>
          <el-button-group>
            <el-button size="small" type="primary" @click.stop="enterDesign(project)">设计</el-button>
            <el-button size="small" @click.stop="enter3D(project)">3D</el-button>
            <el-button size="small" @click.stop="enterCoverage(project)">覆盖</el-button>
            <el-button size="small" type="danger" :icon="Delete" @click.stop="deleteProject(project)" />
          </el-button-group>
        </div>
      </div>

      <el-empty v-if="!loading && projects.length === 0" description="暂无项目，点击右上角新建" />
    </div>

    <!-- 分页 -->
    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="pagination.current"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadData"
        @current-change="loadData"
      />
    </div>

    <!-- 新建项目对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建项目" width="520px">
      <el-form :model="createForm" label-width="80px" size="default">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.projectName" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目编码">
          <el-input v-model="createForm.projectCode" placeholder="如: GD-WH-2024-001" />
        </el-form-item>
        <el-form-item label="区域编码">
          <el-input v-model="createForm.regionCode" placeholder="如: 420100" />
        </el-form-item>
        <el-form-item label="中心经度">
          <el-input-number v-model="createForm.centerLng" :precision="8" :step="0.0001" style="width: 100%" />
        </el-form-item>
        <el-form-item label="中心纬度">
          <el-input-number v-model="createForm.centerLat" :precision="8" :step="0.0001" style="width: 100%" />
        </el-form-item>
        <el-form-item label="缩放级别">
          <el-input-number v-model="createForm.zoomLevel" :min="1" :max="20" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createProject">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, RefreshLeft, Delete } from '@element-plus/icons-vue'
import projectApi from '@/api/project'

const router = useRouter()

const loading = ref(false)
const projects = ref([])
const showCreateDialog = ref(false)

const filters = reactive({
  projectName: '',
  regionCode: '',
  status: null
})

const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

const createForm = reactive({
  projectName: '',
  projectCode: '',
  regionCode: '',
  centerLng: 114.4263,
  centerLat: 30.4925,
  zoomLevel: 14,
  description: '',
  status: 1
})

async function loadData() {
  loading.value = true
  try {
    const res = await projectApi.page({
      current: pagination.current,
      size: pagination.size,
      projectName: filters.projectName || undefined,
      regionCode: filters.regionCode || undefined,
      status: filters.status ?? undefined
    })
    projects.value = res.data.records || []
    pagination.total = res.data.total || 0
  } catch (error) {
    ElMessage.error('加载项目列表失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.projectName = ''
  filters.regionCode = ''
  filters.status = null
  pagination.current = 1
  loadData()
}

async function createProject() {
  if (!createForm.projectName) {
    ElMessage.warning('请输入项目名称')
    return
  }
  try {
    await projectApi.create(createForm)
    ElMessage.success('项目创建成功')
    showCreateDialog.value = false
    Object.assign(createForm, {
      projectName: '', projectCode: '', regionCode: '',
      centerLng: 114.4263, centerLat: 30.4925, zoomLevel: 14, description: '', status: 1
    })
    loadData()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

function enterDesign(project) {
  router.push(`/design/${project.id}`)
}

function enter3D(project) {
  router.push(`/station-3d/${project.id}`)
}

function enterCoverage(project) {
  router.push(`/coverage/${project.id}`)
}

async function deleteProject(project) {
  try {
    await ElMessageBox.confirm(`确定删除项目「${project.projectName}」?`, '提示', { type: 'warning' })
    await projectApi.delete(project.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

function statusLabel(status) {
  return { 0: '禁用', 1: '启用', 2: '归档' }[status] || '未知'
}

function statusTagType(status) {
  return { 0: 'danger', 1: 'success', 2: 'info' }[status] || 'info'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.project-list-page {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;
  background: #f0f2f5;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-title h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.subtitle {
  font-size: 13px;
  color: #909399;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 8px;
}

.project-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
  flex: 1;
}

.project-card {
  padding: 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: box-shadow 0.3s, transform 0.2s;
}

.project-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.card-body {
  font-size: 13px;
  color: #606266;
}

.card-info {
  display: flex;
  margin-bottom: 4px;
}

.info-label {
  width: 50px;
  color: #909399;
  flex-shrink: 0;
}

.info-value {
  flex: 1;
}

.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.card-time {
  font-size: 12px;
  color: #c0c4cc;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
