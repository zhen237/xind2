import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5182,
    proxy: {
      '/api/s2': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
    },
  },
})
