import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  // 部署子路径：生产用 /modules/s4/；开发未设 VITE_BASE 时回退到 /modules/s4/（dev 下可用 `VITE_BASE=/ npm run dev` 切回根路径）
  base: process.env.VITE_BASE || '/modules/s4/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5190,
    proxy: {
      '/api/s1': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
      '/api/s3': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
      '/api/s4': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
      '/api/s5': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
      '/api/pipeline': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
    },
  },
})
