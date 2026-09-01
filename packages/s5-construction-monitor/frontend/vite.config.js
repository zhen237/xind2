import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发服务器端口 5191（S5 手册约定）
// /api/s5 代理到 C# 后端 http://localhost:8092
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5191,
    // 忽略 WebGL 构建产物与视频目录的监听（大文件 watch 会 EBUSY 崩溃）
    watch: {
      ignored: ['**/public/twin-webgl/**', '**/public/videos/**']
    },
    proxy: {
      '/api/s5': {
        target: 'http://localhost:8092',
        changeOrigin: true
      }
    }
  }
})
