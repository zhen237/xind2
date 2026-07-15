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
                  <span v-if="getOwnerTag(menu.menuCode)" class="owner-tag" :class="'tag-' + getOwnerTag(menu.menuCode)?.s">{{ getOwnerTag(menu.menuCode)?.label }}</span>
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
              <h2>工作台</h2>
              <p>{{ userStore.userInfo?.realName || '管理员' }}，欢迎回来</p>
            </div>

            <div class="modules-grid">
              <div class="module-cards">
                <div class="module-card" v-for="module in quickModules" :key="module.title" @click="quickNavigate(module.menuCode)">
                  <div class="module-icon" :style="{ background: module.bgColor }">
                    <el-icon :size="24"><component :is="module.icon" /></el-icon>
                  </div>
                  <div class="module-info">
                    <h4>{{ module.title }}</h4>
                    <p>{{ module.desc }}</p>
                    <span class="module-owner">{{ module.owner }}</span>
                  </div>
                </div>
              </div>
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
  m05: import.meta.env.VITE_FE_M05 || '/modules/m05',
  // 新赛题模块（未配置时为空字符串，iframeUrlMap 会回退到 m04）
  s2: import.meta.env.VITE_FE_S2 || '',
  s3: import.meta.env.VITE_FE_S3 || '',
  s4: import.meta.env.VITE_FE_S4 || '',
  s5: import.meta.env.VITE_FE_S5 || ''
}

// 智能路由：如果 sN 已配置则用 sN，否则回退到 m04（渐进迁移）
const moduleUrl = (subTopic, m04Fallback) => {
  const sUrl = MODULE_BASE[subTopic]
  return sUrl ? `${sUrl}/#/${m04Fallback}` : `${MODULE_BASE.m04}/#/${m04Fallback}`
}

const goBackHome = () => {
  router.push('/')
}

const iconMap = {
  design: markRaw(Box),
  fusion: markRaw(Connection),
  review: markRaw(Monitor),
  instruction: markRaw(CircleCheck),
  supervision: markRaw(Bell),
  system: markRaw(Setting)
}

// S赛题编号 + 负责人标签
const ownerTagMap = {
  design:   { s: 's1', label: 'S1 高' },
  fusion:   { s: 's2', label: 'S2 任' },
  review:   { s: 's3', label: 'S3 王' },
  instruction: { s: 's4', label: 'S4 庞' },
  supervision: { s: 's5', label: 'S5 李' }
}

const getOwnerTag = (menuCode) => {
  const prefix = menuCode.split('_')[0]
  return ownerTagMap[prefix] || null
}

const quickModules = reactive([
  {
    icon: Box,
    title: '智能设计',
    desc: '三维场景 / 基站布局 / 覆盖分析',
    owner: 'S1 高',
    bgColor: '#2563eb',
    menuCode: 'design_3d'   // → /modules/m03/#/design
  },
  {
    icon: Connection,
    title: '数据融合',
    desc: 'CAD数据上传 / 融合状态',
    owner: 'S2 任',
    bgColor: '#059669',
    menuCode: 'fusion_upload'
  },
  {
    icon: Monitor,
    title: '智能审查',
    desc: '安全规范 / 冲突检测 / 审查报告',
    owner: 'S3 王',
    bgColor: '#d97706',
    menuCode: 'review_safety'
  },
  {
    icon: CircleCheck,
    title: '施工指令',
    desc: 'BOM生成 / 工艺要求 / 指令管理',
    owner: 'S4 庞',
    bgColor: '#7c3aed',
    menuCode: 'instruction_bom'
  },
  {
    icon: Bell,
    title: '施工监管',
    desc: '实时监控 / 违章识别 / 验收管理',
    owner: 'S5 李',
    bgColor: '#db2777',
    menuCode: 'supervision_monitor'
  }
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
  // 渐进迁移：sN 未配置时自动回退到 m04
  const iframeUrlMap = {
    // S1 智能设计 — 全部指向 M03 的实际路由
    'design_3d': `${MODULE_BASE.m03}/#/design`,           // 三维场景设计 → /design
    'design_layout': `${MODULE_BASE.m03}/#/design`,        // 基站布局设计 → /design (同一页面不同tab)
    'design_coverage': `${MODULE_BASE.m03}/#/design`,      // 覆盖分析 → /design (同一页面覆盖视图)
    // S2~S5 ...（后续不变）
    'fusion_upload': MODULE_BASE.s2 ? `${MODULE_BASE.s2}/#/upload` : '',
    'fusion_status': MODULE_BASE.s2 ? `${MODULE_BASE.s2}/#/status` : '',
    'review_safety': moduleUrl('s3', 'work-order'),
    'review_conflict': moduleUrl('s3', 'work-order'),
    'review_report': moduleUrl('s3', 'work-order'),
    'instruction_bom': moduleUrl('s4', 'delivery'),
    'instruction_process': moduleUrl('s5', 'construction'),
    'instruction_manage': moduleUrl('s4', 'work-order'),
    'supervision_monitor': moduleUrl('s5', 'project'),
    'supervision_violation': moduleUrl('s5', 'construction'),
    'supervision_acceptance': moduleUrl('s3', 'acceptance'),
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
  if (iframeRef.value && userStore.token && currentUrl.value) {
    const targetOrigin = currentUrl.value.substring(0, currentUrl.value.indexOf('/#'))
    iframeRef.value.contentWindow.postMessage(
      {
        type: 'TOKEN',
        token: userStore.token,
        userInfo: userStore.userInfo || null
      },
      targetOrigin
    )
  }
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
          menuCode: 'fusion',
          menuName: '数据融合',
          children: [
            { menuCode: 'fusion_upload', menuName: 'CAD数据上传', iframeUrl: null },
            { menuCode: 'fusion_status', menuName: '融合状态', iframeUrl: null }
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

/* 负责人 S 标签 */
.owner-tag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 8px;
  line-height: 1.5;
  font-weight: 500;
  vertical-align: middle;
  flex-shrink: 0;
}

.tag-s1 { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
.tag-s2 { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
.tag-s3 { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
.tag-s4 { background: rgba(139, 92, 246, 0.2); color: #c4b5fd; }
.tag-s5 { background: rgba(236, 72, 153, 0.2); color: #f9a8d4; }

.sidebar-menu :deep(.el-menu--collapse) {
  background: transparent !important;
}

.main-content {
  background: #f8fafc;
  padding: 0;
  overflow: auto;
}

.dashboard {
  padding: 28px;
  height: 100%;
  overflow-y: auto;
}

.dashboard-header {
  margin-bottom: 28px;
}

.dashboard-header h2 {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}

.dashboard-header p {
  color: #64748b;
  font-size: 14px;
}

.modules-grid {
  margin-bottom: 0;
}

.modules-grid h3 {
  font-size: 15px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 16px;
}

.module-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.module-card {
  background: white;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.module-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.module-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.module-info {
  flex: 1;
  min-width: 0;
}

.module-info h4 {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 3px;
}

.module-info p {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 6px;
}

.module-owner {
  display: inline-block;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  font-weight: 500;
}

.content-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
