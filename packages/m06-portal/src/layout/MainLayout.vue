<template>
  <div class="layout-wrapper">
    <el-container>
      <!-- Header -->
      <el-header class="header">
        <div class="header-left">
          <el-button
            v-if="route.path !== '/'"
            class="back-btn"
            @click="goBackHome"
          >
            <el-icon :size="18"><ArrowLeft /></el-icon>
            <span>返回主页</span>
          </el-button>
          <div class="logo">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <span class="logo-text">通信基建数智化平台</span>
          </div>
        </div>

        <div class="header-right">
          <div class="header-actions">
            <el-button :icon="Bell" circle />
            <el-button :icon="Setting" circle />
          </div>
          <el-dropdown trigger="click">
            <div class="user-info">
              <el-avatar :size="32" :icon="User" />
              <div class="user-text">
                <span class="username">{{ userStore.userInfo?.realName || userStore.userInfo?.username }}</span>
                <span class="role">管理员</span>
              </div>
              <el-icon class="arrow"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><Close /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container class="main-container">
        <!-- Sidebar -->
        <el-aside :width="isCollapse ? '64px' : '240px'" class="sidebar">
          <div class="collapse-btn" @click="toggleCollapse">
            <el-icon :size="20">
              <component :is="isCollapse ? 'DArrowRight' : 'DArrowLeft'" />
            </el-icon>
          </div>

          <el-menu
            :default-active="activeMenu"
            :collapse="isCollapse"
            class="sidebar-menu"
            @select="handleMenuSelect"
          >
            <template v-for="menu in userStore.menus" :key="menu.menuCode">
              <el-sub-menu v-if="menu.children && menu.children.length > 0" :index="menu.menuCode">
                <template #title>
                  <el-icon :size="20"><component :is="getMenuIcon(menu.menuCode)" /></el-icon>
                  <span>{{ menu.menuName }}</span>
                </template>
                <el-menu-item
                  v-for="child in menu.children"
                  :key="child.menuCode"
                  :index="child.menuCode"
                >
                  <span>{{ child.menuName }}</span>
                </el-menu-item>
              </el-sub-menu>
              <el-menu-item v-else :index="menu.menuCode">
                <el-icon :size="20"><component :is="getMenuIcon(menu.menuCode)" /></el-icon>
                <span>{{ menu.menuName }}</span>
              </el-menu-item>
            </template>
          </el-menu>
        </el-aside>

        <!-- Main Content -->
        <el-main class="main-content">
          <!-- Welcome Dashboard (when at root path) -->
          <div v-if="isDashboard" class="dashboard">
            <div class="dashboard-header">
              <h2>欢迎回来，{{ userStore.userInfo?.realName || '管理员' }}！</h2>
              <p>选择一个菜单开始工作</p>
            </div>

            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-icon blue">
                  <el-icon :size="32"><component :is="Monitor" /></el-icon>
                </div>
                <div class="stat-info">
                  <span class="stat-value">156</span>
                  <span class="stat-label">在线设备</span>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon orange">
                  <el-icon :size="32"><component :is="Bell" /></el-icon>
                </div>
                <div class="stat-info">
                  <span class="stat-value">23</span>
                  <span class="stat-label">待处理告警</span>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon green">
                  <el-icon :size="32"><component :is="CircleCheck" /></el-icon>
                </div>
                <div class="stat-info">
                  <span class="stat-value">89</span>
                  <span class="stat-label">已完成工单</span>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon purple">
                  <el-icon :size="32"><component :is="Box" /></el-icon>
                </div>
                <div class="stat-info">
                  <span class="stat-value">12</span>
                  <span class="stat-label">设计中项目</span>
                </div>
              </div>
            </div>

            <div class="modules-grid">
              <h3>快捷入口</h3>
              <div class="module-cards">
                <div class="module-card" v-for="module in quickModules" :key="module.title" @click="quickNavigate(module.menuCode)">
                  <div class="module-icon" :style="{ background: module.bgColor }">
                    <el-icon :size="28"><component :is="module.icon" /></el-icon>
                  </div>
                  <div class="module-info">
                    <h4>{{ module.title }}</h4>
                    <p>{{ module.desc }}</p>
                  </div>
                </div>
              </div>
            </div>

            <div class="recent-section">
              <h3>最近告警</h3>
              <el-table :data="recentAlerts" stripe>
                <el-table-column prop="time" label="时间" width="180" />
                <el-table-column prop="device" label="设备" width="150" />
                <el-table-column prop="content" label="告警内容" />
                <el-table-column prop="level" label="级别" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getLevelType(row.level)" size="small">
                      {{ getLevelText(row.level) }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- iframe content -->
          <iframe
            v-else-if="currentUrl"
            ref="iframeRef"
            :src="currentUrl"
            class="content-iframe"
            @load="onIframeLoad"
          />

          <!-- Child route content (m03 pages) -->
          <router-view v-else />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, markRaw, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  Menu as MenuIcon,
  User as User,
  Setting as Setting,
  Bell as Bell,
  Monitor as Monitor,
  Box as Box,
  CircleCheck as CircleCheck,
  Connection as Connection,
  DArrowLeft,
  DArrowRight,
  ArrowDown,
  ArrowLeft,
  Close
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const isCollapse = ref(false)
const activeMenu = ref('')
const currentUrl = ref('')
const iframeRef = ref(null)

const isDashboard = computed(() => route.path === '/' && !currentUrl.value)

// 子模块前端地址 —— 从 .env 读取，留空则用同源路径
const MODULE_BASE = {
  m01: import.meta.env.VITE_FE_M01 || '/modules/m01',
  m02: import.meta.env.VITE_FE_M02 || '/modules/m02',
  m03: import.meta.env.VITE_FE_M03 || '/modules/m03',
  m04: import.meta.env.VITE_FE_M04 || '/modules/m04',
  m05: import.meta.env.VITE_FE_M05 || '/modules/m05'
}

const goBackHome = () => {
  router.push('/')
}

const iconMap = {
  design: markRaw(Box),
  review: markRaw(Monitor),
  instruction: markRaw(CircleCheck),
  supervision: markRaw(Bell),
  system: markRaw(Setting)
}

const quickModules = reactive([
  {
    icon: Box,
    title: '智能设计',
    desc: '子赛题1 - 基站智能辅助设计',
    bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    menuCode: 'design_3d'
  },
  {
    icon: Monitor,
    title: '智能审查',
    desc: '子赛题3 - 安全规范审查',
    bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    menuCode: 'review_safety'
  },
  {
    icon: CircleCheck,
    title: 'BOM生成',
    desc: '子赛题4 - 施工指令转化',
    bgColor: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    menuCode: 'instruction_bom'
  },
  {
    icon: Bell,
    title: '施工监管',
    desc: '子赛题5 - 施工过程监管',
    bgColor: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    menuCode: 'supervision_monitor'
  }
])

const recentAlerts = reactive([
  { time: '2026-05-20 14:32:15', device: 'ST001-空调', content: '温度超过阈值', level: 2 },
  { time: '2026-05-20 14:25:03', device: 'ST002-电源', content: '电源模块故障', level: 1 },
  { time: '2026-05-20 13:18:47', device: 'ST001-温感', content: '环境温度异常', level: 3 },
  { time: '2026-05-20 11:05:22', device: 'ST003-门禁', content: '门磁信号丢失', level: 4 }
])

const getMenuIcon = (menuCode) => {
  const prefix = menuCode.split('_')[0]
  return iconMap[prefix] || Box
}

const findMenuByCode = (menuList, code) => {
  for (const menu of menuList) {
    if (menu.menuCode === code) return menu
    if (menu.children) {
      const found = findMenuByCode(menu.children, code)
      if (found) return found
    }
  }
  return null
}

const handleMenuSelect = (menuCode) => {
  activeMenu.value = menuCode
  
  // 子应用路由映射 —— 使用 MODULE_BASE 拼接，端口变化只改 MODULE_BASE
  const iframeUrlMap = {
    'design_3d': `${MODULE_BASE.m03}/#/design-visualization`,
    'design_layout': `${MODULE_BASE.m03}/#/design`,
    'design_coverage': `${MODULE_BASE.m03}/#/coverage`,
    'review_safety': `${MODULE_BASE.m04}/#/work-order`,
    'review_conflict': `${MODULE_BASE.m04}/#/work-order`,
    'review_report': `${MODULE_BASE.m04}/#/work-order`,
    'instruction_bom': `${MODULE_BASE.m04}/#/delivery`,
    'instruction_process': `${MODULE_BASE.m04}/#/construction`,
    'instruction_manage': `${MODULE_BASE.m04}/#/work-order`,
    'supervision_monitor': `${MODULE_BASE.m04}/#/project`,
    'supervision_violation': `${MODULE_BASE.m04}/#/construction`,
    'supervision_acceptance': `${MODULE_BASE.m04}/#/acceptance`,
    'system_user': `${MODULE_BASE.m01}/#/user`,
    'system_role': `${MODULE_BASE.m01}/#/role`
  }
  
  if (iframeUrlMap[menuCode]) {
    currentUrl.value = iframeUrlMap[menuCode]
  } else {
    // 如果没有配置，再尝试从菜单数据读取
    const menu = findMenuByCode(userStore.menus, menuCode)
    if (menu && menu.iframeUrl) {
      currentUrl.value = menu.iframeUrl
    } else {
      currentUrl.value = ''
    }
  }
}

const quickNavigate = (menuCode) => {
  handleMenuSelect(menuCode)
}

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}

const onIframeLoad = () => {
  if (iframeRef.value && userStore.token) {
    iframeRef.value.contentWindow.postMessage(
      { type: 'TOKEN', token: userStore.token },
      '*'
    )
  }
}

const getLevelType = (level) => {
  const types = { 1: 'danger', 2: 'warning', 3: 'info', 4: 'success' }
  return types[level] || 'info'
}

const getLevelText = (level) => {
  const texts = { 1: '紧急', 2: '重要', 3: '警告', 4: '提示' }
  return texts[level] || '未知'
}

watch(currentUrl, () => {
  setTimeout(() => {
    onIframeLoad()
  }, 100)
})

onMounted(async () => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
  if (!userStore.menus || userStore.menus.length === 0) {
    try {
      await userStore.fetchMenus()
    } catch (e) {
      // 后端不可用时使用静态菜单作为后备
    }
    if (!userStore.menus || userStore.menus.length === 0) {
      userStore.menus = [
        {
          menuCode: 'design',
          menuName: '智能设计',
          children: [
            { menuCode: 'design_3d', menuName: '三维场景设计', iframeUrl: null },
            { menuCode: 'design_layout', menuName: '基站布局设计', iframeUrl: null },
            { menuCode: 'design_coverage', menuName: '覆盖分析', iframeUrl: null }
          ]
        },
        {
          menuCode: 'review',
          menuName: '智能审查',
          children: [
            { menuCode: 'review_safety', menuName: '安全规范审查', iframeUrl: null },
            { menuCode: 'review_conflict', menuName: '资源冲突检测', iframeUrl: null },
            { menuCode: 'review_report', menuName: '审查报告', iframeUrl: null }
          ]
        },
        {
          menuCode: 'instruction',
          menuName: '施工指令',
          children: [
            { menuCode: 'instruction_bom', menuName: 'BOM生成', iframeUrl: null },
            { menuCode: 'instruction_process', menuName: '工艺要求', iframeUrl: null },
            { menuCode: 'instruction_manage', menuName: '施工指令管理', iframeUrl: null }
          ]
        },
        {
          menuCode: 'supervision',
          menuName: '施工监管',
          children: [
            { menuCode: 'supervision_monitor', menuName: '实时监控', iframeUrl: null },
            { menuCode: 'supervision_violation', menuName: '违章识别', iframeUrl: null },
            { menuCode: 'supervision_acceptance', menuName: '验收管理', iframeUrl: null }
          ]
        },
        {
          menuCode: 'system',
          menuName: '系统管理',
          children: [
            { menuCode: 'system_user', menuName: '用户管理', iframeUrl: null },
            { menuCode: 'system_role', menuName: '角色管理', iframeUrl: null }
          ]
        }
      ]
    }
  }
})
</script>

<style scoped>
.layout-wrapper {
  height: 100vh;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  background: #1e293b;
  border-bottom: 1px solid #334155;
  height: 64px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  background: rgba(37, 99, 235, 0.1) !important;
  border: 1px solid rgba(37, 99, 235, 0.3) !important;
  color: #94a3b8 !important;
  transition: all 0.3s;
  padding: 8px 16px;
  font-weight: 500;
}

.back-btn:hover {
  background: #2563eb !important;
  border-color: transparent !important;
  color: white !important;
  transform: translateX(-4px);
}

.back-btn .el-icon {
  margin-right: 6px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: #2563eb;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.logo-icon svg {
  width: 24px;
  height: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #f8fafc;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid rgba(37, 99, 235, 0.2);
}

.user-info:hover {
  background: rgba(37, 99, 235, 0.2);
}

.user-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.username {
  font-size: 14px;
  font-weight: 600;
  color: #f8fafc;
}

.role {
  font-size: 12px;
  color: #94a3b8;
}

.main-container {
  height: calc(100vh - 64px);
  background: #f8fafc;
}

.sidebar {
  background: #1e293b;
  border-right: 1px solid #334155;
  position: relative;
  transition: width 0.3s;
}

.collapse-btn {
  position: absolute;
  top: 12px;
  right: -12px;
  width: 24px;
  height: 24px;
  background: #1e293b;
  border: 1px solid #475569;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.3s;
  color: #94a3b8;
}

.collapse-btn:hover {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
}

.sidebar-menu {
  border-right: none;
  padding-top: 50px;
}

.sidebar-menu :deep(.el-menu) {
  background: transparent !important;
  color: #94a3b8;
  border: none;
}

.sidebar-menu :deep(.el-menu-item),
.sidebar-menu :deep(.el-sub-menu__title) {
  color: #94a3b8;
  transition: all 0.3s;
  background: transparent !important;
}

.sidebar-menu :deep(.el-menu-item:hover),
.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(37, 99, 235, 0.15) !important;
  color: #2563eb;
}

.sidebar-menu :deep(.el-menu-item.is-active),
.sidebar-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  background: rgba(37, 99, 235, 0.1) !important;
  color: #2563eb;
  border-right: 3px solid #2563eb;
}

.sidebar-menu :deep(.el-sub-menu__icon-arrow) {
  color: #64748b;
}

.sidebar-menu :deep(.el-menu-item-group) {
  background: transparent !important;
}

.sidebar-menu :deep(.el-menu-item-group__title) {
  color: #64748b;
  background: transparent !important;
}

.sidebar-menu :deep(.el-sub-menu.is-opened .el-sub-menu__title) {
  background: transparent !important;
}

.sidebar-menu :deep(.el-sub-menu .el-menu) {
  background: #1e293b !important;
}

.sidebar-menu :deep(.el-menu--collapse) {
  background: transparent !important;
}

.main-content {
  background: #f8fafc;
  padding: 0;
  overflow: auto;
}

.dashboard {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.dashboard-header {
  margin-bottom: 24px;
}

.dashboard-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
}

.dashboard-header p {
  color: #64748b;
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
  border: 1px solid #e2e8f0;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.blue {
  background: #2563eb;
}

.stat-icon.orange {
  background: #f59e0b;
}

.stat-icon.green {
  background: #10b981;
}

.stat-icon.purple {
  background: #8b5cf6;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
}

.modules-grid {
  margin-bottom: 30px;
}

.modules-grid h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
}

.module-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.module-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.module-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.module-info h4 {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.module-info p {
  font-size: 12px;
  color: #64748b;
}

.recent-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.recent-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
}

.content-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
