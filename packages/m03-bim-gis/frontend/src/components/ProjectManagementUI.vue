/**
 * 项目管理UI组件
 * 提供项目的可视化管理界面
 */

<template>
  <el-dialog
    v-model="dialogVisible"
    title="项目管理"
    width="800px"
    :before-close="handleClose"
    class="project-management-dialog"
  >
    <!-- 搜索和筛选 -->
    <div class="project-controls">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索项目名称..."
        clearable
        style="width: 300px;"
        aria-label="搜索项目"
        @input="filterProjects"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select
        v-model="filterLocation"
        placeholder="按位置筛选"
        clearable
        style="width: 150px; margin-left: 10px;"
        aria-label="按位置筛选项目"
        @change="filterProjects"
      >
        <el-option
          v-for="loc in locationOptions"
          :key="loc.value"
          :label="loc.label"
          :value="loc.value"
        />
      </el-select>
      
      <el-button 
        type="primary" 
        style="margin-left: auto;"
        aria-label="保存当前设计为项目"
        @click="saveCurrentAsProject"
      >
        <el-icon><Plus /></el-icon> 保存新项目
      </el-button>
    </div>
    
    <!-- 项目列表 -->
    <el-table
      :data="filteredProjects"
      stripe
      highlight-current-row
      class="project-table"
      aria-label="项目列表"
      @row-click="handleRowClick"
    >
      <el-table-column
        prop="name"
        label="项目名称"
        min-width="150"
      >
        <template #default="{ row }">
          <span class="project-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      
      <el-table-column
        prop="location"
        label="位置"
        width="120"
      >
        <template #default="{ row }">
          <el-tag size="small">
            {{ getLocationName(row.location) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column
        prop="siteCount"
        label="站点数"
        width="80"
        align="center"
      >
        <template #default="{ row }">
          {{ row.siteCount || 0 }}
        </template>
      </el-table-column>
      
      <el-table-column
        prop="updatedAt"
        label="更新时间"
        width="160"
        sortable
      >
        <template #default="{ row }">
          {{ ProjectManager.formatTime(row.updatedAt) }}
        </template>
      </el-table-column>
      
      <el-table-column
        label="操作"
        width="200"
        fixed="right"
      >
        <template #default="{ row }">
          <el-button
            size="small"
            type="primary"
            aria-label="加载项目 {{ row.name }}"
            @click.stop="loadProjectAction(row.id)"
          >
            加载
          </el-button>
          <el-button
            size="small"
            type="danger"
            aria-label="删除项目 {{ row.name }}"
            @click.stop="deleteProjectAction(row.id)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 项目统计 -->
    <div class="project-stats">
      <el-statistic
        title="项目总数"
        :value="filteredProjects.length"
      />
      <el-statistic
        title="存储使用"
        :value="storageUsedMB"
        suffix="MB"
      />
    </div>
    
    <template #footer>
      <el-button @click="dialogVisible = false">
        关闭
      </el-button>
    </template>
  </el-dialog>
</template>

<script>
export default { name: 'ProjectManagementUI' }
</script>
<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { ProjectManager } from '@/utils/projectManager.js'
import { DEFAULT_LOCATION } from '@/config/location.js'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  currentSites: {
    type: Array,
    default: () => []
  },
  currentParams: {
    type: Object,
    default: () => ({})
  },
  currentLocation: {
    type: String,
    default: 'yuncheng'
  }
})

const emit = defineEmits(['update:visible', 'project-loaded'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const searchKeyword = ref('')
const filterLocation = ref('')
const projects = ref(ProjectManager.loadProjects())

// 位置选项
const locationOptions = [
  { label: '运城学院', value: 'yuncheng' },
  { label: '武汉', value: 'wuhan' },
  { label: '北京', value: 'beijing' }
]

// 过滤后的项目
const filteredProjects = computed(() => {
  let result = [...projects.value]
  
  // 关键词搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(p => 
      p.name.toLowerCase().includes(keyword)
    )
  }
  
  // 位置筛选
  if (filterLocation.value) {
    result = result.filter(p => p.location === filterLocation.value)
  }
  
  return result
})

// 存储使用量
const storageUsedMB = computed(() => {
  const stats = ProjectManager.getStats()
  return (stats.storageUsed / 1024 / 1024).toFixed(2)
})

// 过滤项目
const filterProjects = () => {
  // 计算属性自动更新
}

// 获取位置名称
const getLocationName = (locationKey) => {
  const config = Object.values(DEFAULT_LOCATION).find(
    loc => loc.id === locationKey
  )
  return config ? config.name : locationKey
}

// 保存当前设计为项目
const saveCurrentAsProject = () => {
  if (props.currentSites.length === 0) {
    ElMessage.warning('当前没有站点数据，无法保存项目')
    return
  }
  
  ElMessageBox.prompt('请输入项目名称', '保存项目', {
    confirmButtonText: '保存',
    cancelButtonText: '取消'
  }).then(({ value }) => {
    const projectData = {
      name: value,
      location: props.currentLocation,
      params: { ...props.currentParams },
      sites: JSON.parse(JSON.stringify(props.currentSites)),
      siteCount: props.currentSites.length,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    
    ProjectManager.saveProject(projectData)
    projects.value = ProjectManager.loadProjects()
    ElMessage.success('项目保存成功')
  }).catch(() => {})
}

// 加载项目
const loadProjectAction = (projectId) => {
  const project = ProjectManager.loadProject(projectId)
  if (project) {
    emit('project-loaded', project)
    dialogVisible.value = false
    ElMessage.success(`已加载项目: ${project.name}`)
  }
}

// 删除项目
const deleteProjectAction = (projectId) => {
  const project = ProjectManager.loadProject(projectId)
  if (!project) return
  
  ElMessageBox.confirm(
    `确定要删除项目"${project.name}"吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ProjectManager.deleteProject(projectId)
    projects.value = ProjectManager.loadProjects()
    ElMessage.success('项目已删除')
  }).catch(() => {})
}

// 行点击
const handleRowClick = (row) => {
  loadProjectAction(row.id)
}

// 关闭对话框
const handleClose = () => {
  dialogVisible.value = false
}

// 监听项目变化
watch(
  () => props.visible,
  (val) => {
    if (val) {
      projects.value = ProjectManager.loadProjects()
    }
  }
)
</script>

<style scoped>
.project-management-dialog {
  :deep(.el-dialog__body) {
    padding: 20px;
  }
}

.project-controls {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.project-table {
  margin-bottom: 20px;
}

.project-name {
  font-weight: 500;
}

.project-stats {
  display: flex;
  gap: 40px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}
</style>
