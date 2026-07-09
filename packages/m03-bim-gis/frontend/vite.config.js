import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'
import viteCompression from 'vite-plugin-compression'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

let manualChunks = {}
if (process.env.NODE_ENV === 'production') {
  manualChunks = {
    'element-plus': ['element-plus', '@element-plus/icons-vue'],
    'echarts-vendor': ['echarts'],
    'vue-vendor': ['vue', 'vue-router', 'pinia'],
  }
}

export default defineConfig({
  plugins: [
    vue(),
    cesium(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
      eslintrc: { enabled: true },
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 10240,  // 10KB+ 才压缩
      deleteOriginFile: false,
    }),
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 10240,
      deleteOriginFile: false,
    }),
  ],
  base: process.env.VITE_BASE || '/modules/m03/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@shared': resolve(__dirname, '../../shared/frontend')
    }
  },
  server: {
    port: 9000,
    host: 'localhost',
    proxy: {
      '/api/m03': {
        target: process.env.VITE_M03_BACKEND || 'http://localhost:8083',
        changeOrigin: true
      },
      '/api/m01': {
        target: process.env.VITE_M01_BACKEND || 'http://localhost:8080',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: process.env.NODE_ENV !== 'production',
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
    chunkSizeWarningLimit: 2000,
    esbuild: {
      // 生产环境只移除 log/debug，保留 warn/error 以便排查问题
      drop: process.env.NODE_ENV === 'production' ? ['console.log', 'console.debug', 'debugger'] : []
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
