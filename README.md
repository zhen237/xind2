# 通信基建数智化全流程平台

[![GitHub Pages](https://img.shields.io/badge/%E5%9C%A8%E7%BA%BF%E9%A2%84%E8%A7%88-GitHub%20Pages-blue?style=for-the-badge&logo=github)](https://zhen237.github.io/xind2/)

> 点击上方徽章可直接访问 M03 BIM-GIS 三维设计模块的在线演示（首次加载约 5-10 秒）。

## 比赛信息

**比赛名称**: 挑战杯"揭榜挂帅"擂台赛 - 通信基建工程数智化设计与交付关键技术
**发榜单位**: 烽火通信科技股份有限公司
**截止时间**: 2026年9月15日

## 项目简介

本平台为通信基础设施建设提供一套完整的数字化解决方案，覆盖从**规划设计 → 三维设计 → 交付验收 → 运行维护**的全过程。通过模块化设计，整合了地图可视化、网络覆盖仿真、智能交付流程、设备实时监控与 AI 智能分析等功能。

### 子赛题选择

| 子赛题 | 说明 | 状态 |
|--------|------|------|
| 子赛题1 | 面向专业GIS平台的通信工程智能辅助设计 | ✅ 已完成 |
| 子赛题2 | 多源异构工程数据融合 | ❌ 跳过 |
| 子赛题3 | 基于行业标准的设计智能审查 | 🔄 开发中 |
| 子赛题4 | 设计成果向施工指令的自动转化 | 🔄 开发中 |
| 子赛题5 | 施工过程智能监管 | 🔄 开发中 |

## 架构设计

### 模块划分

| 模块 | 名称 | 端口 | 说明 |
| --- | --- | --- | --- |
| M01 | 统一认证服务 | 8080 | 用户登录、JWT 签发、菜单管理 |
| M03 | BIM+GIS 三维设计引擎 | 8083/5174 | 三维场景、基站设计、覆盖分析 |
| M04 | 数智化交付与工作流 | 8084/5175 | 工单管理、验收流程、交付包管理 |
| M05 | 数字孪生与智慧运维 | 8085 | 设备监控、告警管理、大屏中心 |
| M06 | 统一前端门户 | 5173 | 登录页、动态菜单、iframe 容器 |
| M07 | CV视觉检测引擎 | 8088 | 安全帽检测、围挡检测、违章识别 |
| QGIS插件 | 基站智能设计 | - | 蜂窝拓扑、覆盖计算、图纸导出 |

### 技术栈

- **前端**: Vue 3（页面开发）+ Vite（构建工具）+ Element Plus（界面组件）+ Pinia（状态管理）+ CesiumJS（三维地图）
- **后端**: Spring Boot（后端服务）+ MyBatis Plus（数据库操作）+ JWT（安全认证）
- **QGIS插件**: Python + PyQGIS（地图设计扩展）+ PyQt5（界面开发）
- **AI图像识别**: Python + FastAPI（接口服务）+ YOLOv8（图像识别模型）
- **数据库**: MySQL（主数据库）+ PostgreSQL + PostGIS（空间数据存储）
- **消息队列**: EMQX（MQTT协议，设备通信）
- **文件存储**: MinIO（文件上传下载）
- **时序数据库**: InfluxDB（时间序列数据存储）

## 快速开始

### 1. 环境要求

| 依赖 | 版本 | 下载地址 |
| --- | --- | --- |
| JDK | 17 | [Adoptium Temurin 17](https://adoptium.net/temurin/releases/?version=17) |
| Maven | 3.9+ | [Apache Maven](https://maven.apache.org/download.cgi) |
| MySQL | 8.0+ | [MySQL Community Server](https://dev.mysql.com/downloads/mysql/) |
| Redis | 7.0+ | [Redis Windows](https://github.com/redis-windows/redis-windows/releases) |
| Node.js | 18+ | [Node.js](https://nodejs.org/) |

### 2. 最少服务启动（推荐）

**必须启动的服务：**

| 服务 | 端口 | 作用 | 启动命令 |
| --- | --- | --- | --- |
| MySQL | 3306 | 数据库 | 作为 Windows 服务自动启动 |
| Redis | 6379 | 缓存 | 作为 Windows 服务自动启动 |
| M01 认证服务 | 8080 | 用户认证 | `mvn spring-boot:run` |
| M06 前端门户 | 5173 | 用户界面 | `npm run dev` |

**可选服务：**

| 服务 | 端口 | 作用 | 启动命令 |
| --- | --- | --- | --- |
| M05 运维服务 | 8085 | 设备监控、告警管理 | `mvn spring-boot:run` |

### 3. 启动步骤

**步骤 1：确认基础服务运行**

```powershell
# 检查 MySQL 和 Redis 是否运行
netstat -ano | findstr "3306 6379"
```

**步骤 2：启动 M01 认证服务（终端1）**

```powershell
cd D:\homework\xind2\xind2\packages\m01-auth\backend
D:\maven\apache-maven-3.9.16-bin\bin\mvn.cmd spring-boot:run
```

**步骤 3：启动 M05 运维服务（可选，终端2）**

```powershell
cd D:\homework\xind2\xind2\packages\m05-twin-ops\backend
D:\maven\apache-maven-3.9.16-bin\bin\mvn.cmd spring-boot:run
```

**步骤 4：启动前端门户（终端3）**

```powershell
cd D:\homework\xind2\xind2\packages\m06-portal
npm run dev
```

### 4. 初始化数据库

使用 Navicat 或命令行导入初始化脚本：

```powershell
mysql -uroot -p comm_platform < scripts/init-db.sql
```

### 5. 访问地址

| 服务 | 地址 |
| --- | --- |
| 前端门户 | http://localhost:5173 |
| M01 API | http://localhost:8080/api/m01/ |
| M05 API | http://localhost:8085/api/m05/ |

### 6. 登录信息

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 超级管理员 |
| operator | admin123 | 运维人员 |
| designer | admin123 | 设计人员 |

## 目录结构

```
xind2/
├── packages/
│   ├── m01-auth/           # 统一认证服务
│   │   └── backend/
│   ├── m03-bim-gis/        # BIM+GIS 三维设计
│   │   ├── backend/        # M03后端
│   │   └── frontend/       # M03前端
│   ├── m04-delivery/       # 数智化交付
│   │   ├── backend/        # M04后端
│   │   └── frontend/       # M04前端
│   ├── m05-twin-ops/       # 数字孪生与智慧运维
│   │   └── backend/
│   ├── m06-portal/         # 统一前端门户
│   └── m07-cv-engine/      # CV视觉检测引擎
├── qgis-plugin/            # QGIS基站智能设计插件
│   ├── design_engine/      # 设计引擎
│   ├── models/             # 数据模型
│   └── layers/             # 图层管理
├── docs/                   # 项目文档
├── scripts/
│   └── init-db.sql         # 数据库初始化脚本
├── docker-compose.yml       # Docker Compose 配置
├── .env.example            # 环境变量模板
└── .gitignore
```

## 核心功能

### M01 统一认证
- 用户登录/登出
- 安全令牌验证
- 动态菜单管理
- 角色权限控制

### QGIS插件 - 基站智能设计（子赛题1）
- 基站布局自动生成（六边形网格）
- 信号覆盖范围计算（专业传播模型）
- 标准图纸导出（PDF格式）
- 智能避让检测（避开建筑物、水域、生态保护区）
- 数据同步到系统后端
- 一键完成设计流程

### M03 BIM+GIS三维设计
- 三维可视化展示（基于CesiumJS）
- 基站站点标记显示
- 信号覆盖热力图
- 图层显示控制

### M04 数智化交付（子赛题3/4/5）
- 工单管理
- 工程验收管理
- 交付包管理
- 施工记录管理

### M05 智慧运维
- 设备资产管理
- 实时数据接入（MQTT协议）
- 告警管理与统计
- 自动生成工单

### M07 AI视觉检测引擎（子赛题5）
- 安全帽佩戴检测
- 施工围挡检测
- 违章行为识别
- 隐蔽工程影像验证

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
GET /api/m01/menu
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

## 五人分工

| 成员 | 角色 | 负责模块 |
|------|------|----------|
| 人A | QGIS插件 + M03 | 基站设计、3D可视化、数据同步 |
| 人B | QGIS插件BOM | BOM生成引擎 |
| 人C | M04后端 | 审查引擎、BOM管理、监管模块 |
| 人D | M05 + M07 | 数字孪生、CV引擎 |
| 人E | M06 + 前端 | 门户、前端页面 |

## 开发规范

1. **模块解耦**: 禁止模块间直接 API 调用，数据共享通过数据库表实现
2. **统一认证**: 使用相同的 JWT secret
3. **表命名**: 使用 `m01_`, `m03_`, `m04_`, `shared_` 前缀
4. **代码风格**: 使用 Lombok，遵循 Spring Boot 规范

## License

MIT License
