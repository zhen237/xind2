# M03模块与QGIS插件优化方案（历史归档）

**版本**: v2.0（合并归档）  
**最后更新**: 2026-07-14  
**合并来源**: M03分级优化实施报告、M03前端页面优化方案、QGIS插件必要性分析与优化方案

> 📦 **历史归档说明**: 本文档合并了 Phase 3 期间（2026-06~07）完成的 M03 模块和 QGIS 插件优化工作。优化已全部实施完毕并通过测试，保留本文档供后续维护参考。

---

## 一、优化成果总览

| 优化项目 | 范围 | 状态 | 完成日期 |
|----------|------|------|----------|
| L1 代码质量优化 | M03 Vue composables 拆分、重复代码消除 | ✅ 完成 | 2026-07-02 |
| L2 性能优化 | Cesium 渲染、缓存策略、请求批处理 | ✅ 完成 | 2026-07-02 |
| L3 用户体验优化 | 工作流引导、快捷键、自动保存 | ✅ 完成 | 2026-07-02 |
| L4 架构优化 | Element Plus 按需导入、Husky+lint-staged | ✅ 完成 | 2026-07-02 |
| QGIS 插件优化 | 热力图渲染、管线图层、persistence 修复 | ✅ 完成 | 2026-07-08 |
| QGIS 测试修复 | pipeline.py + persistence.py | ✅ 22/22 通过 | 2026-07-09 |

---

## 二、M03 四级渐进式优化

### 2.1 L1 — 代码质量优化

**核心改动**:
- Vue composables 拆分：`useDesignState` / `useSiteManager` / `useAutoSave` 等
- 消除 Design.vue（原 ~2200 行）中的重复逻辑
- 统一错误处理和 loading 状态管理

### 2.2 L2 — 性能优化

**核心改动**:
- `requestCache` LRU 缓存（max 50 entries）
- Cesium entity 批处理，减少 render loop 开销
- 防抖/节流优化地图交互事件
- 图片懒加载和资源预加载

**优化指标**: 页面首屏加载 ↓40%，Cesium 帧率 ↑35%

### 2.3 L3 — 用户体验优化

**核心改动**:
- 工作流引导系统（4步 onboarding wizard）
- `shortcutManager` 键盘快捷键（Ctrl+S 保存、Ctrl+Z 撤销等）
- `AutoSaveManager` 30秒自动保存 + 草稿恢复
- 高对比度模式和响应式布局增强

### 2.4 L4 — 架构优化

**核心改动**:
- Element Plus 按需导入（减少 bundle size ~200KB）
- Husky + lint-staged（pre-commit 自动 lint）
- XSS 防护、密码脱敏、Token 硬编码修复
- CORS 安全头统一配置

### 2.5 P0 安全修复（2026-07-08 补充）

| 问题 | 修复 |
|------|------|
| XSS `v-html` 注入 | 统一使用 `DOMPurify` |
| 密码明文存储 | BCrypt 加密 |
| Token 硬编码 | 环境变量管理 |
| CORS `*` 通配 | 白名单配置 |

---

## 三、QGIS 插件优化

### 3.1 必要性确认

**结论: QGIS 插件是比赛硬性要求，不可替代。**

- 子赛题1 明确命名为"QGIS 基站智能辅助设计"
- 答辩/演示必须在 QGIS 中操作展示插件 UI
- QGIS（桌面设计）与 M03（Web 可视化）功能互补，非替代关系

### 3.2 已完成的优化

| 优化项 | 问题 | 修复方案 |
|--------|------|----------|
| 热力图渲染 | 标记 2-6px 不可见 | 6-14px + `insertLayer(0)` 置顶 |
| 管线图层 | 单图层名共存冲突 | 路由类型特定名: `基站-管线关联-直连` / `-曼哈顿` |
| 分类渲染器 | 浮点 RSRP 匹配失败 | `QgsGraduatedSymbolRenderer` 替代 `QgsCategorizedSymbolRenderer` |
| RubberBand 导出 | 导出图纸异常 | 改用临时 `QgsVectorLayer` polygon |
| MarkerLine 构造 | API 参数错误 | 构造参数是 `bool`，用 `setSubSymbol()` |
| persistence.py | 数据持久化逻辑错误 | 完整重写 |
| pipeline.py | 管线生成逻辑修复 | 参数校验 + 边界处理 |

### 3.3 测试验证

```
qgis-plugin/tests/ → 22/22 passed
  persistence.py  → 10/10 ✅
  pipeline.py     → 6/6  ✅
  coverage.py     → 6/6  ✅
```

---

## 四、后续优化建议（未实施，供参考）

### 前端
- [ ] 工作流引导国际化（中英文切换）
- [ ] Cesium 3D Tiles 集成（大场景性能）
- [ ] PWA 离线模式

### QGIS
- [ ] 批量站点导入（CSV/Excel）
- [ ] 实时协作设计（WebSocket 同步）
- [ ] 自定义模板市场

---

> **相关文档**: [技术架构与开发规范](./技术架构与开发规范.md) | [子赛题1 规格设计](./子赛题规格设计/2026-06-02-topic1-parametric-design.md)
