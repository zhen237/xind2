/**
 * postbuild-cesium.js
 *
 * 修复 vite-plugin-cesium 的部署路径问题：
 * - 插件默认将 Cesium 静态资源放到 dist/<base>/cesium（即 dist/modules/m03/cesium）
 * - 但门户部署会剥离 /modules/m03 前缀映射到 dist 根目录
 * - 导致 Cesium.js / widgets.css 全部 404，全局 Cesium 未定义 → 地球白屏
 *
 * 此脚本在 vite build 完成后执行，将 cesium 从 dist/modules/m03/cesium 移到 dist/cesium，
 * 使剥离前缀后的路径正好命中。index.html 中的引用前缀 /modules/m03/cesium 保持不变。
 */

import { existsSync, renameSync, rmSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const distDir = resolve(__dirname, '..')
const from = resolve(distDir, 'dist/modules/m03/cesium')
const to = resolve(distDir, 'dist/cesium')

if (!existsSync(from)) {
  // dev 模式或插件未输出时静默跳过
  console.log('[postbuild-cesium] skip: dist/modules/m03/cesium not found (dev mode?)')
  process.exit(0)
}

// 清理旧目标（幂等）
rmSync(to, { recursive: true, force: true })
renameSync(from, to)

console.log(`[postbuild-cesium] moved ${from} -> ${to}`)
