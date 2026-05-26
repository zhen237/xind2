import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue(), cesium()],
  base: '/modules/m03/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5174,
    host: '0.0.0.0',
    proxy: {
      '/api/m03': {
        target: 'http://localhost:8083',
        changeOrigin: true
      },
      '/api/m01': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'esbuild',
    esbuild: {
      drop: ['console', 'debugger']
    }
  },
  css: {
    preprocessorOptions: {
      css: {
        charset: false
      }
    }
  }
})
