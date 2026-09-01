# ADR-003 · GitHub Pages 子路径下 Cesium 资源下沉

> **状态**：已采纳（Accepted）
> **日期**：2026-08-27
> **决策人**：高（统筹）
> **相关**：`.github/workflows/deploy-pages.yml`、`scripts/postbuild-cesium.js`

---

## 背景（Context）

S1 前端（Cesium 三维）需部署到 GitHub Pages 项目页 `https://zhen237.github.io/xind2/modules/m03/`。

GitHub Pages **项目页**的站点根是 `/xind2/`（仓库名即第一级路径），因此构建时 `VITE_BASE=/xind2/modules/m03/` 里的 `xind2` 段会被 Pages 剥离，应用实际应落在站点根的 `/modules/m03/` 下。

原 `postbuild-cesium.js` 把 Cesium 资源移动到 `dist/cesium/`，而 `index.html` 引用的是 `/xind2/modules/m03/cesium/...`。在 Pages 上 `/xind2/` 被剥离后，这些绝对路径全部 404，导致 Cesium 地球白屏。

---

## 决策（Decision）

在 `scripts/postbuild-cesium.js` 中新增 **`DEPLOY_TARGET=pages` 模式**：

- 构建产物整体下沉到 `dist/modules/m03/`（即 `base` 去掉仓库名前缀后的子路径）。
- Cesium、assets、ftth-data.json 等全部相对该目录解析，与 `index.html` 的绝对引用 `/xind2/modules/m03/...` 在 Pages 上完全对齐。
- 默认（`portal` 模式）保持旧行为（Cesium 在 `dist/cesium`），不影响本地 portal 构建。

---

## 替代方案（Options Considered）

| 方案 | 结论 |
|------|------|
| 改用相对路径 `CESIUM_BASE_URL` | ❌ 否决：项目里 Cesium 引用混合绝对/相对，改造面大易漏 |
| 购买自定义域名把站点根设为 `/` | ❌ 不现实：比赛演示无需额外成本 |
| **产物下沉到子路径（采纳）** | ✅ 最小改动，精准对齐 Pages 剥离规则 |

---

## 后果（Consequences）

**正面**
- Pages 子路径下 Cesium / 资源全部正常，不再 404。
- 本地 portal 构建行为不变（`portal` 模式）。

**负面 / 注意**
- 必须区分 `DEPLOY_TARGET` 两种模式，CI 与本地启动不能混用。
- 若未来改用自定义域名（站点根 `/`），需回退该下沉逻辑。

---

## 变更记录

| 版本 | 日期 | 内容 |
|------|------|------|
| v1.0 | 2026-08-27 | 从 S1 Pages 部署踩坑整理为正式 ADR |
