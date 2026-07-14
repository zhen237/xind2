# Screen — 数据大屏聚合层

**类型**: Java Spring Boot 微服务
**端口**: 8087
**归属**: 共享基础设施
**负责人**: 李

## 职责

- 聚合各赛题数据到统一大屏
- 提供大屏专用数据接口
- 实时数据推送（WebSocket）

## 启动

```bash
cd packages/screen/backend
mvn spring-boot:run
```

## 依赖

- **MySQL**: 查询各模块业务数据
- **InfluxDB**: 时序数据读取
- **各赛题数据接口**: `/api/v1/sN/screen-data`

## 数据接口约定

各赛题需提供大屏数据接口：

```
GET /api/v1/s1/screen-data  → S1 设计统计
GET /api/v1/s3/screen-data  → S3 审查统计
GET /api/v1/s4/screen-data  → S4 BOM统计
GET /api/v1/s5/screen-data  → S5 施工监管
```

## 前端

前端目录存在但为空骨架（暂未开发）。
