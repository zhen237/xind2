<template>
  <div class="project-list">
    <el-card title="项目管理" class="card">
      <div class="search-bar">
        <el-input v-model="searchText" placeholder="搜索项目名称" class="search-input" @keyup.enter="loadProjects" />
        <el-button type="primary" @click="loadProjects">搜索</el-button>
        <el-button type="success" @click="showAddModal = true">新建项目</el-button>
      </div>
      
      <el-table :data="projects" border class="table">
        <el-table-column prop="projectCode" label="项目编号" />
        <el-table-column prop="projectName" label="项目名称" />
        <el-table-column prop="regionCode" label="所属区域" />
        <el-table-column prop="status" label="状态">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button size="small" @click="viewProject(scope.row)">查看</el-button>
            <el-button size="small" type="primary" @click="editProject(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteProject(scope.row)">删除</el-button>
            <el-button size="small" type="warning" @click="navigateToDesign(scope.row)">设计</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog title="新建/编辑项目" :visible.sync="showAddModal" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="项目编号">
          <el-input v-model="form.projectCode" />
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="form.projectName" />
        </el-form-item>
        <el-form-item label="所属区域">
          <el-select v-model="form.regionCode">
            <el-option v-for="region in regions" :key="region.regionCode" :label="region.regionName" :value="region.regionCode" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目描述">
          <el-textarea v-model="form.description" rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option :label="getStatusText(0)" :value="0" />
            <el-option :label="getStatusText(1)" :value="1" />
            <el-option :label="getStatusText(2)" :value="2" />
          </el-select>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="showAddModal = false">取消</el-button>
        <el-button type="primary" @click="saveProject">确定</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '../../utils/request'

const searchText = ref('')
const projects = ref([])
const regions = ref([])
const showAddModal = ref(false)
const form = ref({
  id: null,
  projectCode: '',
  projectName: '',
  regionCode: '',
  description: '',
  status: 0
})

const getStatusType = (status) => {
  const types = ['info', 'warning', 'success']
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = ['草稿', '进行中', '已完成']
  return texts[status] || '未知'
}

const loadProjects = async () => {
  try {
    let data = await request.get('/m03/project')
    if (searchText.value) {
      data = data.filter(p => p.projectName.includes(searchText.value))
    }
    projects.value = data
  } catch (e) {
    console.error(e)
  }
}

const loadRegions = async () => {
  try {
    regions.value = await request.get('/m03/region')
  } catch (e) {
    console.error(e)
  }
}

const viewProject = (project) => {
  console.log('查看项目:', project)
}

const editProject = (project) => {
  form.value = { ...project }
  showAddModal.value = true
}

const deleteProject = async (project) => {
  if (!confirm('确定删除该项目吗？')) return
  try {
    await request.delete(`/m03/project/${project.id}`)
    loadProjects()
  } catch (e) {
    console.error(e)
  }
}

const navigateToDesign = (project) => {
  window.location.href = `/m03/design?projectId=${project.id}`
}

const saveProject = async () => {
  try {
    if (form.value.id) {
      await request.put(`/m03/project/${form.value.id}`, form.value)
    } else {
      await request.post('/m03/project', form.value)
    }
    showAddModal.value = false
    loadProjects()
    form.value = { id: null, projectCode: '', projectName: '', regionCode: '', description: '', status: 0 }
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadProjects()
  loadRegions()
})
</script>

<style scoped>
.project-list {
  padding: 20px;
}

.card {
  max-width: 1200px;
  margin: 0 auto;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  width: 300px;
}

.table {
  margin-top: 10px;
}
</style>