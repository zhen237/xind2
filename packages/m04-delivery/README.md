# M04 — 数智化交付与工作流

**类型**: Java Spring Boot + Vue 3 前后端分离
**端口**: 后端 8084 / 前端 5175
**归属**: 过渡模块（逐步迁移到 S3/S4/S5）
**涉及赛题**: S3-王（验收）、S4-庞（交付）、S5-李（施工记录）

## ⚠️ 重要：M04 为过渡模块

M04 当前混合了 3 个赛题的代码，正逐步迁移：

| 代码 | 归属赛题 | 迁移目标 |
|------|---------|----------|
| Acceptance*/SafetyCheck/BarrierCheck 等 | S3 王 | s3-review-engine |
| DeliveryPackage*/WorkOrder 等 | S4 庞 | s4-bom-transform |
| ConstructionRecord 等 | S5 李 | s5-construction-monitor |
| Project/Init/ScreenInternal | 通用保留 | M04 |

**禁止规则**:
- 禁止在 M04 中新增跨赛题的 Entity/Service
- 修改 M04 代码前确认归属的赛题
- 迁移期间 M04 保持可运行状态

## 启动

```bash
# 后端
cd packages/m04-delivery/backend
mvn spring-boot:run

# 前端
cd packages/m04-delivery/frontend
npm install && npm run dev
```

## 依赖

- **MySQL**: 表前缀 `m04_`，Flyway 表 `flyway_schema_history_m04`
- **MinIO**: bucket `m04-media`，存储交付文件
