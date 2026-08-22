<template>
  <div class="page-user-management">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon> 新增用户
      </el-button>
    </div>

    <!-- Search Bar -->
    <div class="search-bar">
      <el-input v-model="searchText" placeholder="搜索用户名/真实姓名" clearable style="width: 280px" prefix-icon="Search" />
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 140px">
        <el-option label="启用" value="active" />
        <el-option label="禁用" value="disabled" />
      </el-select>
    </div>

    <!-- Data Table -->
    <el-table :data="filteredUsers" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="realName" label="真实姓名" width="120" />
      <el-table-column prop="roleName" label="角色" width="140">
        <template #default="{ row }">
          <el-tag size="small" :type="row.roleType === 'admin' ? 'danger' : 'primary'">{{ row.roleName }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="subTopic" label="负责模块" width="160">
        <template #default="{ row }">
          <span v-if="row.subTopic">{{ row.subTopic }}</span>
          <span v-else style="color: #94a3b8">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small" effect="plain">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="lastLoginTime" label="最后登录" width="170">
        <template #default="{ row }">
          {{ row.lastLoginTime || '从未登录' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small">编辑</el-button>
          <el-button link type="warning" size="small">重置密码</el-button>
          <el-button link :type="row.status === 'active' ? 'danger' : 'success'" size="small">
            {{ row.status === 'active' ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="users.length"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
      />
    </div>

    <!-- Stats Cards -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-number">{{ users.length }}</span>
        <span class="stat-label">总用户数</span>
      </div>
      <div class="stat-card">
        <span class="stat-number stat-active">{{ activeCount }}</span>
        <span class="stat-label">已启用</span>
      </div>
      <div class="stat-card">
        <span class="stat-number stat-admin">{{ adminCount }}</span>
        <span class="stat-label">管理员</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const searchText = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// Mock data — 对应项目团队子赛题
const users = ref([
  { id: 1, username: 'zhen237', realName: '', roleName: '管理员 / S1', roleType: 'admin', subTopic: 'S1 智能设计', status: 'active', lastLoginTime: '2026-07-16 12:29' },
  { id: 2, username: 'ren_s2', realName: '', roleName: '成员 / S2', roleType: 'user', subTopic: 'S2 数据融合', status: 'active', lastLoginTime: '2026-07-15 18:30' },
  { id: 3, username: 'w0722', realName: '', roleName: '成员 / S3', roleType: 'user', subTopic: 'S3 设计审查', status: 'active', lastLoginTime: '2026-07-16 09:00' },
  { id: 4, username: 'pang_s4', realName: '', roleName: '成员 / S4', roleType: 'user', subTopic: 'S4 施工指令', status: 'active', lastLoginTime: '2026-07-14 16:20' },
  { id: 5, username: 'li_s5', realName: '', roleName: '成员 / S5', roleType: 'user', subTopic: 'S5 施工监管', status: 'active', lastLoginTime: '2026-07-15 11:45' },
  { id: 6, username: 'guest', realName: '访客账号', roleName: '访客', roleType: 'guest', subTopic: '', status: 'disabled', lastLoginTime: null },
])

const filteredUsers = computed(() => {
  let list = users.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(u =>
      u.username.toLowerCase().includes(q) ||
      (u.realName || '').toLowerCase().includes(q)
    )
  }
  if (filterStatus.value) {
    list = list.filter(u => u.status === filterStatus.value)
  }
  return list
})

const activeCount = computed(() => users.value.filter(u => u.status === 'active').length)
const adminCount = computed(() => users.value.filter(u => u.roleType === 'admin').length)

const showAddDialog = () => {
  // TODO: 弹窗新增用户（对接后端 API）
}
</script>

<style scoped>
.page-user-management {
  padding: 24px;
  min-height: 100%;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.stats-row {
  display: flex;
  gap: 24px;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}
.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 24px;
  background: white;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  min-width: 120px;
}
.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
}
.stat-active { color: #22c55e; }
.stat-admin { color: #ef4444; }
.stat-label {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}
</style>
