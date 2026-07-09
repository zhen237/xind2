# 第5轮优化 — 全部 P0/P1 错误修复总结

## 完成时间
2026-07-09

## 本轮修复概览

| 优先级 | 总数 | 已修复 | 备注 |
|--------|------|--------|------|
| P0 | 5 | 4 | P0-04 (测试) 需独立工作 |
| P1 | 9 | 8 | P1-09 (共享模块) 需架构重构 |

---

## P0 修复详情

### P0-01: m06-portal 硬编码 Token ✅
**文件**: `packages/m06-portal/src/components/CesiumViewer.vue`
- L98: `TIANDITU_TOKEN` → `import.meta.env.VITE_TIANDITU_TOKEN || ''`
- L158: `Cesium.Ion.defaultAccessToken` → `import.meta.env.VITE_CESIUM_ION_TOKEN || ''`
- `.env.example` 新增 Token 模板变量

### P0-02: Git 泄露 ✅
**分析**: `.env` 和 `node_modules` 已被 Git 忽略（根 `.gitignore` 正确配置）
- 补全 `.env.example` 模板（2→7 变量）
- 创建 `m06-portal/.gitignore` 防御层

### P0-03: docker-compose 明文密码 ✅
**文件**: `docker-compose.yml`
- MySQL: `root123`/`apppass123` → `${MYSQL_ROOT_PASSWORD:-changeme}`/`${MYSQL_PASSWORD:-changeme}`
- InfluxDB: `admin123`/`my-super-token` → `${INFLUXDB_ADMIN_PASSWORD:-changeme}`/`${INFLUXDB_ADMIN_TOKEN:-changeme}`
- 保留 `changeme` 默认值 + 说明注释

### P0-05: QGIS persistence.py + 测试 ✅
**文件**: `qgis-plugin/design_engine/persistence.py`
- 从空壳注释恢复为完整实现：`save_design()` / `load_design()` / `list_designs()`
- GeoJSON 格式持久化

**文件**: `qgis-plugin/design_engine/pipeline.py`
- L14: `from ..utils.log_util` → `from utils.log_util` (修复相对导入超界)

**测试结果**: **22/22 全部通过** ✅

---

## P1 修复详情

### P1-01/02: CI 路径 + `|| true` ✅
**文件**: `.github/workflows/deploy.yml`
- `working-directory: xind2/qgis-plugin` → `qgis-plugin`
- 移除 `|| true` (测试失败不应被掩盖)

### P1-03: request.js 取消请求竞态 ✅
**文件**: `packages/m03-bim-gis/frontend/src/utils/request.js`
- **Bug**: `removePending(error.config)` 在 `isCancel` 判断之前执行，取消的请求会误删新请求的 AbortController 引用
- **修复**: `isCancel` 判断移到 `removePending` 之前，取消请求跳过 removePending

### P1-04: XSS 风险 ✅
**文件**: `src/composables/useSiteManager.js` L164
- `innerHTML = entity.description` → `textContent = entity.description`

### P1-05: shortcutManager destroy() ✅
**文件**: `src/utils/shortcutManager.js`
- **Bug**: `bind(this)` 每次创建新引用，`removeEventListener` 永远匹配不上
- **修复**: 在 `init()` 中存储 `_boundKeyDown`/`_boundKeyUp`，destroy() 使用存储的引用

### P1-06: requestCache 无大小上限 ✅
**文件**: `src/utils/requestCache.js`
- 新增 `maxSize = 200`，`set()` 时 LRU 淘汰 (删除 Map 第一个条目)

### P1-07: AutoSaveManager 保存方法 ✅
**文件**: `src/utils/projectManager.js`
- 新增 `AUTO_SAVE_KEY` 常量
- 新增 `saveProjectForAutoSave()` / `loadAutoSave()` / `clearAutoSave()` 静态方法
- `AutoSaveManager.save()` 支持 `setStateProvider()` 回调注入

### P1-08: vite esbuild 保留 error log ✅
**文件**: `vite.config.js`
- `drop: ['console', 'debugger']` → `drop: ['console.log', 'console.debug', 'debugger']`
- 生产环境保留 `console.warn/error` 以便排查

---

## 验证结果

| 验证项 | 状态 |
|--------|------|
| M03 前端 Vite Build | ✅ 通过 |
| QGIS 插件 pytest (22 tests) | ✅ 全部通过 |
| CI Deploy YAML 路径 | ✅ 正确 |

## 未处理的建议（需后续独立工作）

| 优先级 | 项目 | 原因 |
|--------|------|------|
| P0-04 | 3 前端模块添加测试 | 需创建完整测试环境（Jest/Vitest + Cesium mock），工作量 2-3 天 |
| P1-09 | shared/frontend request.js 统一 | 需 3 个前端模块协调升级，工作量 1-2 天 |
