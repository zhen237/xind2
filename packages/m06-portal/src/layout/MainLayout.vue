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

const isDashboard = computed(() => false)

const goBackHome = () => {
  router.push('/')
}

const iconMap = {
  system: markRaw(Setting),
  simulation: markRaw(Bell),
  design: markRaw(Box),
  delivery: markRaw(CircleCheck),
  twin: markRaw(Monitor)
}

const quickModules = reactive([
  {
    icon: Monitor,
    title: '实时监控',
    desc: '查看设备运行状态',
    bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    menuCode: 'twin_monitor'
  },
  {
    icon: Bell,
    title: '告警管理',
    desc: '处理设备告警信息',
    bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    menuCode: 'twin_alert'
  },
  {
    icon: CircleCheck,
    title: '工单管理',
    desc: '处理运维工单',
    bgColor: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    menuCode: 'delivery_order'
  },
  {
    icon: Box,
    title: '三维场景设计',
    desc: 'BIM基站三维建模',
    bgColor: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    menuCode: 'design_collision'
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
  const menu = findMenuByCode(userStore.menus, menuCode)
  if (menu && menu.iframeUrl) {
    currentUrl.value = menu.iframeUrl
  } else {
    currentUrl.value = ''
  }
  
  const routeMap = {
    'design_collision': '/m03/design',
    'design_design': '/m03/design',
    'twin_monitor': '/m03/station3d',
    'twin_alert': '/m03/coverage',
    'delivery_order': '/m04/work-order',
    'delivery_doc': '/m04/project',
    'delivery_acceptance': '/m04/acceptance',
    'simulation_plan': '/m03/coverage',
    'simulation_analysis': '/m03/coverage',
    'system_user': '/m03/project',
    'system_role': '/m03/project'
  }
  
  if (routeMap[menuCode]) {
    router.push(routeMap[menuCode])
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
          menuCode: 'system',
          menuName: '系统管理(M01)',
          children: [
            { menuCode: 'system_user', menuName: '用户管理', iframeUrl: null },
            { menuCode: 'system_role', menuName: '角色管理', iframeUrl: null }
          ]
        },
        {
          menuCode: 'simulation',
          menuName: '网络规划与仿真(M02)',
          children: [
            { menuCode: 'simulation_plan', menuName: '站点规划', iframeUrl: null },
            { menuCode: 'simulation_analysis', menuName: '覆盖分析', iframeUrl: null }
          ]
        },
        {
          menuCode: 'design',
          menuName: 'BIM+GIS设计(M03)',
          children: [
            { menuCode: 'design_collision', menuName: '三维场景设计', iframeUrl: null }
          ]
        },
        {
          menuCode: 'delivery',
          menuName: '数智化交付(M04)',
          children: [
            { menuCode: 'delivery_doc', menuName: '文档管理', iframeUrl: null },
            { menuCode: 'delivery_order', menuName: '工单管理', iframeUrl: null },
            { menuCode: 'delivery_acceptance', menuName: '验收管理', iframeUrl: null }
          ]
        },
        {
          menuCode: 'twin',
          menuName: '数字孪生(M05)',
          children: [
            { menuCode: 'twin_monitor', menuName: '实时监控', iframeUrl: null },
            { menuCode: 'twin_alert', menuName: '告警管理', iframeUrl: null }
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
  background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
  border-bottom: 1px solid rgba(167, 139, 250, 0.2);
  height: 64px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  background: rgba(167, 139, 250, 0.1) !important;
  border: 1px solid rgba(167, 139, 250, 0.3) !important;
  color: #e2e8f0 !important;
  transition: all 0.3s;
  padding: 8px 16px;
  font-weight: 500;
}

.back-btn:hover {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%) !important;
  border-color: transparent !important;
  color: white !important;
  transform: translateX(-4px);
  box-shadow: 0 4px 15px rgba(167, 139, 250, 0.4);
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
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 20px rgba(167, 139, 250, 0.4);
}

.logo-icon svg {
  width: 24px;
  height: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #e2e8f0;
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
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid rgba(167, 139, 250, 0.2);
}

.user-info:hover {
  background: rgba(167, 139, 250, 0.2);
  box-shadow: 0 0 20px rgba(167, 139, 250, 0.3);
}

.user-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.username {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.role {
  font-size: 12px;
  color: #94a3b8;
}

.main-container {
  height: calc(100vh - 64px);
  background: #0f172a;
}

.sidebar {
  background: linear-gradient(180deg, #1e1b4b 0%, #0f172a 100%);
  border-right: 1px solid rgba(167, 139, 250, 0.2);
  position: relative;
  transition: width 0.3s;
}

.collapse-btn {
  position: absolute;
  top: 12px;
  right: -12px;
  width: 24px;
  height: 24px;
  background: #1e1b4b;
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.3s;
  color: #a78bfa;
}

.collapse-btn:hover {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%);
  color: white;
  border-color: #a78bfa;
  box-shadow: 0 0 15px rgba(167, 139, 250, 0.5);
}

.sidebar-menu {
  border-right: none;
  padding-top: 50px;
}

.sidebar-menu :deep(.el-menu) {
  background: transparent !important;
  color: #cbd5e1;
  border: none;
}

.sidebar-menu :deep(.el-menu-item),
.sidebar-menu :deep(.el-sub-menu__title) {
  color: #cbd5e1;
  transition: all 0.3s;
  background: transparent !important;
}

.sidebar-menu :deep(.el-menu-item:hover),
.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(167, 139, 250, 0.15) !important;
  color: #a78bfa;
}

.sidebar-menu :deep(.el-menu-item.is-active),
.sidebar-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  background: linear-gradient(90deg, rgba(167, 139, 250, 0.2) 0%, transparent 100%) !important;
  color: #a78bfa;
  border-right: 3px solid #a78bfa;
}

.sidebar-menu :deep(.el-sub-menu__icon-arrow) {
  color: #94a3b8;
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
  background: rgba(15, 23, 42, 0.95) !important;
}

.sidebar-menu :deep(.el-menu--collapse) {
  background: transparent !important;
}

.main-content {
  background: #0f172a;
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
  color: #e2e8f0;
  margin-bottom: 8px;
}

.dashboard-header p {
  color: #94a3b8;
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
  border: 1px solid rgba(167, 139, 250, 0.2);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(167, 139, 250, 0.3);
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.orange {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.green {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-icon.purple {
  background: linear-gradient(135deg, #a78bfa 0%, #818cf8 100%);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #e2e8f0;
}

.stat-label {
  font-size: 14px;
  color: #94a3b8;
}

.modules-grid {
  margin-bottom: 30px;
}

.modules-grid h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 16px;
}

.module-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.module-card {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(167, 139, 250, 0.2);
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(167, 139, 250, 0.3);
}

.module-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.3);
}

.module-info h4 {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.module-info p {
  font-size: 12px;
  color: #94a3b8;
}

.recent-section {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(167, 139, 250, 0.2);
}

.recent-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 16px;
}

.content-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
