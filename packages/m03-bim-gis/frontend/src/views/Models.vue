<template>
  <div class="models-page">
    <header class="page-header">
      <div class="header-left">
        <el-button text @click="$router.push('/design')">
          <el-icon><ArrowLeft /></el-icon> 返回设计
        </el-button>
        <h1>模型管理</h1>
        <el-tag type="info" effect="plain" size="small">{{ models.length }} 个模型</el-tag>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索模型名称 / 编码 / 类型..."
          clearable
          :prefix-icon="Search"
          class="search-input-wide"
        />
        <el-select v-model="typeFilter" placeholder="模型类型" clearable class="type-filter">
          <el-option label="全部类型" value="" />
          <el-option v-for="t in modelTypes" :key="t" :label="t" :value="t" />
        </el-select>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon> 添加模型
        </el-button>
      </div>
    </header>

    <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="filteredModels"
        stripe
        border
        class="form-full-width"
        max-height="calc(100vh - 140px)"
        row-key="id"
      >
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="modelName" label="模型名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="modelCode" label="编码" width="140" show-overflow-tooltip />
        <el-table-column prop="modelType" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.modelType)" size="small">{{ row.modelType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scale" label="比例" width="90" align="center" />
        <el-table-column prop="fileSize" label="大小" width="100" align="right">
          <template #default="{ row }">
            {{ row.fileSize ? formatFileSize(row.fileSize) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.description || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" align="center" />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-popconfirm
              title="确认删除该模型?"
              confirm-button-text="确认"
              cancel-button-text="取消"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button link type="danger" size="small">
                  <el-icon><Delete /></el-icon> 删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑模型' : '添加模型'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="90px"
        label-position="right"
      >
        <el-form-item label="模型名称" prop="modelName">
          <el-input v-model="form.modelName" placeholder="如: 定向天线 A1" maxlength="100" />
        </el-form-item>
        <el-form-item label="编码" prop="modelCode">
          <el-input v-model="form.modelCode" placeholder="如: ANT-A1-001" maxlength="50" />
        </el-form-item>
        <el-form-item label="类型" prop="modelType">
          <el-select v-model="form.modelType" placeholder="选择类型" class="form-full-width">
            <el-option label="天线" value="antenna" />
            <el-option label="塔桅" value="tower" />
            <el-option label="机房" value="machine_room" />
            <el-option label="管线" value="pipeline" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="比例" prop="scale">
          <el-input v-model="form.scale" placeholder="如: 1:100" maxlength="20" />
        </el-form-item>
        <el-form-item label="文件路径" prop="filePath">
          <el-input v-model="form.filePath" placeholder="三维模型文件路径" maxlength="500" />
        </el-form-item>
        <el-form-item label="预览图" prop="thumbnailPath">
          <el-input v-model="form.thumbnailPath" placeholder="缩略图路径" maxlength="500" />
        </el-form-item>
        <el-form-item label="文件大小" prop="fileSize">
          <el-input-number
            v-model="form.fileSize"
            :min="0"
            :step="1024"
            placeholder="字节"
            class="form-full-width"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="模型描述"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEditing ? '保存修改' : '确认添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default { name: 'ModelsView' }
</script>
<script setup>
import { ref, computed } from 'vue'
import { Plus, Edit, Delete, ArrowLeft, Search } from '@element-plus/icons-vue'
import { modelAPI } from '@/utils/request'
import { useCrudTable } from '@/composables/useCrudTable'

// ── 组件专属状态 ────────────────────────────────────────────
const typeFilter = ref('')
const modelTypes = ref([])

// ── Composable — 通用 CRUD ──────────────────────────────────
const {
  loading, saving, items: models, searchQuery,
  dialogVisible, isEditing, editingId, formRef, form,
  filteredItems: baseFiltered,
  showCreateDialog, showEditDialog, handleSave, handleDelete, fetchItems,
} = useCrudTable({
  api: modelAPI,
  entityName: '模型',
  initialForm: {
    modelName: '', modelCode: '', modelType: '',
    filePath: '', fileSize: null, thumbnailPath: '', scale: '', description: '',
  },
  searchFields: ['modelName', 'modelCode', 'modelType'],
  onFetchSuccess: (items) => {
    modelTypes.value = [...new Set(items.map(m => m.modelType).filter(Boolean))]
  },
  autoFetch: true,
})

// ── 组合搜索（前端搜索 + 类型过滤器） ────────────────────────
const filteredModels = computed(() => {
  let result = baseFiltered.value
  const type = typeFilter.value
  if (type) {
    result = result.filter(m => m.modelType === type)
  }
  return result
})

// ── 表单验证规则 ────────────────────────────────────────────
const formRules = {
  modelName: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  modelCode: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  modelType: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

// ── 工具函数 ────────────────────────────────────────────────
function getTypeTagType(modelType) {
  const map = { antenna: 'success', tower: 'warning', machine_room: 'primary', pipeline: 'info' }
  return map[modelType] || ''
}

function formatFileSize(bytes) {
  if (!bytes || bytes < 0) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.models-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #0a0f1a);
  overflow: hidden;
}

.page-header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-secondary, #0d1b2a);
  border-bottom: 1px solid rgba(0, 212, 255, 0.15);
  gap: 16px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h1 {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color, #00d4ff);
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-wrapper {
  flex: 1;
  padding: 16px 24px;
  overflow: auto;
}

/* ── 布局辅助类 ──────────────────────────────────────────── */
.form-full-width { width: 100%; }
.search-input-wide { width: 280px; }
.type-filter { width: 160px; }
</style>
