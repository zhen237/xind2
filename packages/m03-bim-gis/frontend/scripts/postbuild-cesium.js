/**
 * postbuild-cesium.js
 *
 * 修复 vite-plugin-cesium 的部署路径问题：
 * - 插件会把 Cesium 静态资源放到 dist/<base>/cesium（base 取 vite.config.js 的 base，去首尾斜杠）
 *   · 门户部署（默认 base=/modules/m03/）→ dist/modules/m03/cesium
 *   · GitHub Pages 部署（VITE_BASE=/xind2/）→ dist/xind2/cesium
 * - 但门户 / Pages 都会把 base 前缀剥离映射到 dist 根目录
 * - 因此必须把 cesium 从 dist/<base>/cesium 移到 dist/cesium，
 *   否则 Cesium.js / widgets.css 全部 404 → 地球白屏
 *
 * 本脚本对 base 路径通用：根据 VITE_BASE 自动定位 cesium 源目录并归位到 dist/cesium。
 */

import { existsSync, renameSync, rmSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const distDir = resolve(__dirname, '..')

// 与 vite.config.js 默认值保持一致；CI 部署 Pages 时会注入 VITE_BASE=/xind2/
const baseRaw = process.env.VITE_BASE || '/modules/m03/'
const baseRel = baseRaw.replace(/^\/+/, '').replace(/\/+$/, '')

const from = baseRel
  ? resolve(distDir, 'dist', baseRel, 'cesium')
  : resolve(distDir, 'dist', 'cesium')
const to = resolve(distDir, 'dist', 'cesium')

if (from === to) {
  // base 已经是根（/），cesium 本就在 dist/cesium，无需移动
  console.log('[postbuild-cesium] skip: cesium 已在 dist/cesium')
  process.exit(0)
}

if (!existsSync(from)) {
  // dev 模式或插件未输出时静默跳过
  console.log(`[postbuild-cesium] skip: ${from} 不存在（dev 模式？）`)
  process.exit(0)
}

// 清理旧目标（幂等）
rmSync(to, { recursive: true, force: true })
renameSync(from, to)

console.log(`[postbuild-cesium] moved ${from} -> ${to}`)
