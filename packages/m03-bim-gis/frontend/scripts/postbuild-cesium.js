/**
 * postbuild-cesium.js
 *
 * 根据部署目标（DEPLOY_TARGET）修正 Cesium 静态资源路径：
 *
 * 1) portal（默认）：M06 门户 / 本地 nginx 部署
 *    - 服务器会把 base 前缀（/modules/m03 或 /xind2/modules/m03）剥离后映射到 dist 根
 *    - 因此把 cesium 从 dist/<base>/cesium 移到 dist/cesium，与「剥离前缀后 /cesium/...」对应
 *
 * 2) pages：GitHub Pages 静态部署（无后端、VITE_USE_MOCK=true）
 *    - Pages 不剥离 base 前缀，artifact 根直接映射到 https://<user>.github.io/<repo>/
 *    - 页面所有引用都是绝对路径 /xind2/modules/m03/... （xind2 = 仓库名）
 *    - 因此需把 dist 根下的应用文件整体下沉到 dist/xind2/modules/m03/ ，
 *      使 artifact 里文件正好落在 xind2/modules/m03/... ，与绝对引用一一对应
 *    - Cesium 已天然位于 dist/xind2/modules/m03/cesium（插件按 base 拼接），无需再移动
 */

import { existsSync, renameSync, rmSync, mkdirSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const distDir = resolve(__dirname, '..', 'dist')

const deployTarget = process.env.DEPLOY_TARGET || 'portal'
const baseRaw = process.env.VITE_BASE || '/modules/m03/'
const baseRel = baseRaw.replace(/^\/+/, '').replace(/\/+$/, '') // 如 'xind2/modules/m03'

console.log(`[postbuild-cesium] deployTarget=${deployTarget} base=${baseRaw} -> baseRel=${baseRel || '(root)'}`)

if (deployTarget === 'pages') {
  if (!baseRel) {
    console.log('[postbuild-cesium] base 为根，无需下沉，结束')
    process.exit(0)
  }
  // Pages 项目页站点根 = https://<user>.github.io/<repo>/ ，
  // 因此 base 中的 <repo> 段（如 xind2）会被 Pages 剥离，
  // 应用真正要落在 artifact 的 <subpath>/ 下（base 去掉首个路径段）。
  const repoSeg = baseRel.split('/')[0]                 // 'xind2'
  const nestRel = baseRel.split('/').slice(1).join('/') // 'modules/m03'
  const T = resolve(distDir, nestRel)                   // dist/modules/m03
  mkdirSync(T, { recursive: true })

  // 1) Cesium：插件按 base 输出在 dist/<baseRel>/cesium，挪到 dist/<nestRel>/cesium
  const cesiumSrc = resolve(distDir, baseRel, 'cesium')
  if (existsSync(cesiumSrc)) {
    rmSync(resolve(T, 'cesium'), { recursive: true, force: true })
    renameSync(cesiumSrc, resolve(T, 'cesium'))
  }

  // 2) 其余顶层文件/目录（index.html, assets, datasets, ftth-* 等）移入 T
  const nestTop = nestRel.split('/')[0] // 'modules' — T 自身所在的顶层目录，不能移入自己
  for (const name of readdirSync(distDir)) {
    if (name === repoSeg) continue   // 父目录 xind2 保留到最后删除（cesium 已取出）
    if (name === nestTop) continue   // T 顶层目录本身，跳过
    if (name === 'cesium') continue  // 已在步骤1处理
    const src = resolve(distDir, name)
    const dst = resolve(T, name)
    if (src === dst) continue
    rmSync(dst, { recursive: true, force: true })
    renameSync(src, dst)
  }

  // 3) 清理残留的 base 顶层目录（xind2），避免 artifact 里多出 xind2/xind2/...
  const leftover = resolve(distDir, repoSeg)
  if (existsSync(leftover)) rmSync(leftover, { recursive: true, force: true })

  console.log(`[postbuild-cesium] pages mode: 应用文件已下沉到 dist/${nestRel}/`)
  console.log(`[postbuild-cesium] 示例: ${resolve(T, 'index.html')}`)
  process.exit(0)
}

// ── portal 模式（旧逻辑，保持向后兼容） ───────────────────────────
const from = baseRel
  ? resolve(distDir, baseRel, 'cesium')
  : resolve(distDir, 'cesium')
const to = resolve(distDir, 'cesium')

if (from === to) {
  console.log('[postbuild-cesium] skip: cesium 已在 dist/cesium')
  process.exit(0)
}

if (!existsSync(from)) {
  console.log(`[postbuild-cesium] skip: ${from} 不存在（dev 模式？）`)
  process.exit(0)
}

rmSync(to, { recursive: true, force: true })
renameSync(from, to)
console.log(`[postbuild-cesium] moved ${from} -> ${to}`)
