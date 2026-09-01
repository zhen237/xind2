<script setup>
import { ref, onMounted } from 'vue'

/**
 * 数字孪生页：嵌入 Unity WebGL 构建产物（frontend/public/twin-webgl/）。
 * - 有构建产物 → iframe 全屏嵌入 gamescenes WebGL 客户端
 * - 无构建产物 → 显示构建指引（见 README「WebGL 构建与嵌入」）
 */
const hasBuild = ref(false)
const checking = ref(true)

// 探测构建产物是否就位（产物约定：public/twin-webgl/，loader 在 Build/ 子目录）
// 注意：vite dev / SPA fallback 会把不存在的路径也回退成 index.html（200），
// 因此用 fetch 检查 content-type —— 真正的 loader.js 是 JavaScript，
// fallback 的 index.html 是 text/html，可据此区分。
const LOADER_URL = `${import.meta.env.BASE_URL}twin-webgl/Build/twin-webgl.loader.js`

async function checkBuild() {
  checking.value = true
  try {
    const resp = await fetch(`${LOADER_URL}?_=${Date.now()}`, { method: 'GET' })
    const type = resp.headers.get('content-type') || ''
    hasBuild.value = resp.ok && !type.includes('text/html')
  } catch {
    hasBuild.value = false
  } finally {
    checking.value = false
  }
}

onMounted(checkBuild)
</script>

<template>
  <div class="twin-page">
    <div v-if="checking" class="placeholder">
      <el-icon class="loading-icon" :size="36"><Loading /></el-icon>
      <p>正在加载数字孪生…</p>
    </div>

    <div v-else-if="hasBuild" class="twin-frame">
      <iframe
        src="/twin-webgl/index.html"
        class="twin-iframe"
        frameborder="0"
        allowfullscreen
        title="数字孪生 3D 场景"
      />
    </div>

    <div v-else class="placeholder">
      <el-result icon="info" title="数字孪生（Unity WebGL）尚未构建">
        <template #sub-title>
          <p style="max-width: 620px; margin: 0 auto; line-height: 1.8">
            3D 孪生场景需要先在装有 Unity 2022.3.62f3c1（含 WebGL Build Support）的机器上构建一次，<br />
            构建完成后将产物放到 <code>frontend/public/twin-webgl/</code> 目录（含 index.html / UnityLoader.js 等），<br />
            刷新本页即可直接嵌入显示。
          </p>
        </template>
        <template #extra>
          <el-button type="primary" @click="checkBuild">刷新检测</el-button>
          <el-link href="/twin-webgl/index.html" target="_blank" type="info" :underline="false">
            若已构建，点此直接打开
          </el-link>
        </template>
      </el-result>
    </div>
  </div>
</template>

<style scoped>
.twin-page {
  height: calc(100vh - 120px);
  min-height: 480px;
}
.placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  background: #fafafa;
  border-radius: 6px;
}
.loading-icon {
  animation: spin 1.2s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.twin-frame {
  height: 100%;
}
.twin-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #1a1a2e;
}
code {
  background: #f0f2f5;
  padding: 2px 6px;
  border-radius: 4px;
  color: #c0392b;
}
</style>
