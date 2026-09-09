import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // 部署子路径：生产用 /modules/m04/；开发未设 VITE_BASE 时回退到 /modules/m04/（dev 下可用 `VITE_BASE=/ npm run dev` 切回根路径）
  base: process.env.VITE_BASE || '/modules/m04/',
  plugins: [vue()],
  server: {
    port: 5175,
    proxy: {
      '/api/m04': {
        target: 'http://localhost:8084',
        changeOrigin: true
      }
    }
  }
})