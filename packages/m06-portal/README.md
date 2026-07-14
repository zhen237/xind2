# M06 — 统一前端门户

**类型**: Vue 3 前端应用
**端口**: 5173
**归属**: 共享基础设施
**维护人**: 高

## 职责

- 用户登录门户
- iframe 集成各赛题前端模块
- 统一导航菜单
- JWT Token 管理（签发/刷新/传递）
- Dashboard 仪表盘

## 启动

```bash
cd packages/m06-portal
npm install
npm run dev
```

## 接入新模块

1. 在 `src/layout/MainLayout.vue` 的菜单配置中添加路由
2. 在 `src/layout/MainLayout.vue` 的 `iframeUrlMap` 中配置 iframe 地址
3. 新模块前端引入 `shared/frontend/composables/useTokenReceiver.js` 接收 JWT

## 依赖

- **M01 Auth**: 登录/获取用户信息/动态菜单
- **各赛题前端**: 通过 iframe 嵌入

## 配置

- `.env.example` 中配置各赛题前端地址（VITE_FE_S2~S5）
- 不配置则自动回退到 M04
