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
      },
      // 高德卫星瓦片代理 — 解决跨域截图黑屏问题
      // 高德服务器未返回 CORS 头 → WebGL canvas 被 tainted → toDataURL 读出全黑
      // 通过 Vite 代理转发时注入 Access-Control-Allow-Origin:* 让 Cesium 能读取像素
      '/gaode-tile': {
        target: 'https://webst01.is.autonavi.com',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/gaode-tile/, ''),
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // 注入 CORS 响应头，让 WebGL 读取跨域瓦片时不污染 canvas
            proxyRes.headers['access-control-allow-origin'] = '*'
          })
        }
      },
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
