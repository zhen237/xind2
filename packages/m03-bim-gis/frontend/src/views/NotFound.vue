<template>
  <div class="not-found" v-once>
    <div class="content">
      <h1>404</h1>
      <p class="subtitle">页面未找到</p>
      <p class="description">您访问的页面不存在或已被移除</p>
      <div class="actions">
        <el-button type="primary" size="large" @click="$router.push('/design')">
          <el-icon><ArrowLeft /></el-icon> 返回设计页面
        </el-button>
        <el-button size="large" @click="$router.push('/')">
          <el-icon><HomeFilled /></el-icon> 回到首页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ArrowLeft, HomeFilled } from '@element-plus/icons-vue'
</script>

<style scoped>
.not-found {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary, #0a0f1a);
}

.content {
  text-align: center;
  padding: 48px;
}

h1 {
  font-size: 96px;
  font-weight: 800;
  color: var(--primary-color, #00d4ff);
  margin: 0;
  line-height: 1;
  text-shadow: 0 0 40px rgba(0, 212, 255, 0.3);
}

.subtitle {
  font-size: 24px;
  color: var(--text-primary, #e0e0e0);
  margin: 16px 0 8px;
}

.description {
  color: var(--text-secondary, #888);
  margin-bottom: 32px;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
