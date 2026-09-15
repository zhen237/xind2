# xind2 通信基建数智化全流程平台 · 生产部署工具包

本目录包含一套**可复现**的生产部署工具，目标服务器为腾讯云 Lighthouse `124.220.37.119`（Ubuntu 22.04.5）。

> ✅ **状态：2026-09-15 已全量部署上线**。公网入口 `http://124.220.37.119/`（实测可访问，7 个前端全部 200）。
> 服务器规格：**2 vCPU / 3.7GB 内存 / 59GB 磁盘**，已加 **4GB swapfile**；防火墙仅开放 **22 / 80**，Nginx `:80` 是唯一公网入口。
>
> ❗**部署前请务必先读 §0「三大陷阱」**——本次真实部署即因它们踩坑，相关修复已内置到脚本。

---

## 0. ⚠️ 部署三大陷阱（务必先读）

### 陷阱 1：多模块共用 `comm_platform` + 各自 `baseline-on-migrate: true` → 后续模块跳过 V1（最易踩，优先阅读）
- **机制**：多个 Java 模块**共用同一个库** `comm_platform`，各自配置了 `spring.flyway.baseline-on-migrate: true`。第一个启动的模块（m01）先把库变成"非空"，Flyway 顺带建了它自己的历史表。之后启动的模块发现"库非空、但没有自己的历史表"，于是把 **baseline 记在 V1 上 → V1 被跳过**，直接从下一条迁移开始执行；而下一条迁移往往是对报表的 `ALTER TABLE`，表尚不存在 → 启动失败：
  - m03 报 `m03_design_scheme` 不存在；
  - s2 报 `s2_gis_feature` 不存在。
- **修法**：所有 Java 后端启动参数追加 **`--spring.flyway.baseline-version=0`**。baseline 落到 0，则 V1..Vn 照常执行；各模块的 V1 均为 `CREATE TABLE IF NOT EXISTS`，可重复执行，安全。
- **现状**：`deploy/scripts/start-backends.sh` **已按此修复**（提交 `d4b88f3`）。**请勿 revert 该脚本**，否则 V1 跳过问题会立即复现。

### 陷阱 2：m03 有表不在 Flyway 迁移链里（全新库部署前置必做）
- `m03_design_task`、`m03_parametric_template` **不在任何 Flyway 迁移文件中**，只存在于**仓库根目录的 `m03-fix-tables.sql`**；但 m03 的迁移 `V5` / `V7` 却对这两张表做 `ALTER`。
- 因此**全新库在启动 m03 之前必须先执行**：
  ```bash
  mysql -uroot -p*** comm_platform < m03-fix-tables.sql
  ```
- 该脚本**位于仓库根目录**（不在 `deploy/` 下），用途＝补齐 m03 缺失的基础表。**必须在 m03 首次启动前灌入**，否则 m03 的 V5/V7 会因表不存在而失败（见 §4 步骤 1.5）。

### 陷阱 3：m03 的 `V1__init_m03_schema.sql` 不完全幂等
- 其中的 `CREATE TABLE IF NOT EXISTS` 幂等，但 **`CREATE INDEX` 不幂等** → 重跑报 `Duplicate key name 'idx_m03_device_project_id'`。
- 若**必须重跑** m03 迁移，需先 `DROP` 掉 m03 相关表（或整库重建），否则 V1 会在建索引处中断。

> 相关经验：本机/开发库常因**历史遗留表**而掩盖上述"全新库才暴露"的问题 —— 因此上线前必须做 §3 的**空库演练**。

---

## 1. 架构与端口映射总表

服务器防火墙**仅开放 22 / 80 / ICMP**，因此 **Nginx `:80` 是唯一公网入口**。所有后端仅绑定 `127.0.0.1`，由 Nginx 反代 `/api/*` 转发；静态前端按子路径挂载。

### 1.1 前端子路径 + 反代映射

| 公网路径 (Nginx)        | 模块                  | 后端端口 (127.0.0.1) | 历史模式        | 说明 |
|-------------------------|-----------------------|----------------------|-----------------|------|
| `/`                     | m06-portal            | — (静态)             | HTML5 (root)    | 门户根 |
| `/modules/m03/`         | m03-bim-gis           | 8083                 | Hash            | 静态 + `/api/m03` |
| `/modules/s3/`          | s3-review-engine      | 8089                 | Hash            | 静态 + `/api/s3`、`/api/v1/s3` |
| `/modules/m04/`         | m04-delivery          | 8084                 | HTML5           | 子路径部署 |
| `/modules/s2/`          | s2-cad-fusion         | 8096                 | HTML5           | 子路径部署（应用默认 8082，但前端统一走 8096） |
| `/modules/s4/`          | s4-bom-transform      | 8090                 | HTML5           | 子路径部署 |
| `/modules/s5/`          | s5-construction-monitor | 8091              | HTML5           | 子路径部署 |

> 7 个前端（`/` + 6 个 `/modules/xx/`）上线后**全部 200 通过**。

### 1.2 反向代理前缀 → 后端

| Nginx location        | 转发目标              | 模块 |
|-----------------------|----------------------|------|
| `/api/m01`            | 127.0.0.1:8080       | m01-auth |
| `/api/m03`            | 127.0.0.1:8083       | m03-bim-gis |
| `/api/m04`            | 127.0.0.1:8084       | m04-delivery |
| `/api/m05`            | 127.0.0.1:8085       | m05-twin-ops |
| `/api/s2`             | 127.0.0.1:8096       | s2-cad-fusion |
| `/api/s3`             | 127.0.0.1:8089       | s3-review-engine |
| `/api/v1/s3`          | 127.0.0.1:8089       | s3-review-engine |
| `/api/s4`             | 127.0.0.1:8090       | s4-bom-transform |
| `/api/s5`             | 127.0.0.1:8091       | s5-construction-monitor |

> `screen` 后端 (:8087) 与 `m07-cv-engine` (:8088) **不在** Nginx 代理列表：screen 无前端公网路由（仅本地被其它模块调用），m07 为本地内部引擎（且仓库内未找到可运行入口，见 §7）。

### 1.3 本地 Python 引擎（仅 127.0.0.1，不对外、不代理）

| 引擎 (目录)                    | 端口  | 入口模块 (uvicorn)   | 调用方 |
|--------------------------------|-------|----------------------|--------|
| m03-topology-engine            | 9001  | `main`               | m03 后端 |
| m03-llm-service                | 9002  | `main`               | m03 后端 |
| s2-cad-fusion/engine           | 8092  | `cad_engine.server`  | s2 后端 |
| s3-review-engine/rules         | 8000  | `main`               | s3 后端 (S3_PYTHON_ENGINE_URL 默认 `http://localhost:8000`) |
| s4-bom-transform/engine        | 8100  | `main`               | s4 后端 |
| m07-cv-engine                  | 8088  | （未确认）           | 未启用（见 §7） |

> ⚠️ **每个引擎必须使用独立 venv**：s4-engine 需 `fastapi<0.110`，而 m03 / s3 固定 `0.115.0`，若装进同一个系统 Python 会相互冲突。`start-backends.sh` 中 `start_py` 已改为直接调用 **`<engine>/.venv/bin/python3`**（见 §9），不要改回 `source activate`。

### 1.4 共享基础设施

- MySQL `comm_platform`：localhost:3306，user `root` / `Admin@123`，charset `utf8mb4`（表结构由 Flyway 在应用启动时创建，**多模块共库，注意 §0 陷阱 1**）。
- Redis：127.0.0.1:6379。

---

## 2. 服务器目录约定（scp 目标）

```
/opt/xind2/
├── .env                      # 含 MYSQL_PASSWORD 等敏感配置（来自仓库 .env）
├── db/                       # 数据库脚本（init.sql 等）
├── dist/
│   ├── portal/  m03/  s3/  m04/  s2/  s4/  s5/   # 各前端 build 产物
├── backends/
│   ├── m01-auth/app.jar  …（每个 Java 模块重命名为 app.jar）
│   ├── s5-construction-monitor/   # Node 后端源码（node src/server.js，端口 8091）
├── engines/
│   ├── m03-topology-engine/  m03-llm-service/  s2-cad-fusion/engine/
│   ├── s3-review-engine/rules/  s4-bom-transform/engine/   # Python 引擎源码（各自独立 .venv）
├── scripts/                  # start-backends.sh / stop-backends.sh / health.sh
├── logs/                     # 各进程 .out
└── run/                      # 各进程 .pid
```

**仓库根目录的 `m03-fix-tables.sql`**（非 `deploy/` 内）：补齐 m03 迁移链缺失的 `m03_design_task` / `m03_parametric_template`，**必须在 m03 首次启动前执行**（见 §0 陷阱 2、§4 步骤 1.5）。

---

## 3. 部署前置检查清单（上线前逐项确认）

1. **空库演练（关键）**：先 `DROP DATABASE comm_platform` 重建空库，再启动全部后端。**本地开发库含有历史遗留表，会掩盖"全新库才暴露"的迁移缺陷**（正是陷阱 1/2/3 的根因）。
2. **Java 一律 `mvn clean package`**：本次发现 s2 的 jar 里携带了 `backend/target/classes` 下**源码中已不存在的陈旧迁移文件**，导致库内出现幽灵迁移。**必须 clean**，不能只 `package`。
3. **前端 build 前 `rm -rf dist`**：避免上一版残留文件混入新产物。
4. **m03 前置建表**：启动 m03 前执行仓库根的 `m03-fix-tables.sql`（见 §4 步骤 1.5）。
5. **每引擎独立 venv**：确认 5 个 Python 引擎各自 `.venv` 已建好并装依赖（注意版本约束，见 §1.3）。
6. **服务器就绪**：JDK 21 / Node 18 / Python 3.10 / Nginx / MySQL / Redis；swap 已启用。

---

## 4. 端到端部署步骤

> 前置：本地已 `git` 拉取仓库；服务器已装 **JDK 21**（项目全模块统一 21）/ Node 18 / Python 3.10 / Nginx / MySQL / Redis。

### 步骤 0 — SSH 就绪（用户操作）
1. 运行 `D:\homework\xind2\setup_ssh_key.bat` 将本地公钥注入服务器 `authorized_keys`。
2. 验证：`ssh ubuntu@124.220.37.119`。

### 步骤 1 — 建库
```bash
scp deploy/db/init.sql ubuntu@124.220.37.119:/tmp/init.sql
ssh ubuntu@124.220.37.119 "mysql -uroot -pAdmin@123 < /tmp/init.sql"
```

### 步骤 1.5 — 补齐 m03 缺失表（**全新库必做，见 §0 陷阱 2**）
```bash
scp m03-fix-tables.sql ubuntu@124.220.37.119:/tmp/m03-fix-tables.sql
ssh ubuntu@124.220.37.119 "mysql -uroot -pAdmin@123 comm_platform < /tmp/m03-fix-tables.sql"
```

### 步骤 2 — 本地构建（见 §5 build-all.sh；也可手动）
- Java：`cd packages/<m>/backend && mvn clean package -DskipTests` → `target/*.jar`（**必须 clean**）
- 前端：`cd packages/<m>/frontend && rm -rf dist && npm install && npm run build` → `dist/`
  - 各 `vite.config.js` 的 `base` **已默认正确**（portal=`/`，其余 `/modules/xx/`）；**无需再传 `VITE_BASE`**。

### 步骤 3 — 上传产物到服务器
```bash
# 前端 dist
for m in portal m03 s3 m04 s2 s4 s5; do
  scp -r packages/.../dist ubuntu@124.220.37.119:/opt/xind2/dist/$m
done
# Java jar（重命名为 app.jar）
scp packages/m01-auth/backend/target/*.jar ubuntu@124.220.37.119:/opt/xind2/backends/m01-auth/app.jar
# ... 其余模块同理
# Node 后端 & Python 引擎：整目录 scp（含各自 .venv 或在服务器上重建）
scp -r packages/s5-construction-monitor/backend ubuntu@124.220.37.119:/opt/xind2/backends/s5-construction-monitor
scp -r packages/m03-topology-engine      ubuntu@124.220.37.119:/opt/xind2/engines/
# ... 其余引擎同理
# 配置与脚本
scp .env ubuntu@124.220.37.119:/opt/xind2/.env
scp -r deploy/scripts ubuntu@124.220.37.119:/opt/xind2/scripts
```

### 步骤 4 — 安装 Nginx 配置
```bash
scp deploy/nginx/xind2.conf ubuntu@124.220.37.119:/etc/nginx/sites-available/xind2.conf
ssh ubuntu@124.220.37.119 "\
  sudo ln -sf /etc/nginx/sites-available/xind2.conf /etc/nginx/sites-enabled/xind2.conf && \
  sudo rm -f /etc/nginx/sites-enabled/default && \
  sudo nginx -t && sudo systemctl reload nginx"
```

### 步骤 5 — 启动后端
```bash
ssh ubuntu@124.220.37.119 "sudo bash /opt/xind2/scripts/start-backends.sh"
```
> 新版 `start-backends.sh`（`d4b88f3`）已内置：Java 追加 `--spring.flyway.baseline-version=0`、`JAVA_OPTS` 默认 `-Xmx256m`、Python 引擎用各自 `.venv/bin/python3`。

### 步骤 6 — 健康检查
```bash
ssh ubuntu@124.220.37.119 "bash /opt/xind2/scripts/health.sh"
```
> **多数模块未启用 Actuator，不要再只 `curl /actuator/health`**——请统一用 `health.sh`（见 §6）。

### 停止 / 重启
```bash
ssh ubuntu@124.220.37.119 "sudo bash /opt/xind2/scripts/stop-backends.sh"
```

---

## 5. 本地构建脚本（build-all.sh）

`./deploy/scripts/build-all.sh` 会遍历全部 Java 后端与 7 个前端并完成构建，最后打印产物路径。
- Linux：使用 `mvn`（需 PATH 中存在）。
- Windows 本地：`MVN="D:/maven/apache-maven-3.9.16-bin/bin/mvn.cmd" bash build-all.sh`。
- 构建注意（与 §3 一致）：Java **改用 `mvn clean package`**（本次 s2 幽灵迁移即因未 clean）；前端 **build 前 `rm -rf dist`**。
- 前端 `VITE_BASE` 现已**无需传**（各 `vite.config.js` 的 `base` 默认正确）。

---

## 6. 健康检查（health.sh）

服务器上 `/opt/xind2/scripts/health.sh` 提供**一条命令的总览**，输出：

- **14 个后端端口**：m01:8080、m03:8083、m04:8084、m05:8085、screen:8087、s3:8089、s4:8090、s5:8091(Node)、s2:8096，以及 Python 引擎 8000 / 8092 / 8100 / 9001 / 9002；
- **7 个前端**（`/` + `/modules/{m03,m04,s2,s3,s4,s5}/`）的 HTTP 状态；
- **内存 / swap** 水位。

用法：
```bash
ssh ubuntu@124.220.37.119 "bash /opt/xind2/scripts/health.sh"
```

> 排障提示：页面 200 但接口异常，多为对应后端未起或 Flyway 迁移失败（回到 §0 陷阱 1/2/3 定位）。

---

## 7. 已知不确定项 / 待确认（Ambiguities）

1. **m07-cv-engine 入口未确认**：仓库 `packages/m07-cv-engine/` 仅含空脚手架（`routers/ models/ tests/ utils/` 均为 `.gitkeep` + `README.md`），**未找到任何 `main.py` / `uvicorn` / `FastAPI` 入口**，故其启动命令与端口（假定 8088）无法从代码确认。已在 `start-backends.sh` 中默认禁用（注释状态），待实现后启用。
2. **screen 存在前端目录**：`packages/screen/frontend/`（含 `src/{assets,components,router,stores,utils,views}`），但本部署计划的 7 个前端未包含 screen。当前仅启动 screen 后端 (:8087) 供内部调用，**未为其配置 Nginx 静态/代理路由**。如需对外提供大屏，需补充 `/modules/screen/` 静态位置与可能的 `/api/screen` 代理。
3. **s3 Python 引擎端口**：`packages/s3-review-engine/rules/main.py` 无显式 `uvicorn.run(port=...)`，按约定 `S3_PYTHON_ENGINE_URL=http://localhost:8000` 假定为 **8000**，由 `uvicorn main:app --port 8000` 启动。
4. **s2 Python 引擎**：代码默认 `host=0.0.0.0, port=8092`；为符合"仅本地"原则，启动脚本已强制 `--host 127.0.0.1 --port 8092`。

---

## 8. 已修改的源码文件（可审阅 / 回退）

为使 4 个 HTML5 前端支持子路径部署，**仅修改以下 8 个文件**（其余前端 m03/s3/portal 保持原样）：

- `packages/m04-delivery/frontend/vite.config.js` — 新增 `base: process.env.VITE_BASE || '/modules/m04/'`
- `packages/m04-delivery/frontend/src/router/index.js` — `createWebHistory()` → `createWebHistory(import.meta.env.BASE_URL)`
- `packages/s2-cad-fusion/frontend/vite.config.js` — 新增 `base: ... '/modules/s2/'`
- `packages/s2-cad-fusion/frontend/src/main.js` — `createWebHistory()` → `createWebHistory(import.meta.env.BASE_URL)`
- `packages/s4-bom-transform/frontend/vite.config.js` — 新增 `base: ... '/modules/s4/'`
- `packages/s4-bom-transform/frontend/src/router/index.js` — `createWebHistory()` → `createWebHistory(import.meta.env.BASE_URL)`
- `packages/s5-construction-monitor/frontend/vite.config.js` — 新增 `base: ... '/modules/s5/'`
- `packages/s5-construction-monitor/frontend/src/router/index.js` — `createWebHistory()` → `createWebHistory(import.meta.env.BASE_URL)`

> 说明：开发态下若 `VITE_BASE` 未设置，`base` 回退为 `/modules/<xx>/`，dev server 在该子路径下提供服务；如需在 dev 下回到根路径，可运行 `VITE_BASE=/ npm run dev`。

---

## 9. 修复记录（本次真实部署产生）

| 提交 | 内容 | 影响 |
|------|------|------|
| `d4b88f3` | `start-backends.sh`：Java 启动参数追加 `--spring.flyway.baseline-version=0` | 修复 §0 陷阱 1（后续模块跳过 V1）；**勿 revert** |
| `d4b88f3` | `start_py` 改用 `<engine>/.venv/bin/python3` | 修复 sudo 非交互下 `source .venv/bin/activate` **不改变 PATH**，导致 5 个引擎全报 `No module named uvicorn` |
| `d4b88f3` | `JAVA_OPTS` 默认降为 `-Xmx256m` | 适配 **2C4G 并跑 8 个 JVM**，避免 OOM |
| `a40985e` | `packages/s4-bom-transform/engine/requirements.txt` 补声明 `requests` | 修复 s4 引擎缺依赖 |

> 以上修复已包含在部署脚本/依赖清单中。**本文档仅记录，不代表需再次改动脚本。**
