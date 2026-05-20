<template>
  <el-container style="height: 100vh">
    <el-header class="header">
      <div class="header-left">
        <el-button type="text" @click="toggleMenu" class="menu-toggle">
          <el-icon :size="24">
            <component :is="menuCollapsed ? Menu : Fold" />
          </el-icon>
        </el-button>
        <span class="logo-text">通信基建数智化平台</span>
      </div>
      <div class="header-right">
        <el-dropdown trigger="click">
          <span class="user-info">
            <el-icon :size="20">User</el-icon>
            <span>{{ userStore.userInfo?.realName || userStore.userInfo?.username }}</span>
            <el-icon :size="16">ChevronDown</el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">
                <el-icon>LogOut</el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-container>
      <el-aside :width="menuCollapsed ? '64px' : '200px'" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          :collapse="menuCollapsed"
          mode="vertical"
          class="side-menu"
          @select="handleMenuSelect"
        >
          <template v-for="menu in userStore.menus" :key="menu.menuCode">
            <el-sub-menu v-if="menu.children && menu.children.length > 0" :index="menu.menuCode">
              <template #title>
                <el-icon :size="20">{{ getMenuIcon(menu.menuCode) }}</el-icon>
                <span>{{ menu.menuName }}</span>
              </template>
              <el-menu-item
                v-for="child in menu.children"
                :key="child.menuCode"
                :index="child.menuCode"
              >
                <template #title>
                  <span>{{ child.menuName }}</span>
                </template>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="menu.menuCode">
              <el-icon :size="20">{{ getMenuIcon(menu.menuCode) }}</el-icon>
              <span>{{ menu.menuName }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-aside>
      <el-main class="main-content">
        <iframe
          ref="iframeRef"
          :src="currentUrl"
          style="width: 100%; height: 100%; border: none"
          @load="onIframeLoad"
        />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, watch, onMounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  Menu,
  Fold,
  User,
  ChevronDown,
  LogOut,
  Settings,
  Network,
  Box,
  ClipboardList,
  Monitor
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const menuCollapsed = ref(false)
const activeMenu = ref('')
const currentUrl = ref('')
const iframeRef = ref(null)

const iconMap = {
  system: markRaw(Settings),
  simulation: markRaw(Network),
  design: markRaw(Box),
  delivery: markRaw(ClipboardList),
  twin: markRaw(Monitor)
}

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
  }
}

const toggleMenu = () => {
  menuCollapsed.value = !menuCollapsed.value
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

watch(currentUrl, () => {
  setTimeout(() => {
    onIframeLoad()
  }, 100)
})

onMounted(() => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
  if (!userStore.menus.length) {
    userStore.fetchMenus()
  }
})
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background: #1f2937;
  color: white;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-toggle {
  color: white;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
}

.sidebar {
  background: #374151;
  color: white;
}

.side-menu {
  height: 100%;
  border-right: none;
}

.main-content {
  padding: 0;
  overflow: hidden;
}
</style>
