<template>
  <el-container class="layout">
    <el-aside width="220px">
      <div class="logo">S2 CAD→GIS</div>
      <el-menu :default-active="$route.path" router>
        <el-menu-item index="/upload">📤 图纸上传</el-menu-item>
        <el-menu-item index="/transform">🔄 转换结果</el-menu-item>
        <el-menu-item index="/fusion">🧩 融合结果</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
</script>

<style>
html, body, #app { height: 100%; margin: 0; }
.layout { height: 100vh; }
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-weight: 700;
  color: #409eff;
  border-bottom: 1px solid #eee;
}
.el-aside { border-right: 1px solid #eee; }
</style>
