# S5 — 施工过程智能监管

**类型**: Java Spring Boot + Vue 3（新建）
**端口**: 后端 8091 / 前端 5191
**归属**: S5 — 施工过程智能监管
**负责人**: 李

## 职责

- 施工过程实时监管
- 安全帽/围挡 AI 检测（调用 M07 CV 引擎）
- 施工进度跟踪
- 告警与事件管理
- 施工监管大屏
- 从 M04 迁移施工记录代码（ConstructionRecord）

## 启动

```bash
# 后端
cd packages/s5-construction-monitor/backend
mvn spring-boot:run

# 前端（待创建）
cd packages/s5-construction-monitor/frontend
npm install && npm run dev
```

## 依赖

- **M01 Auth**: JWT 鉴权
- **M05 Twin Ops**: 设备状态/告警数据
- **M07 CV Engine**: AI 视觉检测结果
- **S4 REST API**: 接收施工指令（接口契约见技术架构与开发规范 §5.5）
- **MySQL**: 表前缀 `s5_`，Flyway 表 `flyway_schema_history_s5`

## API 约定

```
POST /api/v1/s5/monitor/plan       # 创建监管计划
GET  /api/v1/s5/monitor/progress   # 施工进度
GET  /api/v1/s5/monitor/alerts     # 实时告警
GET  /api/v1/s5/screen-data        # 大屏数据接口
```

## M04 迁移清单

从 M04 迁移以下代码到 S5：
- ConstructionRecordController/ConstructionRecord
- VideoSurveillanceController
- 对应 Service/Mapper
- 前端 views/ConstructionRecord.vue
