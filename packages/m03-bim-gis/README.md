# M03 — BIM+GIS 三维设计服务

**类型**: Java Spring Boot + Vue 3 前后端分离
**端口**: 后端 8083 / 前端 5174
**归属**: S1 — 面向专业GIS平台的通信工程智能辅助设计
**负责人**: 高

## 职责

- 参数化基站设计（模板选择 → 参数填写 → 拓扑生成）
- 3D 站点可视化（CesiumJS）
- 覆盖分析（热力图/信号仿真）
- 管线路由规划
- 设备/项目管理

## 启动

```bash
# 后端
cd packages/m03-bim-gis/backend
mvn spring-boot:run

# 前端
cd packages/m03-bim-gis/frontend
npm install && npm run dev
```

## 依赖

- **M01 Auth**: JWT 鉴权
- **MySQL**: 表前缀 `m03_`
- **Redis**: database 3，缓存设计模板
- **QGIS 插件**: 通过 REST API 调用设计接口

## 配置要点

- Redis 缓存 key 前缀: `m03:`
- Flyway 表: `flyway_schema_history_m03`
- QGIS 插件内网调用接口无 JWT 鉴权（permit-paths 开放）
- 生产环境建议改为 API Key 鉴权
