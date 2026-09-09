import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // 部署子路径：生产用 /modules/s2/；开发未设 VITE_BASE 时回退到 /modules/s2/（dev 下可用 `VITE_BASE=/ npm run dev` 切回根路径）
  base: process.env.VITE_BASE || '/modules/s2/',
  plugins: [vue()],
  server: {
    port: 5182,
    proxy: {
      // S2 数据融合后端。默认 8096（本机 8082 被死进程占用，S2 实际跑 8096），
      // 可通过 VITE_API_S2 环境变量覆盖（与 portal 同款，便于切换部署）。
      '/api/s2': {
        target: process.env.VITE_API_S2 || 'http://localhost:8096',
        changeOrigin: true,
      },
    },
  },
})
