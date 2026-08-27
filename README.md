# 通信基建数智化全流程平台



## 比赛信息

**比赛名称**: 挑战杯"揭榜挂帅"擂台赛 - 通信基建工程数智化设计与交付关键技术
**发榜单位**: 烽火通信科技股份有限公司
**截止时间**: 2026年9月15日

## 在线演示（Live Demo）

无需后端，前端以「虚拟数据」模式静态部署在 GitHub Pages，打开即可体验 S1 三维设计界面与右上角 FTTH 叠加图层：

> **演示地址**: https://zhen237.github.io/xind2/modules/m03/
>
> 进入后点顶部「加载数据」即可渲染虚拟基站（卡萨布兰卡 JAD-MAR 数据集坐标），再打开右上角「FTTH 叠加」开关叠加光交箱/光缆图层。
> 部署由 `.github/workflows/deploy-pages.yml` 在推送 `feat/s1-design-dock-refactor` 分支时自动完成（`VITE_USE_MOCK=true`，数据来自 `src/mock/fixtures.js` + `public/ftth-data.json`）。

## 项目简介

本平台为通信基础设施建设提供一套完整的数字化解决方案，覆盖从**规划设计 → 三维设计 → 交付验收 → 运行维护**的全过程。通过模块化设计，整合了地图可视化、网络覆盖仿真、智能交付流程、设备实时监控与 AI 智能分析等功能。

### 子赛题覆盖（全5个）

| 子赛题 | 负责人 | 说明 | 状态 |
|--------|--------|------|------|
| 子赛题1 | **高** | 面向专业GIS平台的通信工程智能辅助设计 | ✅ 基础功能完成 |
| 子赛题2 | **庞** | 多源异构工程数据融合（CAD/GIS） | 🔨 新建模块 |
| 子赛题3 | **王** | 基于行业标准的设计智能审查 | 🔄 开发中 |
| 子赛题4 | **任** | 设计成果向施工指令的自动转化（BOM） | 🔄 开发中 |
| 子赛题5 | **李** | 施工过程智能监管（CV+数字孪生） | 🔄 开发中 |

## 架构设计

### 模块划分

| 模块 | 名称 | 端口 | 归属 | 说明 |
| --- | --- | --- | --- | --- |
| M01 | 统一认证服务 | 8080 | 共享 | 用户登录、JWT 签发、菜单管理 |
| M03 | BIM+GIS 三维设计引擎 | 8083/5174 | S1-高 | 三维场景、基站设计、覆盖分析 |
| M04 | 数智化交付与工作流 | 8084/5175 | 过渡 | 工单管理、验收流程、交付包管理（按赛题拆分中） |
| M05 | 数字孪生与智慧运维 | 8085 | S5-李 | 设备监控、告警管理 |
| M06 | 统一前端门户 | 5173 | 共享 | 登录页、动态菜单、iframe 容器 |
| M07 | CV视觉检测引擎 | 8088 | S5-李 | 安全帽检测、围挡检测、违章识别 |
| Screen | 数据大屏聚合 | 8087 | 共享 | 各赛题数据聚合展示 |
| S2 | CAD数据融合 | 8082/5182 | S2-庞 | DWG/DXF解析、坐标系转换 |
| S3 | 设计智能审查 | 8089/5189 | S3-王 | 规则引擎、安全审查 |
| S4 | BOM施工指令转化 | 8090/5190 | S4-任 | BOM生成、施工指令 |
| S5 | 施工智能监管 | 8091/5191 | S5-李 | CV检测扩展、施工监管 |
| QGIS插件 | 基站智能设计 | - | S1-高 | 蜂窝拓扑、覆盖计算、图纸导出 |

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
| JDK | 21 | [Adoptium Temurin 21](https://adoptium.net/temurin/releases/?version=21) |
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
│   ├── m01-auth/           # 统一认证服务（共享）
│   │   └── backend/
│   ├── m03-bim-gis/        # BIM+GIS 三维设计（S1-高）
│   │   ├── backend/
│   │   └── frontend/
│   ├── m04-delivery/       # 数智化交付（过渡，逐步迁移）
│   │   ├── backend/
│   │   └── frontend/
│   ├── m05-twin-ops/       # 数字孪生与智慧运维（S5-李）
│   │   └── backend/
│   ├── m06-portal/         # 统一前端门户（共享）
│   ├── m07-cv-engine/      # CV视觉检测引擎（S5-李）
│   ├── s2-cad-fusion/      # 多源数据融合（S2-庞）🆕
│   ├── s3-review-engine/   # 设计智能审查（S3-王）🆕
│   ├── s4-bom-transform/   # BOM施工指令转化（S4-任）🆕
│   ├── s5-construction-monitor/ # 施工智能监管（S5-李）🆕
│   ├── screen/             # 数据大屏（共享）
│   └── shared/             # 共享组件/工具类（共享）
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

## 五人分工（按子赛题）

| 成员 | 赛题 | 职责 | 现有模块 | 新建模块 |
|------|------|------|----------|----------|
| **高** | S1 智能设计 | QGIS插件+三维设计+拓扑引擎 | qgis-plugin, m03-bim-gis, m03-topology-engine | — |
| **庞** | S2 数据融合 | CAD/DWG解析+坐标系转换 | — | s2-cad-fusion |
| **王** | S3 智能审查 | 规则引擎+安全审查 | M04验收/安全检查代码 | s3-review-engine |
| **任** | S4 BOM转化 | BOM生成+施工指令 | M04交付/工单代码 | s4-bom-transform |
| **李** | S5 施工监管 | CV检测+数字孪生+监管大屏 | m07-cv-engine, m05-twin-ops, M04施工代码 | s5-construction-monitor |

> **共享基础设施**: m01-auth, m06-portal, shared, screen — 高统筹维护，各赛题独立调用
> 
> **详细分工方案**: 见 [docs/五人分工方案-按子赛题重组.md](docs/五人分工方案-按子赛题重组.md)

## 开发规范

1. **模块解耦**: 禁止模块间直接 API 调用，数据共享通过数据库表实现
2. **统一认证**: 使用相同的 JWT secret
3. **表命名**: 使用 `m01_`, `m03_`, `m04_`, `shared_` 前缀
4. **代码风格**: 使用 Lombok，遵循 Spring Boot 规范

## 分支与目录对应约定（常驻）

每个子赛题有**独立常驻开发分支**，只改自己负责的 `packages/<模块>` 目录，合入 `main` 后**不删分支**（仓库 `delete_branch_on_merge` 已关闭）。

| 分支 | 负责人 | 负责目录（仅这些） | 说明 |
|------|--------|--------------------|------|
| `feat/s1-design-dock-refactor` | 高 | `qgis-plugin/`, `packages/m03-bim-gis/`, `packages/m03-topology-engine/`, `packages/m03-llm-service/` | S1 长期开发分支，**必须常驻远程** |
| `feat/s2-cad-fusion` | 庞 | `packages/s2-cad-fusion/` | |
| `feat/s3-review-engine` | 王 | `packages/s3-review-engine/` | |
| `feat/s4-bom-transform` | 任 | `packages/s4-bom-transform/` | |
| `feat/s2-cad-fusion` | 任 | `packages/s2-cad-fusion/` | |
| `feat/s3-review-engine` | 王 | `packages/s3-review-engine/` | |
| `feat/s4-bom-transform` | 庞 | `packages/s4-bom-transform/` | |
| `feat/s5-construction-monitor` | 李 | `packages/s5-construction-monitor/`, `packages/m05-twin-ops/`, `packages/m07-cv-engine/` | |
| `main` | 全体 | 共享：`packages/m01-auth/`, `packages/m06-portal/`, `packages/screen/`, `packages/shared/`, `docs/`, `scripts/` | 仅共享模块与文档合入 |

> **共享模块约定**：`m01-auth`/`m06-portal`/`screen`/`shared` 任何人改前先在群里说一声，避免两人同时改。
> **禁止跨目录**：S2~S5 分支不要动别人的 `packages/<模块>`，也不要动 `qgis-plugin/`（归高）。

## 多人修改同一文件的冲突处理

当两个人必须改同一份文件（如共享模块、README、pom.xml、`.env.example`）时，按以下流程：

1. **先 rebase 再提交**：`git fetch && git rebase origin/main`，把别人的最新改动拉到本地再合并，减少冲突面。
2. **小步提交**：每次只改一个逻辑点就 commit+push，别攒一大坨再合，冲突面越小越好解。
3. **冲突发生时**：
   - `git status` 看 `both modified` 的文件 → 用编辑器手动解决（保留双方需要的块，删掉 `<<<<<<<`/`=======`/`>>>>>>>` 标记）。
   - 解决后 `git add <文件> && git rebase --continue`。
4. **无法判断谁对谁错时**：在群里 @ 对方确认，**不要默默覆盖**。
5. **锁文件约定**：`package-lock.json` / `pom.xml` 依赖版本变更必须先在群里同步，避免几个人同时加依赖导致合并地狱。
6. **文档类（README/docs）**：改用"追加章节"而非重写整段；若必改同一段，先提 Issue/群消息占位，避免双写。

## 文档

- [S1 设计模块-功能与导出说明](docs/S1-设计模块-功能与导出说明.md) — S1 三维设计页（基站/机房标签拆分、FTTH 叠加信息人话化、模型入口移除）、QGIS CAD 矢量 DXF 导出与闪退修复、覆盖盲区修复、验收对照。
- [S1 接口契约](docs/S1-接口契约.md) — M03 后端 REST API（:8083）+ 拓扑引擎（:9001）的接口清单：鉴权分档、逐接口入参出参、关键 DTO 字段、示例 curl，供 S2~S5 跨队联调。

> **演示数据说明**：GitHub Pages 静态站点无后端，由 `src/mock/adapter.js` + `src/mock/fixtures.js` 提供虚拟基站/项目/模板数据，`public/ftth-data.json`（卡萨布兰卡 JAD-MAR 竣工数据集）提供 FTTH 叠加图层。本地开发仍直连后端（默认不启用 mock）。

## License

MIT License
