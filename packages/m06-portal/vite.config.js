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
      '/api/m03': {
        target: process.env.VITE_API_M03 || 'http://localhost:8083',
        changeOrigin: true
      },
      '/api/m05': {
        target: process.env.VITE_API_M05 || 'http://localhost:8085',
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