# 通信基建数智化平台

> **🌐 在线演示（Live Demo）**: http://124.220.37.119/
> 云服务器完整部署（前后端真实联通），进入平台门户后可切换体验 S1~S5 全部子赛题模块。

## 比赛信息

**比赛名称**: 挑战杯"揭榜挂帅"擂台赛 - 通信基建工程数智化设计与交付关键技术
**发榜单位**: 烽火通信科技股份有限公司
**截止时间**: 2026年9月15日

## 在线演示（Live Demo）

平台部署在云服务器上，前后端真实联通，打开门户即可体验全部子赛题模块：

> **演示地址**: http://124.220.37.119/
>
> 打开门户后，可从导航进入各模块：

| 模块 | 入口 | 说明 |
|------|------|------|
| S1 三维智能设计 | http://124.220.37.119/modules/m03/ | 三维设计页 + FTTH 叠加；QGIS 插件设计成果一键上传 |
| S2 多源数据融合 | http://124.220.37.119/modules/s2/ | CAD/GIS 多源异构工程数据融合 |
| S3 设计智能审查 | http://124.220.37.119/modules/s3/ | 智能审查（电力/防雷/结构/电磁/通用/管线 6 类规则） |
| S4 BOM 清单转化 | http://124.220.37.119/modules/s4/ | 设计成果 → 设备清单 + 工程量报表 |
| S5 施工智能监管 | http://124.220.37.119/modules/s5/ | 施工监控 + AI 智能分析 + 数字孪生 |

> **S1 演示提示**：进入三维设计页后点顶部「加载数据」渲染基站（卡萨布兰卡 JAD-MAR 数据集坐标），再打开右上角「FTTH 叠加」开关叠加光交箱/光缆图层。

## 项目简介

本平台面向通信基建工程的**设计与交付**场景，由五名成员各负责一个子赛题模块，串成一条完整的业务数据链路：

**S2 多源数据融合（CAD/GIS）→ S1 智能设计（QGIS 插件 + 三维）→ S3 设计智能审查 → S4 设备清单与工程量转化 → S5 施工过程监管**

各模块通过统一认证（JWT）与 REST 接口衔接：QGIS 插件完成设计后自动上传至三维设计模块，设计任务完成后自动推送智能审查，审查结果可被清单转化模块拉取，最终汇聚到施工监管。平台采用微服务架构，共 11 个后端服务 + 5 个 Python 计算引擎 + 统一门户，已整体部署上线。

### 子赛题覆盖（全5个）

| 子赛题 | 负责人 | 说明 | 状态 |
|--------|--------|------|------|
| 子赛题1 | **高** | 面向专业GIS平台的通信工程智能辅助设计 | ✅ 已上线 |
| 子赛题2 | **庞** | 多源异构工程数据融合（CAD/GIS） | ✅ 已上线 |
| 子赛题3 | **王** | 基于行业标准的设计智能审查 | ✅ 已上线 |
| 子赛题4 | **任** | 设计成果向施工指令的自动转化（BOM） | ✅ 已上线 |
| 子赛题5 | **李** | 施工过程智能监管（CV+数字孪生） | ✅ 已上线 |

## 架构设计

### 模块划分

| 模块 | 名称 | 本地端口 | 归属 | 说明 |
| --- | --- | --- | --- | --- |
| M01 | 统一认证服务 | 8080 | 共享 | 用户登录、JWT 签发、菜单管理 |
| M03 | BIM+GIS 三维设计引擎 | 8083/5174 | S1-高 | 三维场景、基站设计、覆盖分析、任务式数据接口 |
| m03-topology-engine | 拓扑计算引擎 (Python) | 9001 | S1-高 | 信号传播模型、拓扑计算（FastAPI，仅本机回环） |
| m03-llm-service | LLM 服务 (Python) | — | S1-高 | 大模型辅助服务 |
| M04 | 数智化交付与工作流 | 8084 | 共享 | 工单/验收/交付包基础能力（已按赛题拆分至 S2~S5） |
| M05 | 数字孪生与智慧运维 | 8085 | S5-李 | 设备监控、告警管理 |
| M06 | 统一前端门户 | 5173 | 共享 | 登录页、动态菜单、模块导航 |
| M07 | CV视觉检测引擎 | 8088 | S5-李 | 安全帽检测、围挡检测、违章识别 |
| Screen | 数据大屏聚合 | 8087 | 共享 | 各赛题数据聚合展示 |
| S2 | CAD数据融合 | 8082/5182 | S2-庞 | DWG/DXF解析、坐标系转换（含 Python 融合引擎） |
| S3 | 设计智能审查 | 8089/5189 | S3-王 | 规则引擎、安全审查（SQL 种子规则 + 代码内置规则） |
| S4 | BOM施工指令转化 | 8090/5190 | S4-任 | 设备清单 BOM、工程量与造价报表（含 Python 计算引擎） |
| S5 | 施工智能监管 | 8091/5191 | S5-李 | 施工任务监管、AI 助手、数字孪生（Node.js 后端） |
| QGIS插件 | 基站智能设计 | - | S1-高 | FTTH/基站协同设计、覆盖计算、DXF 图纸导出 |

> 生产环境由 nginx 统一反代（:80），入口 `/` 与 `/modules/{模块}/`，各服务端口与本地开发端口不同，开发者无需关心。

### 技术栈

- **前端**: Vue 3 + Vite + Element Plus + Pinia；三维场景 CesiumJS
- **后端**: Spring Boot + MyBatis-Plus + JWT（JDK 21）；S5 施工监管后端为 Node.js
- **QGIS插件**: Python + PyQGIS + PyQt5
- **计算引擎**: Python + FastAPI（拓扑传播模型、CAD 融合、造价计算等）
- **AI 能力**: YOLOv8 视觉检测（安全帽/围挡）；S5 AI 智能助手（大模型问答，注入实时业务数据）
- **数字孪生**: Unity WebGL
- **数据**: MySQL 8（业务库 `comm_platform`，Flyway 自动迁移）+ Redis（缓存）
- **部署**: 腾讯云 Lighthouse + nginx 统一反代，前后端分离部署

> 说明：仓库中保留了 MinIO / InfluxDB / EMQX 的依赖定义但**当前未接入**（文件上传落服务器本地磁盘，业务数据全部落 MySQL）；本地联调无需安装这三样。

## 快速开始

### 1. 环境要求

| 依赖 | 版本 | 下载地址 |
| --- | --- | --- |
| JDK | 21 | [Adoptium Temurin 21](https://adoptium.net/temurin/releases/?version=21) |
| Maven | 3.9+ | [Apache Maven](https://maven.apache.org/download.cgi) |
| MySQL | 8.0+ | [MySQL Community Server](https://dev.mysql.com/downloads/mysql/) |
| Redis | 7.0+ | [Redis Windows](https://github.com/redis-windows/redis-windows/releases) |
| Node.js | 18+ | [Node.js](https://nodejs.org/) |
| Python | 3.11（仅拓扑引擎/QGIS 插件开发需要） | [Python](https://www.python.org/) |

### 2. 最少服务启动（推荐）

**必须启动的服务：**

| 服务 | 端口 | 作用 | 启动命令 |
| --- | --- | --- | --- |
| MySQL | 3306 | 数据库 | 作为 Windows 服务自动启动 |
| Redis | 6379 | 缓存 | 作为 Windows 服务自动启动 |
| M01 认证服务 | 8080 | 用户认证 | `mvn spring-boot:run` |
| M06 前端门户 | 5173 | 用户界面 | `npm run dev` |

**按需启动**（做哪个子赛题就启动对应模块的后端与前端，端口见「模块划分」表）：

```bash
# 1. 先安装共享后端（各模块依赖它，首次必须执行）
cd packages/shared/backend
mvn install -DskipTests

# 2. 启动任意后端模块（示例：M03）
cd packages/m03-bim-gis/backend
mvn spring-boot:run

# 3. 启动对应前端（示例：M03）
cd packages/m03-bim-gis/frontend
npm install
npm run dev
```

> - 数据库表结构由各模块 **Flyway** 在首次启动时自动创建迁移，无需手工导表；`scripts/init-db.sql` 提供基础账号等种子数据。
> - 后端启动请**显式指定端口**（如 `--server.port=8083`），避免端口冲突。
> - M03 内部接口需携带 `X-API-Key` 请求头（QGIS 插件与跨模块调用），默认值见 `.env.example`。

### 3. 访问地址（本地）

| 服务 | 地址 |
| --- | --- |
| 前端门户 | http://localhost:5173 |
| M01 API | http://localhost:8080/api/m01/ |
| M03 API | http://localhost:8083/api/m03/ |

### 4. 登录信息

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
│   ├── m03-topology-engine/ # 拓扑计算引擎 Python（S1-高）
│   ├── m03-llm-service/    # LLM 服务 Python（S1-高）
│   ├── m04-delivery/       # 数智化交付（共享，基础能力）
│   │   ├── backend/
│   │   └── frontend/
│   ├── m05-twin-ops/       # 数字孪生与智慧运维（S5-李）
│   │   └── backend/
│   ├── m06-portal/         # 统一前端门户（共享）
│   ├── m07-cv-engine/      # CV视觉检测引擎（S5-李）
│   ├── s2-cad-fusion/      # 多源数据融合（S2-庞），含 Python 引擎
│   ├── s3-review-engine/   # 设计智能审查（S3-王）
│   ├── s4-bom-transform/   # BOM施工指令转化（S4-任），含 Python 引擎
│   ├── s5-construction-monitor/ # 施工智能监管（S5-李，Node.js 后端）
│   ├── screen/             # 数据大屏（共享）
│   └── shared/             # 共享组件/工具类（共享）
├── qgis-plugin/            # QGIS基站智能设计插件
│   ├── design_engine/      # 设计引擎
│   ├── models/             # 数据模型
│   └── layers/             # 图层管理
├── deploy/                 # 部署配置（nginx / db / scripts）
├── docs/                   # 项目文档
├── scripts/                # 初始化与部署脚本
├── .env.example            # 环境变量模板（MYSQL_PWD / M03_API_KEY）
└── .gitignore
```

## 核心功能

### M01 统一认证
- 用户登录/登出
- 安全令牌验证（JWT）
- 动态菜单管理
- 角色权限控制

### QGIS插件 - 基站智能设计（子赛题1）
- FTTH 光纤与蜂窝基站协同设计（七步引导式流程）
- 信号覆盖范围计算（专业传播模型）与覆盖盲区补盲补热
- 智能避让检测（避开建筑物、水域、生态保护区）
- 标准图纸导出（DXF 矢量格式）
- 设计成果任务式上传至 M03（`POST /tasks` → 本地数据 → 生成），S4 即刻可见

### M03 BIM+GIS三维设计（子赛题1）
- 三维可视化展示（基于 CesiumJS）
- 基站/机房站点标记、FTTH 叠加图层（光交箱/光缆）
- 信号覆盖热力图
- 设计任务数据落库（站点、管线、工程量），供 S3 审查与 S4 清单消费

### S2 多源数据融合（子赛题2）
- DWG/DXF 图纸解析
- 多源异构工程数据融合
- 坐标系转换

### S3 设计智能审查（子赛题3）
- 审查规则库：SQL 种子规则 + 代码内置规则，覆盖电力/防雷/结构/电磁/通用/管线 6 类
- S1 设计任务完成后自动推送审查（无需人工触发）
- 审查结果按规则编号归类，支持 S4 拉取

### S4 BOM 清单转化（子赛题4）
- 设计成果 → 设备清单（BOM）自动生成
- 工程量报表与造价估算
- 拉取 S3 审查结果，数据来源精确标注（真实成果/演示数据）

### S5 施工智能监管（子赛题5）
- 施工任务校验与监管流程
- AI 智能助手（大模型问答，自动注入实时业务数据）
- 数字孪生大屏（Unity WebGL）

### M07 AI视觉检测引擎（子赛题5）
- 安全帽佩戴检测
- 施工围挡检测
- 违章行为识别

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

### 创建设计任务（M03，供 QGIS 插件/跨模块调用）

```bash
POST /api/m03/design/tasks
X-API-Key: <M03_API_KEY>
Content-Type: application/json
```

## 配置说明

复制 `.env.example` 为 `.env` 并修改配置：

```bash
MYSQL_PWD=your-mysql-password
M03_API_KEY=your-internal-api-key
```

- `MYSQL_PWD`：MySQL root 密码（部署脚本与各服务读取）
- `M03_API_KEY`：M03 内部接口 `/api/m03/design/**` 的 API Key，QGIS 插件与内部服务调用时须携带 `X-API-Key` 请求头

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
3. **表命名**: 按模块前缀命名（`m01_`, `m03_`, `s2_` 等），Flyway 历史表按模块独立（`flyway_schema_history_<模块>`）
4. **代码风格**: 使用 Lombok，遵循 Spring Boot 规范；全部后端模块统一 JDK 21

## 分支与目录对应约定（常驻）

每个子赛题有**独立常驻开发分支**，只改自己负责的 `packages/<模块>` 目录，合入 `main` 后**不删分支**。

| 分支 | 负责人 | 负责目录（仅这些） | 说明 |
|------|--------|--------------------|------|
| `feat/s1-design-dock-refactor` | 高 | `qgis-plugin/`, `packages/m03-bim-gis/`, `packages/m03-topology-engine/`, `packages/m03-llm-service/` | S1 长期开发分支，**必须常驻远程** |
| `feat/s2-cad-fusion` | 庞 | `packages/s2-cad-fusion/` | |
| `feat/s3-review-engine` | 王 | `packages/s3-review-engine/` | |
| `feat/s4-bom-transform` | 任 | `packages/s4-bom-transform/` | |
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

> **演示说明**：线上演示为云服务器完整部署（前后端真实联通，业务数据落 MySQL）。本地开发时 S1 前端默认直连后端（不启用 mock），`src/mock/`（虚拟基站/项目/模板数据）与 `public/ftth-data.json`（卡萨布兰卡 JAD-MAR 竣工数据集）仅在离线场景手动开启。

## License

MIT License
