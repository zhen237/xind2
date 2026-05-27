<template>
  <div class="page-container">
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="项目ID">
          <el-input v-model.number="searchForm.projectId" placeholder="请输入项目ID" />
        </el-form-item>
        <el-form-item label="任务状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态">
            <el-option :label="'全部'" :value="null" />
            <el-option label="待验收" :value="0" />
            <el-option label="验收中" :value="1" />
            <el-option label="已通过" :value="2" />
            <el-option label="未通过" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="addTask" style="float: right;">新增验收任务</el-button>
    </el-card>

    <el-card class="data-card">
      <el-table :data="tableData" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="projectId" label="项目ID" />
        <el-table-column prop="taskName" label="任务名称" />
        <el-table-column prop="taskType" label="任务类型" />
        <el-table-column prop="status" label="状态">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="problemCount" label="问题数量">
          <template #default="scope">
            <el-tag :type="scope.row.problemCount > 0 ? 'danger' : 'success'">{{ scope.row.problemCount || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="acceptanceTime" label="验收时间" width="180" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="editTask(scope.row)">编辑</el-button>
            <el-button size="small" @click="viewProblems(scope.row)">查看问题</el-button>
            <el-button size="small" type="danger" @click="deleteTask(scope.row.id)">删除</el-button>
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
        <el-form-item label="项目ID" prop="projectId">
          <el-input v-model.number="formData.projectId" />
        </el-form-item>
        <el-form-item label="任务名称" prop="taskName">
          <el-input v-model="formData.taskName" />
        </el-form-item>
        <el-form-item label="任务类型" prop="taskType">
          <el-input v-model="formData.taskType" />
        </el-form-item>
        <el-form-item label="验收标准" prop="acceptanceStandard">
          <el-input type="textarea" v-model="formData.acceptanceStandard" :rows="3" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="formData.status">
            <el-option label="待验收" :value="0" />
            <el-option label="验收中" :value="1" />
            <el-option label="已通过" :value="2" />
            <el-option label="未通过" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="结果描述" prop="resultDescription">
          <el-input type="textarea" v-model="formData.resultDescription" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveTask">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog title="验收问题列表" :visible="problemDialogVisible" width="800px" @close="problemDialogVisible = false">
      <div style="margin-bottom: 10px;">
        <el-button type="primary" size="small" @click="addProblem">新增问题</el-button>
      </div>
      <el-table :data="problemList" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="problemTitle" label="问题标题" />
        <el-table-column prop="problemLevel" label="问题级别">
          <template #default="scope">
            <el-tag :type="getProblemLevelType(scope.row.problemLevel)">{{ getProblemLevelLabel(scope.row.problemLevel) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="problemDescription" label="问题描述" />
        <el-table-column prop="status" label="状态">
          <template #default="scope">
            <el-tag :type="getProblemStatusType(scope.row.status)">{{ getProblemStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rectifyDeadline" label="整改截止日期" />
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="editProblem(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteProblem(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog :title="problemDialogTitle" :visible="problemFormVisible" width="600px" @close="problemFormVisible = false">
      <el-form :model="problemForm" label-width="120px">
        <el-form-item label="问题标题" prop="problemTitle">
          <el-input v-model="problemForm.problemTitle" />
        </el-form-item>
        <el-form-item label="问题级别" prop="problemLevel">
          <el-select v-model="problemForm.problemLevel">
            <el-option label="一般" :value="1" />
            <el-option label="严重" :value="2" />
            <el-option label="重大" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题描述" prop="problemDescription">
          <el-input type="textarea" v-model="problemForm.problemDescription" :rows="3" />
        </el-form-item>
        <el-form-item label="整改截止日期" prop="rectifyDeadline">
          <el-date-picker v-model="problemForm.rectifyDeadline" type="date" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="problemForm.status">
            <el-option label="待整改" :value="0" />
            <el-option label="整改中" :value="1" />
            <el-option label="已整改" :value="2" />
            <el-option label="已复查" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="整改结果" prop="rectifyResult">
          <el-input type="textarea" v-model="problemForm.rectifyResult" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="problemFormVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProblem">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '../utils/request'

const searchForm = reactive({
  projectId: null,
  status: null
})

const tableData = ref([])
const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const dialogVisible = ref(false)
const dialogTitle = ref('新增验收任务')
const formData = reactive({
  id: null,
  projectId: null,
  taskName: '',
  taskType: '',
  status: 0,
  acceptanceStandard: '',
  resultDescription: '',
  problemCount: 0
})

const problemDialogVisible = ref(false)
const problemList = ref([])
const currentTaskId = ref(null)

const problemFormVisible = ref(false)
const problemDialogTitle = ref('新增验收问题')
const problemForm = reactive({
  id: null,
  taskId: null,
  problemTitle: '',
  problemLevel: 1,
  problemDescription: '',
  status: 0,
  rectifyDeadline: '',
  rectifyResult: ''
})

const search = () => {
  pagination.pageNum = 1
  loadData()
}

const reset = () => {
  searchForm.projectId = null
  searchForm.status = null
  search()
}

const loadData = async () => {
  try {
    const res = await request.get('/acceptance/task', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        projectId: searchForm.projectId,
        status: searchForm.status
      }
    })
    tableData.value = res?.records || []
    pagination.total = res?.total || res?.records?.length || 0
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const handlePageChange = (page) => {
  pagination.pageNum = page
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
  formData.problemCount = 0
  dialogVisible.value = true
}

const editTask = (row) => {
  dialogTitle.value = '编辑验收任务'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
}

const saveTask = async () => {
  try {
    if (formData.id) {
      await request.put(`/acceptance/task/${formData.id}`, formData)
    } else {
      await request.post('/acceptance/task', formData)
    }
    closeDialog()
    loadData()
    alert('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败')
  }
}

const deleteTask = async (id) => {
  if (!confirm('确定要删除吗？')) return
  try {
    await request.delete(`/acceptance/task/${id}`)
    loadData()
    alert('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败')
  }
}

const viewProblems = async (row) => {
  currentTaskId.value = row.id
  try {
    const res = await request.get('/acceptance/problem', {
      params: { pageNum: 1, pageSize: 100, taskId: row.id }
    })
    problemList.value = res.records
    problemDialogVisible.value = true
  } catch (error) {
    console.error('加载问题失败:', error)
  }
}

const addProblem = () => {
  problemDialogTitle.value = '新增验收问题'
  problemForm.id = null
  problemForm.taskId = currentTaskId.value
  problemForm.problemTitle = ''
  problemForm.problemLevel = 1
  problemForm.problemDescription = ''
  problemForm.status = 0
  problemForm.rectifyDeadline = ''
  problemForm.rectifyResult = ''
  problemFormVisible.value = true
}

const editProblem = (row) => {
  problemDialogTitle.value = '编辑验收问题'
  Object.assign(problemForm, row)
  problemFormVisible.value = true
}

const saveProblem = async () => {
  try {
    if (problemForm.id) {
      await request.put(`/acceptance/problem/${problemForm.id}`, problemForm)
    } else {
      await request.post('/acceptance/problem', problemForm)
    }
    problemFormVisible.value = false
    viewProblems({ id: currentTaskId.value })
    alert('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败')
  }
}

const deleteProblem = async (id) => {
  if (!confirm('确定要删除吗？')) return
  try {
    await request.delete(`/acceptance/problem/${id}`)
    viewProblems({ id: currentTaskId.value })
    alert('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败')
  }
}

const getStatusType = (status) => {
  const types = { 0: 'warning', 1: 'primary', 2: 'success', 3: 'danger' }
  return types[status] || 'default'
}

const getStatusLabel = (status) => {
  const labels = { 0: '待验收', 1: '验收中', 2: '已通过', 3: '未通过' }
  return labels[status] || status
}

const getProblemLevelType = (level) => {
  const types = { 1: 'success', 2: 'warning', 3: 'danger' }
  return types[level] || 'default'
}

const getProblemLevelLabel = (level) => {
  const labels = { 1: '一般', 2: '严重', 3: '重大' }
  return labels[level] || level
}

const getProblemStatusType = (status) => {
  const types = { 0: 'warning', 1: 'primary', 2: 'success', 3: 'info' }
  return types[status] || 'default'
}

const getProblemStatusLabel = (status) => {
  const labels = { 0: '待整改', 1: '整改中', 2: '已整改', 3: '已复查' }
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