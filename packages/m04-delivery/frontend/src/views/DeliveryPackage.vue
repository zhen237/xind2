<template>
  <div class="page-container">
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="项目ID">
          <el-input v-model.number="searchForm.projectId" placeholder="请输入项目ID" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态">
            <el-option :label="'全部'" :value="null" />
            <el-option label="待打包" :value="0" />
            <el-option label="已打包" :value="1" />
            <el-option label="已归档" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="addPackage" style="float: right;">新增交付包</el-button>
    </el-card>

    <el-card class="data-card">
      <el-table :data="tableData" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="projectId" label="项目ID" />
        <el-table-column prop="packageName" label="交付包名称" />
        <el-table-column prop="packageType" label="交付包类型" />
        <el-table-column prop="status" label="状态">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fileCount" label="文件数量" />
        <el-table-column prop="totalSize" label="总大小">
          <template #default="scope">
            {{ formatSize(scope.row.totalSize) }}
          </template>
        </el-table-column>
        <el-table-column prop="minioPath" label="存储路径" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="editPackage(scope.row)">编辑</el-button>
            <el-button size="small" @click="updateStatus(scope.row)">改状态</el-button>
            <el-button size="small" type="danger" @click="deletePackage(scope.row.id)">删除</el-button>
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
        <el-form-item label="交付包名称" prop="packageName">
          <el-input v-model="formData.packageName" />
        </el-form-item>
        <el-form-item label="交付包类型" prop="packageType">
          <el-input v-model="formData.packageType" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="formData.status">
            <el-option label="待打包" :value="0" />
            <el-option label="已打包" :value="1" />
            <el-option label="已归档" :value="2" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="savePackage">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog title="修改状态" :visible="statusDialogVisible" width="300px" @close="statusDialogVisible = false">
      <el-form :model="statusForm" label-width="80px">
        <el-form-item label="状态">
          <el-select v-model="statusForm.status">
            <el-option label="待打包" :value="0" />
            <el-option label="已打包" :value="1" />
            <el-option label="已归档" :value="2" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveStatus">确定</el-button>
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
const dialogTitle = ref('新增交付包')
const formData = reactive({
  id: null,
  projectId: null,
  packageName: '',
  packageType: '',
  status: 0,
  fileCount: 0,
  totalSize: 0,
  minioPath: ''
})

const statusDialogVisible = ref(false)
const statusForm = reactive({
  packageId: null,
  status: 0
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
    const res = await request.get('/delivery-package', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        projectId: searchForm.projectId,
        status: searchForm.status
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

const addPackage = () => {
  dialogTitle.value = '新增交付包'
  formData.id = null
  formData.projectId = null
  formData.packageName = ''
  formData.packageType = ''
  formData.status = 0
  formData.fileCount = 0
  formData.totalSize = 0
  formData.minioPath = ''
  dialogVisible.value = true
}

const editPackage = (row) => {
  dialogTitle.value = '编辑交付包'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const updateStatus = (row) => {
  statusForm.packageId = row.id
  statusForm.status = row.status
  statusDialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
}

const savePackage = async () => {
  try {
    if (formData.id) {
      await request.put(`/delivery-package/${formData.id}`, formData)
    } else {
      await request.post('/delivery-package', formData)
    }
    closeDialog()
    loadData()
    alert('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败')
  }
}

const saveStatus = async () => {
  try {
    await request.put(`/delivery-package/${statusForm.packageId}/status`, { status: statusForm.status })
    statusDialogVisible.value = false
    loadData()
    alert('更新成功')
  } catch (error) {
    console.error('更新失败:', error)
    alert('更新失败')
  }
}

const deletePackage = async (id) => {
  if (!confirm('确定要删除吗？')) return
  try {
    await request.delete(`/delivery-package/${id}`)
    loadData()
    alert('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败')
  }
}

const getStatusType = (status) => {
  const types = { 0: 'warning', 1: 'primary', 2: 'success' }
  return types[status] || 'default'
}

const getStatusLabel = (status) => {
  const labels = { 0: '待打包', 1: '已打包', 2: '已归档' }
  return labels[status] || status
}

const formatSize = (size) => {
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let index = 0
  let s = size
  while (s >= 1024 && index < units.length - 1) {
    s /= 1024
    index++
  }
  return s.toFixed(2) + ' ' + units[index]
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