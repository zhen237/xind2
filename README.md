# 通信基建数智化全流程平台

## 项目简介

本平台服务于通信基础设施的全生命周期管理，覆盖**规划设计 → 三维设计 → 交付验收 → 数字孪生运维**四大阶段。通过模块化、微前端架构，整合 GIS/BIM 可视化、5G 网络仿真、智能交付工作流、物联网实时监控与 AI 告警等能力。

## 架构设计

### 模块划分

| 模块 | 名称 | 端口 | 说明 |
| --- | --- | --- | --- |
| M01 | 统一认证服务 | 8080 | 用户登录、JWT 签发、菜单管理 |
| M02 | 数通网络规划与仿真 | 8081 | 基站站址规划、覆盖仿真、干扰分析 |
| M03 | BIM+GIS 三维设计引擎 | 8083 | 三维场景、BIM 建模、碰撞检测 |
| M04 | 数智化交付与工作流 | 8084 | 工单管理、验收流程、交付包管理 |
| M05 | 数字孪生与智慧运维 | 8085 | 设备监控、告警管理、大屏中心 |
| M06 | 统一前端门户 | 5173 | 登录页、动态菜单、iframe 容器 |

### 技术栈

- **前端**: Vue 3 + Vite + Element Plus + Pinia
- **后端**: Spring Boot 3.2 + MyBatis Plus + JWT
- **数据库**: MySQL 8.0 + PostGIS 3.4
- **消息队列**: EMQX (MQTT)
- **对象存储**: MinIO
- **时序数据库**: InfluxDB 2.7

## 快速开始

### 1. 启动依赖服务

```bash
cd xind2
docker-compose up -d
```

### 2. 初始化数据库

```bash
docker exec -it comm-mysql mysql -uroot -proot123
source /path/to/scripts/init-db.sql
```

### 3. 启动后端服务

```bash
# M01 认证服务
cd packages/m01-auth/backend
mvn spring-boot:run

# M05 运维服务（新开发的日志模块）
cd packages/m05-twin-ops/backend
mvn spring-boot:run
```

### 4. 启动前端门户

```bash
cd packages/m06-portal
npm install
npm run dev
```

### 5. 访问地址

- 前端门户: http://localhost:5173
- M01 API: http://localhost:8080/api/m01/
- M05 API: http://localhost:8085/api/m05/

## 目录结构

```
xind2/
├── packages/
│   ├── m01-auth/           # 统一认证服务
│   │   └── backend/
│   ├── m02-simulation/     # 网络规划与仿真（预留）
│   ├── m03-bim-gis/        # BIM+GIS 三维设计（预留）
│   ├── m04-delivery/       # 数智化交付（预留）
│   ├── m05-twin-ops/       # 数字孪生与智慧运维
│   │   └── backend/
│   └── m06-portal/         # 统一前端门户
├── scripts/
│   └── init-db.sql         # 数据库初始化脚本
├── docker-compose.yml       # Docker Compose 配置
├── .env.example            # 环境变量模板
└── .gitignore
```

## 核心功能

### M01 统一认证
- 用户登录/登出
- JWT Token 生成与验证
- 动态菜单管理
- 角色权限控制

### M05 智慧运维（新开发）
- 设备资产管理
- MQTT 实时数据接入
- 告警管理与统计
- 自动工单生成

## API 示例

### 登录

```bash
POST /api/m01/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

### 获取菜单

```bash
GET /api/m01/menu/user
Authorization: Bearer <token>
```

### 获取告警统计

```bash
GET /api/m05/alert/statistics
Authorization: Bearer <token>
```

## 配置说明

复制 `.env.example` 为 `.env` 并修改配置：

```bash
MYSQL_URL=jdbc:mysql://localhost:3306/comm_platform
JWT_SECRET=your-strong-secret-change-in-production
MINIO_ENDPOINT=http://localhost:9000
MQTT_BROKER=tcp://localhost:1883
```

## 开发规范

1. **模块解耦**: 禁止模块间直接 API 调用，数据共享通过数据库表实现
2. **统一认证**: 使用相同的 JWT secret
3. **表命名**: 使用 `m01_`, `m02_`, `shared_` 前缀
4. **代码风格**: 使用 Lombok，遵循 Spring Boot 规范

## License

MIT License
