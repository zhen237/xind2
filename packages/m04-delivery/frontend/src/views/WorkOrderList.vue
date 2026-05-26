<template>
  <div class="page-container">
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="工单标题">
          <el-input v-model="searchForm.title" placeholder="请输入工单标题" />
        </el-form-item>
        <el-form-item label="工单状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态">
            <el-option :label="'全部'" :value="null" />
            <el-option label="待处理" :value="0" />
            <el-option label="处理中" :value="1" />
            <el-option label="已完成" :value="2" />
            <el-option label="已关闭" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="工单类型">
          <el-input v-model="searchForm.type" placeholder="请输入工单类型" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="addOrder" style="float: right;">新增工单</el-button>
    </el-card>

    <el-card class="data-card">
      <el-table :data="tableData" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="orderNo" label="工单编号" />
        <el-table-column prop="title" label="工单标题" />
        <el-table-column prop="type" label="工单类型" />
        <el-table-column prop="priority" label="优先级">
          <template #default="scope">
            <el-tag :type="getPriorityType(scope.row.priority)">{{ getPriorityLabel(scope.row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stationCode" label="站点编码" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="editOrder(scope.row)">编辑</el-button>
            <el-button size="small" @click="updateOrderStatus(scope.row)">改状态</el-button>
            <el-button size="small" type="danger" @click="deleteOrder(scope.row.id)">删除</el-button>
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
        <el-form-item label="工单标题" prop="title">
          <el-input v-model="formData.title" />
        </el-form-item>
        <el-form-item label="工单类型" prop="type">
          <el-input v-model="formData.type" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="formData.priority">
            <el-option label="低" :value="1" />
            <el-option label="中" :value="2" />
            <el-option label="高" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="站点编码" prop="stationCode">
          <el-input v-model="formData.stationCode" />
        </el-form-item>
        <el-form-item label="设备编码" prop="deviceCode">
          <el-input v-model="formData.deviceCode" />
        </el-form-item>
        <el-form-item label="工单描述" prop="description">
          <el-input type="textarea" v-model="formData.description" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveOrder">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog title="修改状态" :visible="statusDialogVisible" width="300px" @close="statusDialogVisible = false">
      <el-form :model="statusForm" label-width="80px">
        <el-form-item label="状态">
          <el-select v-model="statusForm.status">
            <el-option label="待处理" :value="0" />
            <el-option label="处理中" :value="1" />
            <el-option label="已完成" :value="2" />
            <el-option label="已关闭" :value="3" />
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
  title: '',
  status: null,
  type: ''
})

const tableData = ref([])
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
  status: 0
})

const search = () => {
  pagination.pageNum = 1
  loadData()
}

const reset = () => {
  searchForm.title = ''
  searchForm.status = null
  searchForm.type = ''
  search()
}

const loadData = async () => {
  try {
    const res = await request.get('/work-order', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        title: searchForm.title,
        status: searchForm.status,
        type: searchForm.type
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
  statusDialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
}

const saveOrder = async () => {
  try {
    if (formData.id) {
      await request.put(`/work-order/${formData.id}`, formData)
    } else {
      await request.post('/work-order', formData)
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
    await request.put(`/work-order/${statusForm.orderId}/status`, { status: statusForm.status })
    statusDialogVisible.value = false
    loadData()
    alert('更新成功')
  } catch (error) {
    console.error('更新失败:', error)
    alert('更新失败')
  }
}

const deleteOrder = async (id) => {
  if (!confirm('确定要删除吗？')) return
  try {
    await request.delete(`/work-order/${id}`)
    loadData()
    alert('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败')
  }
}

const getPriorityType = (priority) => {
  const types = { 1: 'success', 2: 'warning', 3: 'danger' }
  return types[priority] || 'default'
}

const getPriorityLabel = (priority) => {
  const labels = { 1: '低', 2: '中', 3: '高' }
  return labels[priority] || priority
}

const getStatusType = (status) => {
  const types = { 0: 'warning', 1: 'primary', 2: 'success', 3: 'info' }
  return types[status] || 'default'
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