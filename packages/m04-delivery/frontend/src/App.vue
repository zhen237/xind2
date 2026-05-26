<template>
  <el-container style="height: 100vh;">
    <el-header class="header">
      <div class="logo">M04 数智化交付</div>
      <el-menu mode="horizontal" :default-active="currentMenu" class="nav-menu">
        <el-menu-item index="/project" @click="navigate('/project')">项目管理</el-menu-item>
        <el-menu-item index="/work-order" @click="navigate('/work-order')">工单管理</el-menu-item>
        <el-menu-item index="/construction" @click="navigate('/construction')">施工记录</el-menu-item>
        <el-menu-item index="/acceptance" @click="navigate('/acceptance')">验收管理</el-menu-item>
        <el-menu-item index="/delivery" @click="navigate('/delivery')">交付包管理</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const currentMenu = ref('/project')

watch(() => router.currentRoute.value.path, (val) => {
  currentMenu.value = val
})

const navigate = (path) => {
  router.push(path)
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.el-container {
  height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.logo {
  font-size: 20px;
  font-weight: bold;
}

.nav-menu {
  flex: 1;
  justify-content: flex-end;
}

.nav-menu .el-menu-item {
  color: rgba(255, 255, 255, 0.9);
}

.nav-menu .el-menu-item:hover,
.nav-menu .el-menu-item.is-active {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.main {
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
}
</style>