<template>
  <div
    v-if="error"
    class="error-boundary"
  >
    <div class="error-icon">
      ⚡
    </div>
    <h2>组件渲染异常</h2>
    <p class="error-msg">
      {{ error.message || '未知错误' }}
    </p>
    <pre
      v-if="showStack"
      class="error-stack"
    >{{ error.stack }}</pre>
    <div class="error-actions">
      <el-button
        type="primary"
        @click="retry"
      >
        重试
      </el-button>
      <el-button @click="showStack = !showStack">
        {{ showStack ? '隐藏' : '查看' }}详情
      </el-button>
    </div>
  </div>
  <slot v-else />
</template>

<script>
export default { name: 'ErrorBoundary' }
</script>
<script setup>
import { ref, onErrorCaptured } from 'vue'
import { logger } from '@/utils/logger.js'

const error = ref(null)
const showStack = ref(false)

onErrorCaptured((err, instance, info) => {
  error.value = err
  logger.error('ErrorBoundary', '组件渲染异常', {
    message: err?.message,
    component: instance?.$?.type?.name || instance?.type?.name,
    info,
    stack: err?.stack,
  })
  return false  // 阻止向上传播，避免全局白屏
})

function retry() {
  error.value = null
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-lg, 16px);
  text-align: center;
  min-height: 300px;
}
.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.error-boundary h2 {
  color: var(--danger-color, #ff4444);
  margin-bottom: 12px;
  font-size: 20px;
}
.error-msg {
  color: var(--text-secondary, #a0aec0);
  margin-bottom: 16px;
  max-width: 480px;
  word-break: break-all;
}
.error-stack {
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-muted, #4a5568);
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 11px;
  font-family: var(--font-mono);
  max-width: 600px;
  max-height: 200px;
  overflow: auto;
  margin-bottom: 16px;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-all;
}
.error-actions {
  display: flex;
  gap: 12px;
}
</style>
