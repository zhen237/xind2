import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发服务器端口 5191（S5 手册约定）
// /api/s5 代理到 C# 后端 http://localhost:8091
export default defineConfig({
  // 部署子路径：生产用 /modules/s5/；开发未设 VITE_BASE 时回退到 /modules/s5/（dev 下可用 `VITE_BASE=/ npm run dev` 切回根路径）
  base: process.env.VITE_BASE || '/modules/s5/',
  plugins: [vue()],
  server: {
    port: 5191,
    // 忽略 WebGL 构建产物与视频目录的监听（大文件 watch 会 EBUSY 崩溃）
    watch: {
      ignored: ['**/public/twin-webgl/**', '**/public/videos/**']
    },
    proxy: {
      '/api/s5': {
        target: 'http://localhost:8091',
        changeOrigin: true
      }
    }
  }
})
