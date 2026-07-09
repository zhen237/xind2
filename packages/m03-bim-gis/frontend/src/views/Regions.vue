<template>
  <div class="regions-page">
    <header class="page-header">
      <div class="header-left">
        <el-button text @click="$router.push('/design')">
          <el-icon><ArrowLeft /></el-icon> 返回设计
        </el-button>
        <h1>区域管理</h1>
        <el-tag type="info" effect="plain" size="small">{{ regions.length }} 个区域</el-tag>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索区域名称 / 编码..."
          clearable
          :prefix-icon="Search"
          class="search-input-wide"
        />
        <el-select v-model="levelFilter" placeholder="区域级别" clearable class="level-filter">
          <el-option label="全部" value="" />
          <el-option label="省份" value="1" />
          <el-option label="城市" value="2" />
          <el-option label="区县" value="3" />
          <el-option label="乡镇" value="4" />
        </el-select>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon> 添加区域
        </el-button>
      </div>
    </header>

    <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="filteredRegions"
        stripe
        border
        class="form-full-width"
        max-height="calc(100vh - 140px)"
        row-key="id"
        default-expand-all
      >
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="regionName" label="区域名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="regionCode" label="区域编码" width="160" show-overflow-tooltip />
        <el-table-column prop="parentCode" label="上级编码" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span :style="{ color: row.parentCode ? undefined : 'var(--el-text-color-placeholder)' }">
              {{ row.parentCode || '— 顶级 —' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="级别" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.level)" size="small">
              {{ getLevelLabel(row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="中心坐标" width="200" align="center">
          <template #default="{ row }">
            <span v-if="row.longitude != null && row.latitude != null" class="coord-text">
              {{ row.longitude.toFixed(4) }}, {{ row.latitude.toFixed(4) }}
            </span>
            <span v-else class="coord-empty">未设置</span>
          </template>
        </el-table-column>
        <el-table-column prop="bounds" label="边界范围" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.bounds || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" align="center" />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-popconfirm
              title="确认删除该区域? 子区域将受到影响"
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
      :title="isEditing ? '编辑区域' : '添加区域'"
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
        <el-form-item label="区域名称" prop="regionName">
          <el-input v-model="form.regionName" placeholder="如: 运城市" maxlength="100" />
        </el-form-item>
        <el-form-item label="区域编码" prop="regionCode">
          <el-input v-model="form.regionCode" placeholder="如: 140800" maxlength="50" />
        </el-form-item>
        <el-form-item label="上级编码" prop="parentCode">
          <el-input v-model="form.parentCode" placeholder="上级区域编码（顶级留空）" maxlength="50" />
        </el-form-item>
        <el-form-item label="级别" prop="level">
          <el-select v-model="form.level" placeholder="选择级别" class="form-full-width">
            <el-option label="省份" :value="1" />
            <el-option label="城市" :value="2" />
            <el-option label="区县" :value="3" />
            <el-option label="乡镇" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="中心经度" prop="longitude">
          <el-input-number
            v-model="form.longitude"
            :precision="6"
            :min="-180"
            :max="180"
            placeholder="如: 110.932000"
            class="form-full-width"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="中心纬度" prop="latitude">
          <el-input-number
            v-model="form.latitude"
            :precision="6"
            :min="-90"
            :max="90"
            placeholder="如: 35.124000"
            class="form-full-width"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="边界范围" prop="bounds">
          <el-input
            v-model="form.bounds"
            type="textarea"
            :rows="2"
            placeholder="如: POLYGON((110.0 34.5, 112.0 34.5, 112.0 36.0, 110.0 36.0, 110.0 34.5))"
            maxlength="2000"
          />
        </el-form-item>
        <el-form-item label="中心坐标描述" prop="centerCoord">
          <el-input v-model="form.centerCoord" placeholder="中心坐标文字描述" maxlength="200" />
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
export default { name: 'RegionsView' }
</script>
<script setup>
import { ref, computed } from 'vue'
import { Plus, Edit, Delete, ArrowLeft, Search } from '@element-plus/icons-vue'
import { regionAPI } from '@/utils/request'
import { useCrudTable } from '@/composables/useCrudTable'

// ── 组件专属状态 ────────────────────────────────────────────
const levelFilter = ref('')

// ── Composable — 通用 CRUD ──────────────────────────────────
const {
  loading, saving, items: regions, searchQuery,
  dialogVisible, isEditing, editingId, formRef, form,
  filteredItems: baseFiltered,
  showCreateDialog, showEditDialog, handleSave, handleDelete, fetchItems,
} = useCrudTable({
  api: regionAPI,
  entityName: '区域',
  initialForm: {
    regionName: '', regionCode: '', parentCode: '',
    level: null, longitude: null, latitude: null,
    bounds: '', centerCoord: '',
  },
  searchFields: ['regionName', 'regionCode'],
  autoFetch: true,
})

// ── 组合搜索（前端搜索 + 级别过滤器） ────────────────────────
const filteredRegions = computed(() => {
  let result = baseFiltered.value
  const level = levelFilter.value
  if (level) {
    result = result.filter(r => r.level === Number(level))
  }
  return result
})

// ── 表单验证规则 ────────────────────────────────────────────
const formRules = {
  regionName: [{ required: true, message: '请输入区域名称', trigger: 'blur' }],
  regionCode: [{ required: true, message: '请输入区域编码', trigger: 'blur' }],
}

// ── 工具函数 ────────────────────────────────────────────────
function getLevelLabel(level) {
  const map = { 1: '省份', 2: '城市', 3: '区县', 4: '乡镇' }
  return map[level] || level
}

function getLevelTagType(level) {
  const map = { 1: 'danger', 2: 'warning', 3: 'success', 4: 'info' }
  return map[level] || ''
}
</script>

<style scoped>
.regions-page {
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

.coord-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--primary-color, #00d4ff);
}

.coord-empty {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}

/* ── 布局辅助类 ──────────────────────────────────────────── */
.form-full-width { width: 100%; }
.search-input-wide { width: 280px; }
.level-filter { width: 140px; }
</style>
