<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const active = computed(() => route.path)
</script>

<template>
  <el-container class="app">
    <el-aside width="220px" class="aside">
      <div class="logo">S5 施工监管</div>
      <el-menu :default-active="active" router>
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon><span>施工监测看板</span>
        </el-menu-item>
        <el-menu-item index="/devices">
          <el-icon><Cpu /></el-icon><span>设备孪生状态</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon><span>告警列表</span>
        </el-menu-item>
        <el-menu-item index="/twin">
          <el-icon><Monitor /></el-icon><span>数字孪生</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">{{ route.meta.title }}</el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style>
html, body, #app { height: 100%; margin: 0; }
.app { height: 100vh; }
.aside { background: #001529; }
.logo { color: #fff; font-size: 18px; font-weight: 600; padding: 18px 16px; letter-spacing: 1px; }
.aside .el-menu { background: #001529; border-right: none; }
.aside .el-menu-item { color: #c0c4cc; }
.aside .el-menu-item.is-active { color: #fff; background: #1890ff33; }
.header { display: flex; align-items: center; font-size: 18px; font-weight: 600; background: #fff; border-bottom: 1px solid #eee; }
</style>
