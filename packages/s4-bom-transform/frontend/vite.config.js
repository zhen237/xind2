import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
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
