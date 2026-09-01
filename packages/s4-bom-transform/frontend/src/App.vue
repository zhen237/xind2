<template>
  <div id="s4-app">
    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <h1>XA-202610 通信基建工程数智化设计与交付</h1>
          <span class="app-tag">S4 施工指令转化 (BOM)</span>
        </div>
        <div class="header-nav">
          <el-button
            :type="$route.path === '/' ? 'primary' : 'default'"
            size="small"
            @click="$router.push('/')"
          >
            流水线概览
          </el-button>
          <el-button
            :type="$route.path === '/bom' ? 'primary' : 'default'"
            size="small"
            @click="$router.push('/bom')"
          >
            BOM 生成
          </el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1f3a5f;
  color: white;
  padding: 0 20px;
  height: 56px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-left h1 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}
.app-tag {
  font-size: 12px;
  color: #a0b4d0;
  background: rgba(255,255,255,0.1);
  padding: 2px 10px;
  border-radius: 10px;
}
.header-nav {
  display: flex;
  gap: 8px;
}
</style>
