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
