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
            <el-menu-item
              v-for="item in sideNav"
              :key="item.menuCode"
              :index="item.menuCode"
            >
              <el-icon :size="20"><component :is="getMenuIcon(item.menuCode)" /></el-icon>
              <span>{{ item.name }}</span>
              <span v-if="getOwnerTag(item.menuCode)" class="owner-tag" :class="'tag-' + getOwnerTag(item.menuCode)?.s">{{ getOwnerTag(item.menuCode)?.label }}</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <!-- Main Content -->
        <el-main class="main-content">
          <!-- Welcome Dashboard (when at root path) —— v-show 切换，不销毁已打开的模块 iframe -->
          <div v-show="isDashboard" class="dashboard">
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

            <S1S3Flow @navigate="quickNavigate" />
          </div>

          <!-- Child route content (m03 pages) -->
          <div v-show="isRouterPage" class="router-page">
            <router-view />
          </div>

          <!-- iframe 池：每个模块 URL 一个常驻 iframe，切换菜单只切换可见性，
               子应用内部状态（Cesium 场景 / 已加载数据 / 表单）不会因切页丢失 -->
          <iframe
            v-for="f in framePool"
            :key="f.url"
            :src="f.url"
            class="content-iframe"
            :class="{ 'frame-hidden': !(currentUrl && f.url === currentUrl) }"
            @load="onFrameLoad(f, $event)"
          />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, markRaw, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import S1S3Flow from '@/components/S1S3Flow.vue'
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
  Close,
  HomeFilled
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const isCollapse = ref(false)
const activeMenu = ref('')
const currentUrl = ref('')

// iframe 池：按 URL 常驻，切换菜单仅切换可见性（visibility），
// 子应用内部状态（Cesium 场景 / 已加载数据 / 进行中任务）不会因切页丢失
const framePool = ref([])
const ensureFrame = (url) => {
  if (!url) return
  if (!framePool.value.some(f => f.url === url)) {
    framePool.value.push({ url })
  }
}

const isDashboard = computed(() => route.path === '/' && !currentUrl.value)
const isRouterPage = computed(() => !currentUrl.value && route.path !== '/')

// 子模块前端地址 —— 从 .env 读取，留空则用同源路径（适配生产部署）
const MODULE_BASE = {
  m01: import.meta.env.VITE_FE_M01 || '/modules/m01',
  m02: import.meta.env.VITE_FE_M02 || '/modules/m02',
  // M03 前端独立 dev server（端口 9000），dev 模式必须用绝对地址
  // 因为 Vite proxy 无法将完整 HTML SPA 页面反向代理给 iframe
  // 生产环境未配置时回退到同源相对路径 /modules/m03/
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
  workbench: markRaw(HomeFilled),
  design: markRaw(Box),
  fusion: markRaw(Connection),
  review: markRaw(Monitor),
  instruction: markRaw(CircleCheck),
  supervision: markRaw(Bell),
  system: markRaw(Setting)
}

// S赛题编号 + 负责人标签（同时覆盖 DB 菜单代码和开发模式代码）
const ownerTagMap = {
  // 开发模式菜单前缀
  design:   { s: 's1', label: 'S1' },
  fusion:   { s: 's2', label: 'S2' },
  review:   { s: 's3', label: 'S3' },
  instruction: { s: 's4', label: 'S4' },
  supervision: { s: 's5', label: 'S5' },
  // 数据库返回的菜单代码
  simulation: { s: 's2', label: 'S2' },
  delivery:   { s: 's4', label: 'S4' },
  twin:       { s: 's5', label: 'S5' }
}

const getOwnerTag = (menuCode) => {
  const prefix = menuCode.split('_')[0]
  return ownerTagMap[prefix] || null
}

// 侧边栏固定为 S1–S5 五大模块（真实业务流顺序：S2 融合 → S1 设计 → S3 审查 → S4 指令 → S5 监管）
// 与首页卡片、顶部数据流看板保持一致；menuCode 复用 iframeUrlMap / routerPaths 的既有跳转
const sideNav = reactive([
  { menuCode: 'workbench', name: '工作台' },
  { menuCode: 'fusion_upload', name: 'S2 数据融合' },
  { menuCode: 'design', name: 'S1 智能设计' },
  { menuCode: 'review_safety', name: 'S3 智能审查' },
  { menuCode: 'instruction_bom', name: 'S4 施工指令' },
  { menuCode: 'supervision_monitor', name: 'S5 施工监管' }
])

const quickModules = reactive([
  {
    icon: Connection,
    title: '数据融合',
    desc: 'CAD数据上传 / 融合状态',
    owner: 'S2',
    bgColor: '#059669',
    menuCode: 'fusion_upload'
  },
  {
    icon: Box,
    title: '智能设计',
    desc: '三维场景 / 基站布局 / 覆盖分析',
    owner: 'S1',
    bgColor: '#2563eb',
    menuCode: 'design'   // 智能设计（合并原三维场景/基站布局/覆盖分析三个同名入口）→ /modules/m03/#/design
  },
  {
    icon: Monitor,
    title: '智能审查',
    desc: '安全规范 / 冲突检测 / 审查报告',
    owner: 'S3',
    bgColor: '#d97706',
    menuCode: 'review_safety'
  },
  {
    icon: CircleCheck,
    title: '施工指令',
    desc: 'BOM生成 / 工艺要求 / 指令管理',
    owner: 'S4',
    bgColor: '#7c3aed',
    menuCode: 'instruction_bom'
  },
  {
    icon: Bell,
    title: '施工监管',
    desc: '实时监控 / 违章识别 / 验收管理',
    owner: 'S5',
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

  // 工作台：回到首页 dashboard（含 S1→S3 设计审查流看板）
  if (menuCode === 'workbench') {
    currentUrl.value = ''
    router.push('/')
    return
  }

  // 子应用路由映射 —— 使用 MODULE_BASE 拼接，端口变化只改 MODULE_BASE
  // 渐进迁移：sN 未配置时自动回退到 m04
  const iframeUrlMap = {
    // S1 智能设计 — 全部指向 M03 的实际路由
    'design': `${MODULE_BASE.m03}/#/design`,               // 智能设计 → /design（合并原三维场景/基站布局/覆盖分析三个同名入口）
    // S2~S5 ...（后续不变）
    // S2 与 s3/s4/s5 一致：s2 已配置则走 S2 前端，否则回退 m04（不再出现空串导致点不动）
    // 注意：S2 前端路由只有 /upload、/transform、/fusion，无 /status，故融合状态映射到 /fusion
    'fusion_upload': moduleUrl('s2', 'upload'),
    'fusion_status': moduleUrl('s2', 'fusion'),
    'review_safety': moduleUrl('s3', 'work-order'),
    'review_conflict': moduleUrl('s3', 'work-order'),
    'review_report': moduleUrl('s3', 'work-order'),
    'instruction_bom': moduleUrl('s4', 'bom'),
    'instruction_process': moduleUrl('s4', 'construction'),
    'instruction_manage': moduleUrl('s4', 'work-order'),
    'supervision_monitor': moduleUrl('s5', 'project'),
    'supervision_violation': moduleUrl('s5', 'construction'),
    'supervision_acceptance': moduleUrl('s5', 'acceptance')
  }

  // 系统管理页面走路由（Vue 组件内嵌渲染，不走 iframe）
  const routerPaths = {
    'system_user': '/system/user',
    'system_role': '/system/role',
    'system_progress': '/system/progress'
  }

  if (routerPaths[menuCode]) {
    // 路由页面：清空 iframe URL → 触发 <router-view> 渲染（iframe 池保持常驻，仅隐藏）
    currentUrl.value = ''
    router.push(routerPaths[menuCode])
  } else if (iframeUrlMap[menuCode]) {
    // iframe 页面（子模块前端）：入池并激活；已打开过则直接复用，不重载、不丢状态
    const url = iframeUrlMap[menuCode]
    ensureFrame(url)
    currentUrl.value = url
  } else {
    // 如果没有配置，再尝试从菜单数据读取
    const menu = findMenuByCode(userStore.menus, menuCode)
    if (menu && menu.iframeUrl) {
      ensureFrame(menu.iframeUrl)
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

const onFrameLoad = (frame, event) => {
  const win = event?.target?.contentWindow
  if (win && userStore.token && frame.url) {
    // 提取目标 origin：绝对URL 取协议+host，相对路径用当前窗口 origin
    let targetOrigin
    if (frame.url.startsWith('http')) {
      // http://host/path#/route → 取 http://host
      targetOrigin = frame.url.substring(0, frame.url.indexOf('/', 8))
    } else {
      // /modules/m03/#/design → 同源
      targetOrigin = window.location.origin
    }
    win.postMessage(
      {
        type: 'TOKEN',
        token: userStore.token,
        userInfo: userStore.userInfo || null
      },
      targetOrigin || '*'
    )
  }
}

onMounted(async () => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
  // 统一使用静态菜单（与本地开发模式一致，含 S 标签）
  // 不再依赖数据库菜单格式，确保生产环境与开发环境界面一致
  userStore.menus = [
    {
      menuCode: 'workbench',
      menuName: '工作台'
    },
    {
      menuCode: 'design',
      menuName: '智能设计'
      // 合并原三个子项（三维场景设计/基站布局设计/覆盖分析）——三者均指向 M03 同一页面 /design，单一入口即可
    },
    {
      menuCode: 'fusion',
      menuName: '数据融合',
      children: [
        { menuCode: 'fusion_upload', menuName: 'CAD数据上传' },
        { menuCode: 'fusion_status', menuName: '融合状态' }
      ]
    },
    {
      menuCode: 'review',
      menuName: '智能审查',
      children: [
        { menuCode: 'review_safety', menuName: '安全规范审查' },
        { menuCode: 'review_conflict', menuName: '资源冲突检测' },
        { menuCode: 'review_report', menuName: '审查报告' }
      ]
    },
    {
      menuCode: 'instruction',
      menuName: '施工指令',
      children: [
        { menuCode: 'instruction_bom', menuName: 'BOM生成' },
        { menuCode: 'instruction_process', menuName: '工艺要求' },
        { menuCode: 'instruction_manage', menuName: '施工指令管理' }
      ]
    },
    {
      menuCode: 'supervision',
      menuName: '施工监管',
      children: [
        { menuCode: 'supervision_monitor', menuName: '实时监控' },
        { menuCode: 'supervision_violation', menuName: '违章识别' },
        { menuCode: 'supervision_acceptance', menuName: '验收管理' }
      ]
    },
    {
      menuCode: 'system',
      menuName: '系统管理',
      children: [
        { menuCode: 'system_user', menuName: '用户管理' },
        { menuCode: 'system_role', menuName: '角色管理' },
        { menuCode: 'system_progress', menuName: '进度看板' }
      ]
    }
  ]

  // 一步到位：门户默认直接嵌入 M03 智能设计页（含「空白网格规划」等设计操作）
  // 用户打开 portal 即可在 5173 内操作 S1 设计模块，无需跳转到 9000
  activeMenu.value = 'design'
  const designUrl = `${MODULE_BASE.m03}/#/design`
  ensureFrame(designUrl)
  currentUrl.value = designUrl
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
  position: relative;
}

.router-page {
  height: 100%;
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

/* iframe 池：全部绝对定位叠放，隐藏用 visibility（保留布局盒，
   避免 display:none 导致 Cesium/WebGL 场景恢复时需重算尺寸） */
.content-iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: none;
  background: #f8fafc;
}

.frame-hidden {
  visibility: hidden;
  pointer-events: none;
}
</style>
