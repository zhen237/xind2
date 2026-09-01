<template>
  <div class="page-role-management">
    <div class="page-header">
      <h2>角色管理</h2>
      <el-button type="primary" @click="showAddDialog" size="default">
        <el-icon><Plus /></el-icon> 新增角色
      </el-button>
    </div>

    <!-- Roles Table -->
    <el-table :data="roles" stripe style="width: 100%">
      <el-table-column prop="roleCode" label="角色编码" width="140" />
      <el-table-column prop="roleName" label="角色名称" width="160" />
      <el-table-column prop="description" label="描述" min-width="200" />
      <el-table-column prop="userCount" label="关联用户数" width="110" align="center">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.userCount }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small" effect="plain">
            {{ row.status === 'enabled' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small">权限配置</el-button>
          <el-button link type="warning" size="small">编辑</el-button>
          <el-button link :type="row.status === 'enabled' ? 'danger' : 'success'" size="small">
            {{ row.status === 'enabled' ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Permission Matrix -->
    <div class="section-title-bar">
      <h3>权限矩阵</h3>
    </div>
    <div class="permission-matrix">
      <table class="matrix-table">
        <thead>
          <tr>
            <th class="th-role">角色 / 权限</th>
            <th v-for="p in permissions" :key="p.code">{{ p.name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in roles" :key="r.roleCode">
            <td class="td-role">
              <span class="role-name" :class="'role-' + r.roleCode">{{ r.roleName }}</span>
            </td>
            <td v-for="p in permissions" :key="p.code" class="td-check">
              <span v-if="hasPermission(r, p.code)" class="check-yes">✓</span>
              <span v-else class="check-no">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Permission Legend -->
    <div class="legend-row">
      <span class="legend-item"><span class="check-yes">✓</span> 有此权限</span>
      <span class="legend-item"><span class="check-no">—</span> 无此权限</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'

const roles = ref([
  {
    roleCode: 'admin',
    roleName: '系统管理员',
    description: '拥有全部模块的全部权限，负责系统配置与用户管理',
    userCount: 1,
    status: 'enabled',
    perms: ['*']
  },
  {
    roleCode: 's1_leader',
    roleName: 'S1 智能设计负责人',
    description: 'S1 子赛题（面向专业GIS平台的通信工程智能辅助设计）的模块管理权限',
    userCount: 1,
    status: 'enabled',
    perms: ['design:view', 'design:edit', 'design:export', 's1:manage', 'system:user:view', 'progress:view']
  },
  {
    roleCode: 's2_leader',
    roleName: 'S2 数据融合负责人',
    description: 'S2 子赛题（多源异构工程数据融合）的模块管理权限',
    userCount: 1,
    status: 'enabled',
    perms: ['fusion:view', 'fusion:edit', 'fusion:upload', 's2:manage', 'progress:view']
  },
  {
    roleCode: 's3_leader',
    roleName: 'S3 设计审查负责人',
    description: 'S3 子赛题（基于行业标准的设计智能审查）的模块管理权限',
    userCount: 1,
    status: 'enabled',
    perms: ['review:view', 'review:run', 'review:report', 's3:manage', 'progress:view']
  },
  {
    roleCode: 's4_leader',
    roleName: 'S4 施工指令负责人',
    description: 'S4 子赛题（设计成果向施工指令的自动转化）的模块管理权限',
    userCount: 1,
    status: 'enabled',
    perms: ['instruction:view', 'instruction:bom', 'instruction:manage', 's4:manage', 'progress:view']
  },
  {
    roleCode: 's5_leader',
    roleName: 'S5 施工监管负责人',
    description: 'S5 子赛题（施工过程智能监管）的模块管理权限',
    userCount: 1,
    status: 'enabled',
    perms: ['supervision:view', 'supervision:monitor', 'supervision:report', 's5:manage', 'progress:view']
  },
  {
    roleCode: 'guest',
    roleName: '访客',
    description: '只读访问部分公开页面，无操作权限',
    userCount: 0,
    status: 'disabled',
    perms: ['design:view', 'progress:view']
  },
])

const permissions = ref([
  { code: 'design:view', name: '设计查看' },
  { code: 'design:edit', name: '设计编辑' },
  { code: 'fusion:edit', name: '融合操作' },
  { code: 'review:run', name: '执行审查' },
  { code: 'instruction:bom', name: 'BOM生成' },
  { code: 'supervision:monitor', name: '实时监控' },
  { code: 'system:user:view', name: '用户查看' },
  { code: 'system:role:view', name: '角色查看' },
  { code: 'progress:view', name: '进度查看' },
])

const hasPermission = (role, permCode) => {
  return role.perms.includes('*') || role.perms.includes(permCode)
}

const showAddDialog = () => {
  // TODO: 弹窗新增角色
}
</script>

<style scoped>
.page-role-management {
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

.section-title-bar {
  margin-top: 32px;
  margin-bottom: 16px;
}
.section-title-bar h3 {
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin: 0;
}

.permission-matrix {
  overflow-x: auto;
  background: white;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}
.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.matrix-table th {
  background: #f8fafc;
  padding: 10px 12px;
  text-align: center;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}
.matrix-table td {
  padding: 8px 12px;
  text-align: center;
  border-bottom: 1px solid #f1f5f9;
}
.th-role {
  text-align: left !important;
  position: sticky;
  left: 0;
  background: #f8fafc;
  z-index: 2;
  min-width: 150px;
}
.td-role {
  text-align: left !important;
  background: white;
  position: sticky;
  left: 0;
  z-index: 1;
}
.role-name {
  font-weight: 600;
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 6px;
}
.role-admin { background: rgba(239,68,68,0.1); color: #dc2626; }
.role-s1_leader { background: rgba(59,130,246,0.1); color: #2563eb; }
.role-s2_leader { background: rgba(16,185,129,0.1); color: #059669; }
.role-s3_leader { background: rgba(245,158,11,0.1); color: #d97706; }
.role-s4_leader { background: rgba(139,92,246,0.1); color: #7c3aed; }
.role-s5_leader { background: rgba(236,72,153,0.1); color: #db2777; }
.role-guest { background: #f1f5f9; color: #94a3b8; }

.check-yes {
  color: #22c55e;
  font-weight: 700;
  font-size: 15px;
}
.check-no {
  color: #cbd5e1;
}

.legend-row {
  display: flex;
  gap: 24px;
  margin-top: 12px;
  justify-content: flex-end;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
}
</style>
