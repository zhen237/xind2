# ADR-004 · CI 依赖安装策略（禁用 npm ci，按平台重装）

> **状态**：已采纳（Accepted）
> **日期**：2026-08-27
> **决策人**：高（统筹）
> **相关**：`.github/workflows/deploy-pages.yml`

---

## 背景（Context）

S1 前端 CI 用 GitHub Actions（Linux runner）构建。初版 workflow 用 `npm ci` 安装依赖，构建报错：

```
Error: Cannot find module @rollup/rollup-linux-x64-gnu
```

根因：`package-lock.json` 是在 **Windows 本机**生成的，锁定了 Windows 平台的 Rollup 原生二进制（`@rollup/rollup-win32-x64-msvc`），而 **Linux 所需的 `@rollup/rollup-linux-x64-gnu` 是可选依赖（optionalDependencies），lockfile 未包含**。

`npm ci` 严格按 lockfile 安装，不会为当前平台补装缺失的可选原生二进制；`vite build` 底层用 Rollup，缺失 Linux 二进制即崩溃。

---

## 决策（Decision）

**CI 中放弃 `npm ci`，改为先删除 lockfile 再 `npm install`：**

```yaml
- name: Install dependencies
  run: |
    rm -f package-lock.json
    npm install
```

`npm install` 会按 **当前 runner 平台（Linux）重新解析并装齐可选依赖**，包含正确的 Rollup 原生二进制。

---

## 替代方案（Options Considered）

| 方案 | 结论 |
|------|------|
| `npm ci` + 手动补装 linux rollup | ❌ 否决：脆弱，lockfile 一旦再生又坏 |
| 提交跨平台 lockfile | ❌ 不现实：Windows 生成的天然缺 linux 二进制 |
| **删除 lockfile + npm install（采纳）** | ✅ 按平台重装，稳定可复现 |

---

## 后果（Consequences）

**正面**
- CI 构建稳定，消除平台原生二进制缺失问题。
- 本地开发仍可用 `package-lock.json`（Windows 环境正常）。

**负面 / 注意**
- CI 每次 `npm install` 比 `npm ci` 略慢（无 lockfile 约束）。
- 仅前端 `m03-bim-gis/frontend` 受影响；其余模块 CI 如有同类问题需同样处理。
- lockfile 不进 CI，但本地提交时仍可保留（不影响构建，仅 CI 会删）。

---

## 变更记录

| 版本 | 日期 | 内容 |
|------|------|------|
| v1.0 | 2026-08-27 | 从 S1 Pages CI 构建失败整理为正式 ADR |
