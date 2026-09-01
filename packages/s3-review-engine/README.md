# S3 设计智能审查引擎（packages/s3-review-engine）

基于行业标准的通信基建设计智能审查模块，属 xind2 monorepo 子赛题3（S3）。本目录已对齐仓库规范，可直接合入 `main`。

## 1. 目录结构

```
packages/s3-review-engine/
├── backend/        # Spring Boot 后端（artifactId: s3-review-engine）
│   ├── pom.xml
│   └── src/main/java/com/comm/s3/...
│   └── src/main/resources/
│       ├── application.yml
│       └── db/migration/        # Flyway 迁移（V1 建表 / V2 灌规则）
├── rules/          # Python FastAPI 规则引擎（内部调用，端口 8000）
│   ├── main.py
│   ├── app/
│   └── requirements.txt
└── frontend/       # Vue3 + Vite 子模块（iframe 嵌入 m06-portal，base=/modules/s3，hash 路由）
    ├── vite.config.js   # base: '/modules/s3/'
    ├── .gitignore
    └── src/
        ├── views/Workbench.vue   # 门户「智能审查」统一入口（三 tab：安全规范/资源冲突/审查报告）
        ├── router/index.js       # createWebHashHistory；/work-order 为入口，/report/:id 独立路由
        ├── main.js               # 监听门户 postMessage({type:'TOKEN'}) 注入 JWT
        └── api/request.js        # 401 不再跳 /login（登录由门户统一处理）
```

## 2. 技术栈与依赖

- Java 21（编译目标 17）/ Spring Boot 3.1.10 / MyBatis-Plus 3.5.5 / OkHttp 4.12.0 / OpenPDF 1.3.11
- 父 POM：`com.comm:comm-platform-parent:1.0.0`（提供依赖管理与插件）
- 共享：`com.comm:shared-backend`（提供 `SecurityAutoConfiguration` JWT 校验、`application-shared.yml`、统一 Result/异常）
- Python：FastAPI（内部调用，不经 Nginx 对外暴露）

## 3. 构建（在仓库根目录）

```bash
# 仅编译本模块（含父 POM 依赖）
mvn compile -pl packages/s3-review-engine/backend -am -DskipTests

# 打包
mvn package -pl packages/s3-review-engine/backend -am -DskipTests
```

> 注意：模块 `pom.xml` 已对齐骨架 `java.version=21`（CLAUDE.md：JDK 21 / 编译目标 17）。集成构建需 JDK 21；本地仅自测可用 17。

## 4. 环境变量（均在 application.yml 以 `${ENV:default}` 读取，禁止硬编码）

| 变量 | 说明 | 默认 |
|------|------|------|
| `JWT_SECRET` | 共享 JWT 密钥（≥32字符），由 shared 校验 | 需团队下发 |
| `MYSQL_URL` / `MYSQL_USER` / `MYSQL_PASSWORD` | 数据源（库名 `comm_platform`） | localhost/root/CHANGE_ME |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | 三级缓存 Redis | localhost/6379/空 |
| `S3_PYTHON_ENGINE_URL` | Python 引擎内部地址 | http://localhost:8000/api/v1/s3/review/check |
| `SERVER_PORT` | 后端端口 | 8089 |
| `PDF_FONT_PATH` | PDF 中文嵌入字体 | C:/Windows/Fonts/msyh.ttc |

## 5. 认证模型（已对齐规范）

- **禁止自建 SecurityConfig**：JWT 校验由 `shared-backend` 的 `SecurityAutoConfiguration` 自动装配（密钥读 `JWT_SECRET` 环境变量）。
- **Token 签发**：统一由 `m01-auth`（端口 8080）完成；本模块只校验不签发（已移除本地 `AuthController` 登录/签发）。
- **公开接口**（`security.permit-paths`）：`/api/v1/s3/health/**`、`/api/v1/s3/internal/**`、以及 S1 机器推送 `/api/v1/s3/review/s1/receive`。
- **写操作门控**：规则增删改（`/api/v1/s3/review/rule` 的 POST/PUT/DELETE）加 `@PreAuthorize("hasRole('ADMIN')")`，需 `shared` 的方法级安全已启用（标准 starter 默认开启）。
- 前端登录应改为调用 `m01-auth` 获取 token，再带 `Authorization: Bearer <jwt>` 访问本模块。

## 6. 数据库（Flyway 自动迁移）

- 库名 `comm_platform`（与团队统一库一致，表前缀 `s3_`）。
- 启动时 Flyway 自动执行：
  - `V1__init_s3_schema.sql`：建 `s3_safety_rule` / `s3_review_task` / `s3_review_result`（均 `IF NOT EXISTS`，无 DROP）。
  - `V2__init_s3_rules.sql`：`INSERT IGNORE` 灌入 24 条行业规则（含 GD-001 埋深），幂等。
- 历史表：`flyway_schema_history_s3`（每模块独立）。

## 7. 本地运行（开发联调）

```bash
# 1) Python 引擎（先于 Java 启动）
cd packages/s3-review-engine/rules
pip install -r requirements.txt
uvicorn main:app --port 8000

# 2) Java 后端
mvn -pl packages/s3-review-engine/backend -am spring-boot:run

# 3) 前端（注意 base=/modules/s3，需带路径访问）
cd packages/s3-review-engine/frontend
npm install && npm run dev    # 打开 http://localhost:5189/modules/s3/  （详见第 8 节）
```

## 8. 前端 iframe 集成（m06-portal 子模块）

本模块前端**不是独立站**，而是被 `m06-portal`（统一前端门户，端口 5173）以 **iframe 聚合**方式嵌入的子模块。导航栏的「智能审查」与工作台「智能审查(S3)」卡片均由门户渲染，点击后通过 `iframeUrlMap` 跳转到本模块的 `/#/work-order`。

### 8.1 前端已做的适配（满足门户契约）

| 契约点 | 实现 |
|--------|------|
| 基路径 | `vite.config.js` → `base: '/modules/s3/'`；dev/build 均在此路径下服务 |
| 路由模式 | `createWebHashHistory()`；门户拼接 URL 为 `/modules/s3/#/work-order` |
| 入口路由 | `/work-order` → `Workbench.vue`（el-tabs 三页签：安全规范审查 / 资源冲突检测 / 审查报告），分别对应 `TaskList` / `RuleManage` / `ReviewReport` |
| 深度链接 | 保留 `/report/:taskId?` 独立路由（任务列表「报告」按钮与报告页切换任务时直跳） |
| 登录/导航 | 不内置 `Login` 与侧栏顶栏（已删除 `Layout.vue`/`Login.vue`/`SystemInfoDrawer.vue`），由门户提供 chrome |
| Token 注入 | `main.js` 监听 `window.message`：收到 `{ type:'TOKEN', token, userInfo }` 写入 `localStorage`；`request.js` 每次请求自动带 `Authorization: Bearer <jwt>` |
| 401 行为 | 清除本地凭证并提示「请在门户重新登录」，不再跳不存在的 `/login` |

### 8.2 需要 m06-portal 侧配合（不在本模块范围内，按 [SHARED] PR 由门户 owner 处理）

1. `m06-portal/.env.production` 增加 `VITE_FE_S3=/modules/s3`（生产静态资源路径）。
2. `m06-portal/.env.development` 增加 `VITE_FE_S3=http://localhost:5189/modules/s3`（本地联调）。
3. 门户 `MainLayout.vue` 的 `iframeUrlMap` 已含 `'review_*': moduleUrl('s3','work-order')`，无需改；若 s3 未配置则自动回退 m04（渐进迁移策略）。
4. 部署时把本模块 `npm run build` 的 `dist/` 拷贝到门户可访问的 `/modules/s3/` 目录（Nginx 或静态托管）。

### 8.3 本地联调（无门户也能验证）

```bash
cd packages/s3-review-engine/frontend
npm install && npm run dev
# 打开 http://localhost:5189/modules/s3/  （注意带 base 路径）
# 因无门户 postMessage，需手动在浏览器控制台注入 token 以联调业务接口：
#   localStorage.setItem('token','<m01-auth签发的jwt>')
```

## 9. 上传集成到 xind2（操作清单）

本目录即为可直接合入 `packages/s3-review-engine/` 的内容。提交前确认只改动本模块：

```bash
git clone https://github.com/zhen237/xind2.git
cd xind2
git checkout -b feat/s3-review-engine           # 分支名 feat/ 前缀（CLAUDE.md §4.4）
# 将本 packages/s3-review-engine/ 目录整体覆盖/复制到 xind2 对应位置
git add packages/s3-review-engine
git diff main --stat                           # 确认只碰 s3-review-engine/
git commit -m "feat(s3): 设计智能审查引擎合入（后端/rules/前端+Flyway+shared认证）"
git push -u origin feat/s3-review-engine       # 禁止 --force
# 在 GitHub 提 PR → CODEOWNERS 已 @w0722 自动评审
```

> 提交类型与 scope 规范：`<type>(s3): <subject>`（s3 为子赛题3 模块 scope），type ∈ feat|fix|docs|refactor|test|chore。
