<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="brand-section-title">规则管理</span>
          <div class="card-actions">
            <el-button type="primary" @click="showCreateDialog = true" :disabled="!isAdmin">新增规则</el-button>
            <el-select v-model="filterCategory" placeholder="按分类筛选" style="width: 120px; margin-left: 10px">
              <el-option label="全部" value="" />
              <el-option label="电力" value="电力" />
              <el-option label="防雷" value="防雷" />
              <el-option label="结构" value="结构" />
              <el-option label="电磁" value="电磁" />
              <el-option label="通用" value="通用" />
            </el-select>
          </div>
        </div>
      </template>
      <div class="page-content">
        <el-table :data="filteredData" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="ruleCode" label="规则编号" />
          <el-table-column prop="ruleName" label="规则名称" />
          <el-table-column prop="category" label="分类" />
          <el-table-column prop="threshold" label="阈值条件" min-width="150" />
          <el-table-column prop="riskLevel" label="风险等级">
            <template #default="scope">
              <el-tag :type="getRiskLevelType(scope.row.riskLevel)">
                {{ getRiskLevelText(scope.row.riskLevel) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态">
            <template #default="scope">
              <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">
                {{ scope.row.status === 1 ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createTime" label="创建时间" />
          <el-table-column label="操作">
            <template #default="scope">
              <el-button size="small" @click="showEditDialog(scope.row)" :disabled="!isAdmin">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(scope.row.id)" :disabled="!isAdmin">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑规则' : '新增规则'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="规则编号" prop="ruleCode" :rules="[{ required: true, message: '请输入规则编号' }]">
          <el-input v-model="form.ruleCode" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="规则名称" prop="ruleName" :rules="[{ required: true, message: '请输入规则名称' }]">
          <el-input v-model="form.ruleName" />
        </el-form-item>
        <el-form-item label="分类" prop="category" :rules="[{ required: true, message: '请选择分类' }]">
          <el-select v-model="form.category">
            <el-option label="电力" value="电力" />
            <el-option label="防雷" value="防雷" />
            <el-option label="结构" value="结构" />
            <el-option label="电磁" value="电磁" />
            <el-option label="通用" value="通用" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值条件" prop="threshold">
          <el-input v-model="form.threshold" />
        </el-form-item>
        <el-form-item label="风险等级" prop="riskLevel" :rules="[{ required: true, message: '请选择风险等级' }]">
          <el-select v-model="form.riskLevel">
            <el-option label="严重(critical)" value="critical" />
            <el-option label="错误(error)" value="error" />
            <el-option label="警告(warning)" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item label="整改建议" prop="suggestion">
          <el-input v-model="form.suggestion" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { ruleApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuth } from '../utils/auth'

const { isAdmin } = useAuth()

const tableData = ref([])
const showDialog = ref(false)
const filterCategory = ref('')
const isEdit = ref(false)

const form = reactive({
  id: '',
  ruleCode: '',
  ruleName: '',
  category: '',
  threshold: '',
  riskLevel: 'warning',
  suggestion: '',
  status: 1
})

const filteredData = computed(() => {
  if (!filterCategory.value) {
    return tableData.value
  }
  return tableData.value.filter(item => item.category === filterCategory.value)
})

const loadRules = async () => {
  try {
    const res = await ruleApi.list()
    tableData.value = res.data || []
  } catch (error) {
    console.error('加载规则失败:', error)
    ElMessage.error('加载规则失败')
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  Object.assign(form, {
    id: '',
    ruleCode: '',
    ruleName: '',
    category: '',
    threshold: '',
    riskLevel: 'warning',
    suggestion: '',
    status: 1
  })
  showDialog.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    ruleCode: row.ruleCode,
    ruleName: row.ruleName,
    category: row.category,
    threshold: row.threshold,
    riskLevel: row.riskLevel,
    suggestion: row.suggestion || '',
    status: row.status
  })
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const handleSave = async () => {
  if (!form.ruleCode) {
    ElMessage.warning('请输入规则编号')
    return
  }
  if (!form.ruleName) {
    ElMessage.warning('请输入规则名称')
    return
  }
  if (!form.category) {
    ElMessage.warning('请选择分类')
    return
  }
  if (!form.riskLevel) {
    ElMessage.warning('请选择风险等级')
    return
  }

  try {
    if (isEdit.value) {
      await ruleApi.update(form)
      ElMessage.success('规则更新成功')
    } else {
      await ruleApi.create(form)
      ElMessage.success('规则创建成功')
    }
    showDialog.value = false
    loadRules()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  }
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这条规则吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await ruleApi.delete(id)
    ElMessage.success('删除成功')
    loadRules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadRules()
})

const getRiskLevelType = (level) => {
  const types = {
    critical: 'danger',
    error: 'warning',
    warning: 'info'
  }
  return types[level] || 'info'
}

const getRiskLevelText = (level) => {
  const texts = {
    critical: '严重',
    error: '错误',
    warning: '警告'
  }
  return texts[level] || level
}
</script>

<style scoped>
.page-container {
  padding: 22px;
}

.page-card {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 4px;
}

.card-actions {
  display: flex;
  align-items: center;
}

.page-content {
  padding-top: 18px;
}
</style>
