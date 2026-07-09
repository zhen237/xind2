# CLAUDE.md — AI 协作指引

> 本文件是任何 AI 工具（Claude / Cursor / WorkBuddy / Copilot）进入本项目的**强制入口**。
> 读完后你应该能独立完成 80% 的任务，无需全量扫描代码库。

---

## 1. 项目身份

**项目名称**: 通信基建数智化全流程平台
**赛事**: 挑战杯"揭榜挂帅" — XA-202610 通信基建工程数智化设计与交付关键技术
**子赛题覆盖**: 子赛题1(QGIS智能设计) / 子赛题3(设计智能审查) / 子赛题4(施工指令转化) / 子赛题5(施工智能监管)
**样例数据区域**: 山西运城学院 (111.0°E, 35.0°N)

---

## 2. 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| Java 后端 | Spring Boot + MyBatis-Plus + MySQL 8 | JDK 17 / SB 3.1.10 |
| 前端 | Vue 3 + Vite + Element Plus + CesiumJS + ECharts | Vue 3.4 / Vite 5 |
| QGIS 插件 | Python + QGIS API | QGIS 3.44 / Python 3.10+ |
| AI 视觉 | Python FastAPI + YOLOv8 | FastAPI 0.100+ |
| 基础设施 | Redis + MinIO + Nginx + Flyway | — |

---

## 3. 模块地图

```
xind2/
├── packages/
│   ├── shared/backend/          # 共享: Security/JWT/Cache/异常/Result 包装
│   ├── m01-auth/backend/        # 统一认证 (端口 8080)
│   ├── m03-bim-gis/             # BIM+GIS 三维设计 (端口 8083 / 前端 5174)
│   ├── m04-delivery/backend/    # 数智化交付与工作流 (端口 8084)
│   ├── m05-twin-ops/backend/    # 数字孪生运维 (端口 8085)
│   ├── m06-portal/              # 统一前端门户 (端口 5173)
│   ├── m07-cv-engine/           # AI 视觉检测 (端口 8088, Python)
│   └── screen/backend/          # 数据大屏聚合层 (端口 8086)
├── qgis-plugin/                 # QGIS 基站智能设计插件
│   ├── ui/                      # 面板 UI (design_dock.py 主文件 ~2200行)
│   ├── design_engine/           # 蜂窝网格/覆盖/管线/避障/导出
│   ├── layers/                  # 图层管理 (基站/管线/热力图)
│   ├── models/                  # 数据模型
│   └── tools/                   # 地图工具
├── docs/                        # 项目文档
├── scripts/                     # SQL/启动脚本/测试
├── pom.xml                      # 父 POM (6 个 Java 模块)
└── .env.example                 # 环境变量模板
```

### 模块职责边界（禁止越界）

| 模块 | 负责内容 | 不负责 |
|------|----------|--------|
| shared | Security Starter / Cache / 异常处理 / Result 包装 | 业务逻辑 |
| M01 | 用户认证 / JWT 签发 | 基站设计 / 管线 |
| M03 | 参数化设计 / 站点生成 / 覆盖分析 / 管线路由 | 交付工作流 |
| M04 | 交付工作流 / BOM / 设计审查 / 施工监管 | 三维渲染 |
| M05 | 数字孪生 / 设备监控 / 告警 | 设计生成 |
| M06 | 统一门户 / iframe 聚合 / 路由 | 后端业务 |
| M07 | CV 检测 / YOLO 推理 | Java 业务 |
| Screen | 跨模块数据聚合 (通过 REST 调 M04/M05) | 直查数据库 |
| QGIS | 基站拓扑 / 覆盖热力图 / 管线 / 图纸导出 | 后端 API |

---

## 4. 构建命令

### Java 后端（多模块 Maven）

```bash
# 全量编译（根目录执行）
cd xind2
mvn compile -DskipTests

# 单模块编译
mvn compile -pl packages/m04-delivery/backend -am -DskipTests

# 全量打包
mvn package -DskipTests
```

### 前端

```bash
# M06 统一门户
cd packages/m06-portal
npm install && npm run dev          # 开发 → http://localhost:5173

# M03 三维前端
cd packages/m03-bim-gis/frontend
npm install && npm run dev          # 开发 → http://localhost:5174
```

### QGIS 插件

```python
# 无构建步骤，直接在 QGIS 中加载
# 插件 → 管理和安装插件 → 从文件安装 → 选择 qgis-plugin/ 目录
# 开发调试: 重新加载插件即可生效
```

### Python (M07)

```bash
cd packages/m07-cv-engine
pip install -r requirements.txt
python main.py                      # → http://localhost:8088
```

### 基础设施

```bash
# MySQL 初始化
mysql -u root -p < scripts/init-mysql.sql

# 启动全部服务 (Windows)
scripts/start-all.bat

# Nginx 配置
# 配置文件: scripts/nginx.conf (含限流/安全头/gzip)
```

---

## 5. 代码规范

### Java
- **规范**: 阿里巴巴 Java 开发手册
- **命名**: 类 PascalCase / 方法 camelCase / 常量 UPPER_SNAKE / 包名全小写
- **异常**: 禁止 `throw new RuntimeException()`，必须用 `BusinessException(code, msg)`
- **Controller**: 禁止 try-catch 包裹，交给 `GlobalExceptionHandler` 统一处理
- **日志**: 禁止 `System.out`，必须用 SLF4J `log.warn/info/error`
- **安全**: 禁止 `anyRequest().permitAll()`，必须明确列出公开接口
- **配置**: 禁止硬编码密码/密钥，必须用 `${ENV_VAR:default}` 占位

### Vue / 前端
- **风格**: Composition API (`<script setup>`)
- **命名**: 组件 PascalCase / 文件 kebab-case / 变量 camelCase
- **状态**: Pinia store，禁止全局变量
- **销毁**: Cesium/ECharts 实例必须在 `onUnmounted` 中 `dispose()`
- **安全**: `postMessage` 禁止 `targetOrigin: '*'`，必须提取具体域名
- **请求**: 统一 axios 封装， baseURL 从 `.env` 读取

### Python (QGIS 插件 / M07)
- **规范**: PEP 8
- **命名**: 函数/变量 snake_case / 类 PascalCase
- **注释**: 所有公共函数必须有中文 docstring
- **QGIS 图层**: 内存图层用 `"memory"` provider，渲染器优先 `GraduatedSymbolRenderer`

### 提交规范

```
<type>(<scope>): <subject>

类型: feat | fix | docs | style | refactor | test | chore
范围: m01 | m03 | m04 | m05 | m06 | m07 | qgis | shared | screen | docs
```

---

## 6. 架构规则（Phase 3 重构后）

### 安全架构
- **统一 Security Starter**: `shared-backend` 中的 `SecurityAutoConfiguration` 自动装配 JWT 过滤器
- **各模块禁止自建 SecurityConfig**，通过 `application.yml` 中 `security.public-paths` 配置公开接口
- **JWT**: 统一 `JwtAuthenticationFilter`，密钥从 `JWT_SECRET` 环境变量读取（≥32字符）

### 数据库架构
- **逻辑隔离**: 每个模块独立数据库 schema，禁止跨模块直查表
- **Screen 模块**: 通过 REST API 调用 M04/M05，禁止直连它们的数据库
- **迁移**: Flyway 管理，每模块独立 `flyway_schema_history` 表
- **建表**: 禁止 `DROP TABLE`，必须 `CREATE TABLE IF NOT EXISTS`

### 缓存架构
- **Redis**: 双 TTL 策略 — 默认 5 分钟 / longCache 30 分钟
- **注解**: `@Cacheable("longCache")` 用于低频变更数据
- **配置**: `shared-backend` 中的 `CacheConfig` 统一管理

### 日志架构
- **格式**: 统一 `logback-spring.xml`，含 traceId MDC
- **滚动**: 100MB 滚动，保留 30 天
- **环境**: dev 控制台输出 / prod 仅文件

### 配置管理
- **环境变量**: `.env.example` 定义 18 个必需变量
- **共享配置**: `application-shared.yml` 放公共 Jackson/JWT/Redis 配置
- **敏感信息**: 一律 `${ENV_VAR}`，禁止硬编码

---

## 7. 子代理使用指南

本节指导如何利用子代理（Sub-agent）在本项目中进行任务分发和上下文隔离。

### 7.1 什么时候用子代理

| 场景 | 用子代理 | 不用子代理 |
|------|----------|------------|
| 搜索 "所有 SecurityConfig 文件" | ✅ Explore Agent | — |
| 修改 1 个文件的 1 个函数 | — | ✅ 直接改 |
| 审查 M04 + M05 的 API 一致性 | ✅ 2 个并行 Agent | — |
| 理解 QGIS 插件渲染流程 | ✅ Explore Agent | — |
| 修复 1 个已知 Bug | — | ✅ 直接改 |
| 跨模块重构（如安全统一） | ✅ 每模块 1 个 Agent | — |
| 读 1 个文件回答问题 | — | ✅ 直接 Read |

### 7.2 子代理类型选择

```
┌─────────────────────────────────────────────────┐
│  需要搜索/阅读/理解代码？                         │
│  ├─ 是 → Explore Agent（只读，快，不污染主上下文）│
│  └─ 否 → 需要写文件？                             │
│           ├─ 是 → general-purpose Agent（可编辑） │
│           └─ 否 → 直接在主对话处理                 │
└─────────────────────────────────────────────────┘
```

**Explore Agent** — 只读搜索，适合：
- "找出所有硬编码密码"
- "M04 有哪些 Controller？"
- "QGIS 插件怎么生成管线？"
- "哪些模块有 permitAll？"

**general-purpose Agent** — 可读可写，适合：
- "给 M04 加一个 BOM 生成接口"
- "重构 QGIS 热力图渲染逻辑"
- "给 M05 补充 Flyway 迁移脚本"

### 7.3 上下文隔离原则

子代理有独立的上下文窗口，**主对话不会看到子代理读过的文件内容**。利用这一点：

1. **避免上下文爆炸**: 让 Explore Agent 搜索 50 个文件，只返回 200 字摘要，主对话只消耗 200 token 而非 50000
2. **并行任务**: 同时派 3 个 Agent 分别查 M03/M04/M05，互不干扰
3. **指令要自包含**: 子代理看不到当前对话，prompt 必须包含完整背景

**好的子代理 prompt 示例**:
```
项目路径: D:\homework\xind2\xind2
任务: 找出 M04-delivery 模块所有 Controller 的 API 端点，
      列出每个端点的 HTTP 方法、路径、入参、出参。
      不需要修改任何文件，只返回结构化列表。
      重点关注: 是否有缺失的输入校验注解(@Valid/@NotNull)。
```

**坏的子代理 prompt 示例**:
```
帮我看看之前说的那个模块的接口有没有问题
```
（子代理不知道"之前"是什么，也不知道"那个模块"是哪个）

### 7.4 本项目推荐的子代理工作流

#### 场景 A: 跨模块安全审查

```
主代理: 创建 3 个并行 Explore Agent
  ├─ Agent-1: "审查 M03 的 SecurityConfig，列出所有 permitAll 路径"
  ├─ Agent-2: "审查 M04 的 Controller，找出缺失 @Valid 的端点"
  └─ Agent-3: "审查 M05 的 application.yml，找出硬编码密码"

主代理: 汇总 3 个 Agent 的结果 → 统一修复方案 → 逐模块修改
```

#### 场景 B: QGIS 插件 Bug 修复

```
主代理: 先派 1 个 Explore Agent
  → "阅读 qgis-plugin/ui/design_dock.py 的 _create_heatmap_layer 方法，
     总结当前渲染逻辑、标记尺寸、图层添加方式，不超过 300 字"

主代理: 基于摘要直接修改，不需要把 2200 行文件加载到主上下文
```

#### 场景 C: 新功能开发（如子赛题3 设计审查）

```
主代理:
  1. Explore Agent → "阅读 docs/烽火通信-子赛题1345开发方案.md 中子赛题3部分，
     总结需要的 4 个审查引擎、输入输出、API 契约"
  2. Explore Agent → "扫描 M04 现有结构，列出已有 package、Controller、Service"
  3. 主代理 → 基于两个摘要设计实现方案
  4. general-purpose Agent → "按以下方案在 m04-delivery/backend 创建 review 包..."
```

### 7.5 自定义 Agent 配置

在 `.workbuddy/agents/` 目录下可以创建项目级自定义 Agent（Markdown 格式）:

```
.workbuddy/agents/
├── qgis-dev.md          # QGIS 插件开发专用 Agent
├── java-reviewer.md     # Java 代码审查 Agent
└── frontend-dev.md      # Vue 前端开发 Agent
```

每个文件定义 Agent 的角色、可用工具、约束条件。WorkBuddy 会自动发现并加载。

---

## 8. 常见陷阱清单

这些 Bug 已经修复过，AI 工具**不要重新引入**：

### 安全类
| 陷阱 | 正确做法 | 已修复位置 |
|------|----------|------------|
| `anyRequest().permitAll()` | 明确列出公开接口，其余 `authenticated()` | 所有模块 SecurityConfig |
| 硬编码密码 `Admin@123` | `${MYSQL_PASSWORD:root123}` | application.yml |
| `postMessage(data, '*')` | 提取具体 targetOrigin | MainLayout.vue |

### QGIS 类
| 陷阱 | 正确做法 |
|------|----------|
| `QgsCategorizedSymbolRenderer` 匹配浮点 RSRP | 用 `QgsGraduatedSymbolRenderer` + `QgsRendererRange` |
| `QgsRubberBand` 用于导出图纸 | 用临时 `QgsVectorLayer` polygon |
| 管线单图层名共存冲突 | 路由类型特定名: `基站-管线关联-直连` / `-曼哈顿` |
| 热力图标记 2-6px 看不见 | 6-14px + `insertLayer(0)` 置顶 |
| `QgsMarkerLineSymbolLayer(QgsMarkerSymbol)` | 构造参数是 `bool`，用 `setSubSymbol()` |

### 架构类
| 陷阱 | 正确做法 |
|------|----------|
| Screen 直查 M04/M05 数据库 | 通过 REST API 调用 |
| `DROP TABLE` 建表 | `CREATE TABLE IF NOT EXISTS` |
| 各模块自建 SecurityConfig | 用 shared SecurityAutoConfiguration |
| `System.out` 打日志 | SLF4J `log.warn/info/error` |
| `throw new RuntimeException()` | `throw new BusinessException(code, msg)` |

---

## 9. 关键文件速查

| 需要找什么 | 去哪里看 |
|------------|----------|
| 赛题要求 | `docs/烽火通信-子赛题1345开发方案.md` |
| 数据库表结构 | `docs/数据库设计.md` |
| API 接口定义 | `docs/API接口文档.md` |
| 环境变量 | `.env.example` (根目录) |
| Nginx 配置 | `scripts/nginx.conf` |
| SQL 初始化 | `scripts/init-mysql.sql` |
| QGIS 插件主 UI | `qgis-plugin/ui/design_dock.py` |
| QGIS 设计引擎 | `qgis-plugin/design_engine/` |
| 共享安全配置 | `packages/shared/backend/.../security/` |
| 共享缓存配置 | `packages/shared/backend/.../common/CacheConfig.java` |
| 架构审查报告 | `.workbuddy/architecture-review-report.md` |

---

## 10. 当前项目状态

| 子赛题 | 完成度 | 关键状态 |
|--------|--------|----------|
| 子赛题1 (QGIS智能设计) | ~95% | 6 Bug 已修复 + 3 Bug 本轮修复完成 |
| 子赛题3 (设计智能审查) | 0% | M04 缺 review 包，4 个审查引擎未实现 |
| 子赛题4 (施工指令转化) | 0% | QGIS 缺 bom_generator，M04 缺 bom 包 |
| 子赛题5 (施工智能监管) | 0% | M07 只有 README，M04 缺 surveillance 包 |

**Phase 3 架构重构**: a/b/c 三阶段全部完成 (13/13)，包含安全统一/Flyway/Redis/Nginx/Actuator。

---

## 11. AI 工具使用流程

```
1. 读取本文件 (CLAUDE.md)              ← 你在这里
2. 根据任务定位模块（第3节模块地图）
3. 需要搜索代码 → 派 Explore Agent（第7节）
4. 需要修改代码 → 直接改或派 general-purpose Agent
5. 遵守代码规范（第5节）
6. 避开常见陷阱（第8节）
7. 完成后更新 .workbuddy/memory/YYYY-MM-DD.md
```

---

*本文件最后更新: 2026-07-08 | 维护: 项目开发团队*
