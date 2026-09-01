import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  // iframe 子模块基路径：m06-portal 通过 moduleUrl('s3') 拼接为 /modules/s3/，
  // dev 与 build 均在此路径下服务；生产静态资源须部署到门户的 /modules/s3 目录。
  base: '/modules/s3/',
  plugins: [vue()],
  server: {
    port: 5189,
    proxy: {
      // S3 Python 规则引擎专属探活接口（前端经此探活；具体路径优先于通用前缀，避免被 /api/v1/s3 吞掉）
      '/api/v1/s3/review/health': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/api/v1/s3/review/stats': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/api/v1/s3/review/rules': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      // 统一认证 m01-auth（端口 8080）：登录签发 JWT
      '/api/m01': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      // S3 Java 后端（/api/v1/s3/** 全部走 8089）
      '/api/v1/s3': {
        target: 'http://localhost:8089',
        changeOrigin: true
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  }
})
