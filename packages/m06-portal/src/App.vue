<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import axios from 'axios'

const token = localStorage.getItem('token')
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

onMounted(() => {})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #0f172a !important;
  color: #e2e8f0;
}

.el-menu {
  background: transparent !important;
}

.el-menu-item,
.el-sub-menu__title {
  background: transparent !important;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #1e1b4b;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #a78bfa, #60a5fa);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #c4b5fd, #93c5fd);
}
</style>
