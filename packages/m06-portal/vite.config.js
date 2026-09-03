import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api/m01': {
        target: process.env.VITE_API_M01 || 'http://localhost:8080',
        changeOrigin: true
      },
      '/api/m02': {
        target: process.env.VITE_API_M02 || 'http://localhost:8081',
        changeOrigin: true
      },
      '/api/m03': {
        target: process.env.VITE_API_M03 || 'http://localhost:8083',
        changeOrigin: true
      },
      '/api/m04': {
        target: process.env.VITE_API_M04 || 'http://localhost:8084',
        changeOrigin: true
      },
      '/api/m05': {
        target: process.env.VITE_API_M05 || 'http://localhost:8085',
        changeOrigin: true
      },
      // S3 审查后端（portal 工作台「S1→S3 设计审查流」看板直接调用）
      '/api/v1/s3': {
        target: process.env.VITE_API_S3 || 'http://localhost:8089',
        changeOrigin: true
      },
      // S2 数据融合后端（工作台状态条调用 /api/s2/cad/fusion/tasks）
      // 注意：S2 后端默认 8082，但本机 8082 被死进程占用，实际常跑在 8096
      '/api/s2': {
        target: process.env.VITE_API_S2 || 'http://localhost:8096',
        changeOrigin: true
      },
      // S5 施工监管后端（Node，工作台状态条调用 /api/s5/devices）
      '/api/s5': {
        target: process.env.VITE_API_S5 || 'http://localhost:8091',
        changeOrigin: true
      },
      // S4 BOM 后端（任务看板聚合 S1/S3/S4 状态）
      '/api/s4': {
        target: process.env.VITE_API_S4 || 'http://localhost:8090',
        changeOrigin: true
      },
      // 子模块前端开发代理（dev 时各子模块独立启动，portal 通过代理访问）
      '/modules/m03': {
        target: 'http://localhost:9000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/modules\/m03/, '/modules/m03')
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@shared': resolve(__dirname, '../shared/frontend')
    }
  }
})
