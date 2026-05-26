<template>
  <div class="page-container">
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="项目名称">
          <el-input v-model="searchForm.projectName" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="区域编码">
          <el-input v-model="searchForm.regionCode" placeholder="请输入区域编码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="addProject" style="float: right;">新增项目</el-button>
    </el-card>

    <el-card class="data-card">
      <el-table :data="tableData" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="projectName" label="项目名称" />
        <el-table-column prop="projectCode" label="项目编号" />
        <el-table-column prop="regionCode" label="区域编码" />
        <el-table-column prop="currentPhase" label="当前阶段">
          <template #default="scope">
            <el-tag :type="getPhaseType(scope.row.currentPhase)">{{ getPhaseLabel(scope.row.currentPhase) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalProgress" label="总进度">
          <template #default="scope">
            <el-progress :percentage="scope.row.totalProgress" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="editProject(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteProject(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        :current-page="pagination.pageNum"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        @current-change="handlePageChange"
        layout="total, prev, pager, next, jumper"
      />
    </el-card>

    <el-dialog :title="dialogTitle" :visible="dialogVisible" width="600px" @close="closeDialog">
      <el-form :model="formData" label-width="120px">
        <el-form-item label="项目名称" prop="projectName">
          <el-input v-model="formData.projectName" />
        </el-form-item>
        <el-form-item label="项目编号" prop="projectCode">
          <el-input v-model="formData.projectCode" />
        </el-form-item>
        <el-form-item label="区域编码" prop="regionCode">
          <el-input v-model="formData.regionCode" />
        </el-form-item>
        <el-form-item label="当前阶段" prop="currentPhase">
          <el-select v-model="formData.currentPhase">
            <el-option label="规划" value="PLANNING" />
            <el-option label="设计" value="DESIGN" />
            <el-option label="施工" value="CONSTRUCTION" />
            <el-option label="验收" value="ACCEPTANCE" />
          </el-select>
        </el-form-item>
        <el-form-item label="施工单位" prop="constructionUnit">
          <el-input v-model="formData.constructionUnit" />
        </el-form-item>
        <el-form-item label="设计单位" prop="designUnit">
          <el-input v-model="formData.designUnit" />
        </el-form-item>
        <el-form-item label="监理单位" prop="supervisionUnit">
          <el-input v-model="formData.supervisionUnit" />
        </el-form-item>
        <el-form-item label="建设单位" prop="ownerUnit">
          <el-input v-model="formData.ownerUnit" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveProject">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '../utils/request'

const searchForm = reactive({
  projectName: '',
  regionCode: ''
})

const tableData = ref([])
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
  loadData()
}

const reset = () => {
  searchForm.projectName = ''
  searchForm.regionCode = ''
  search()
}

const loadData = async () => {
  try {
    const res = await request.get('/project', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        projectName: searchForm.projectName,
        regionCode: searchForm.regionCode
      }
    })
    tableData.value = res.records
    pagination.total = res.total
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const handlePageChange = (page) => {
  pagination.pageNum = page
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
      await request.put(`/project/${formData.id}`, formData)
    } else {
      await request.post('/project', formData)
    }
    closeDialog()
    loadData()
    alert('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败')
  }
}

const deleteProject = async (id) => {
  if (!confirm('确定要删除吗？')) return
  try {
    await request.delete(`/project/${id}`)
    loadData()
    alert('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败')
  }
}

const getPhaseType = (phase) => {
  const types = { PLANNING: 'info', DESIGN: 'primary', CONSTRUCTION: 'warning', ACCEPTANCE: 'success' }
  return types[phase] || 'default'
}

const getPhaseLabel = (phase) => {
  const labels = { PLANNING: '规划', DESIGN: '设计', CONSTRUCTION: '施工', ACCEPTANCE: '验收' }
  return labels[phase] || phase
}

const getStatusType = (status) => {
  const types = { 0: 'warning', 1: 'success', 2: 'info' }
  return types[status] || 'default'
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
  padding: 0;
}

.search-card {
  margin-bottom: 20px;
}

.search-form {
  margin-bottom: 10px;
}

.data-card {
  min-height: 400px;
}
</style>