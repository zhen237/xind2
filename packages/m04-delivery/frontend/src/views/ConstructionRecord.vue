<template>
  <div class="page-container">
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="项目ID">
          <el-input v-model.number="searchForm.projectId" placeholder="请输入项目ID" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="searchForm.responsiblePerson" placeholder="请输入负责人" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="addRecord" style="float: right;">新增记录</el-button>
    </el-card>

    <el-card class="data-card">
      <el-table :data="tableData" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="projectId" label="项目ID" />
        <el-table-column prop="responsiblePerson" label="负责人" />
        <el-table-column prop="workDate" label="施工日期" />
        <el-table-column prop="workContent" label="施工内容" />
        <el-table-column prop="constructionUnits" label="施工班组" />
        <el-table-column prop="environmentAssessment" label="环境评估">
          <template #default="scope">
            <el-tag :type="scope.row.environmentAssessment === 0 ? 'success' : 'danger'">
              {{ scope.row.environmentAssessment === 0 ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hazardDescription" label="危险源描述" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="editRecord(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteRecord(scope.row.id)">删除</el-button>
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
        <el-form-item label="负责人" prop="responsiblePerson">
          <el-input v-model="formData.responsiblePerson" />
        </el-form-item>
        <el-form-item label="施工日期" prop="workDate">
          <el-date-picker v-model="formData.workDate" type="date" />
        </el-form-item>
        <el-form-item label="施工内容" prop="workContent">
          <el-input type="textarea" v-model="formData.workContent" :rows="3" />
        </el-form-item>
        <el-form-item label="施工班组" prop="constructionUnits">
          <el-input v-model="formData.constructionUnits" />
        </el-form-item>
        <el-form-item label="环境评估" prop="environmentAssessment">
          <el-select v-model="formData.environmentAssessment">
            <el-option label="正常" :value="0" />
            <el-option label="异常" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="危险源描述" prop="hazardDescription">
          <el-input type="textarea" v-model="formData.hazardDescription" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveRecord">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '../utils/request'

const searchForm = reactive({
  projectId: null,
  responsiblePerson: ''
})

const tableData = ref([])
const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const dialogVisible = ref(false)
const dialogTitle = ref('新增施工记录')
const formData = reactive({
  id: null,
  projectId: null,
  responsiblePerson: '',
  workDate: '',
  workContent: '',
  constructionUnits: '',
  environmentAssessment: 0,
  hazardDescription: ''
})

const search = () => {
  pagination.pageNum = 1
  loadData()
}

const reset = () => {
  searchForm.projectId = null
  searchForm.responsiblePerson = ''
  search()
}

const loadData = async () => {
  try {
    const res = await request.get('/construction-record', {
      params: {
        pageNum: pagination.pageNum,
        pageSize: pagination.pageSize,
        projectId: searchForm.projectId,
        responsiblePerson: searchForm.responsiblePerson
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

const addRecord = () => {
  dialogTitle.value = '新增施工记录'
  formData.id = null
  formData.projectId = null
  formData.responsiblePerson = ''
  formData.workDate = ''
  formData.workContent = ''
  formData.constructionUnits = ''
  formData.environmentAssessment = 0
  formData.hazardDescription = ''
  dialogVisible.value = true
}

const editRecord = (row) => {
  dialogTitle.value = '编辑施工记录'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
}

const saveRecord = async () => {
  try {
    if (formData.id) {
      await request.put(`/construction-record/${formData.id}`, formData)
    } else {
      await request.post('/construction-record', formData)
    }
    closeDialog()
    loadData()
    alert('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败')
  }
}

const deleteRecord = async (id) => {
  if (!confirm('确定要删除吗？')) return
  try {
    await request.delete(`/construction-record/${id}`)
    loadData()
    alert('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败')
  }
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