# xind2 通信基建数智化全流程平台 · 生产部署工具包

本目录包含一套**可复现**的生产部署工具，目标服务器为腾讯云 Ubuntu 22.04（IP `124.220.37.119`）。

> ⚠️ 当前阶段：**本地产出，未推送、未开 PR**。SSH 密钥待就绪，所有文件先写入仓库 `deploy/`，待密钥就绪后再上服务器。

---

## 1. 架构与端口映射总表

服务器防火墙**仅开放 22 / 80 / ICMP**，因此 **Nginx :80 是唯一公网入口**。所有后端仅绑定 `127.0.0.1`，由 Nginx 反代 `/api/*` 转发；静态前端按子路径挂载。

### 1.1 前端子路径 + 反代映射

| 公网路径 (Nginx)        | 模块                  | 后端端口 (127.0.0.1) | 历史模式        | 说明 |
|-------------------------|-----------------------|----------------------|-----------------|------|
| `/`                     | m06-portal            | — (静态)             | HTML5 (root)    | 门户根 |
| `/modules/m03/`         | m03-bim-gis           | 8083                 | Hash            | 静态 + `/api/m03` |
| `/modules/s3/`          | s3-review-engine      | 8089                 | Hash            | 静态 + `/api/s3`、`/api/v1/s3` |
| `/modules/m04/`         | m04-delivery          | 8084                 | HTML5           | 已改子路径部署 |
| `/modules/s2/`          | s2-cad-fusion         | 8096                 | HTML5           | 已改子路径部署（应用默认 8082，但前端统一走 8096） |
| `/modules/s4/`          | s4-bom-transform      | 8090                 | HTML5           | 已改子路径部署 |
| `/modules/s5/`          | s5-construction-monitor | 8091              | HTML5           | 已改子路径部署 |

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

> `screen` 后端 (:8087) 与 `m07-cv-engine` (:8088) **不在** Nginx 代理列表：screen 无前端公网路由（仅本地被其它模块调用），m07 为本地内部引擎（且仓库内未找到可运行入口，见 §5）。

### 1.3 本地 Python 引擎（仅 127.0.0.1，不对外、不代理）

| 引擎 (目录)                    | 端口  | 入口模块 (uvicorn)   | 调用方 |
|--------------------------------|-------|----------------------|--------|
| m03-topology-engine            | 9001  | `main`               | m03 后端 |
| m03-llm-service                | 9002  | `main`               | m03 后端 |
| s2-cad-fusion/engine           | 8092  | `cad_engine.server`  | s2 后端 |
| s3-review-engine/rules         | 8000  | `main`               | s3 后端 (S3_PYTHON_ENGINE_URL 默认 `http://localhost:8000`) |
| s4-bom-transform/engine        | 8100  | `main`               | s4 后端 |
| m07-cv-engine                  | 8088  | （未确认）           | 未启用（见 §5） |

### 1.4 共享基础设施

- MySQL `comm_platform`：localhost:3306，user `root` / `Admin@123`，charset `utf8mb4`（表结构由 Flyway 在应用启动时创建）。
- Redis：127.0.0.1:6379。

---

## 2. 服务器目录约定（scp 目标）

```
/opt/xind2/
├── .env                      # 含 MYSQL_PASSWORD 等敏感配置（来自仓库 .env）
├── dist/
│   ├── portal/  m03/  s3/  m04/  s2/  s4/  s5/   # 各前端 build 产物
├── backends/
│   ├── m01-auth/app.jar  …（每个 Java 模块重命名为 app.jar）
│   ├── s5-construction-monitor/   # Node 后端源码（npm start -> node src/server.js）
├── engines/
│   ├── m03-topology-engine/  m03-llm-service/  s2-cad-fusion/engine/
│   ├── s3-review-engine/rules/  s4-bom-transform/engine/   # Python 引擎源码
├── scripts/                  # start-backends.sh / stop-backends.sh
├── logs/                     # 各进程 .out
└── run/                      # 各进程 .pid
```

---

## 3. 端到端部署步骤

> 前置：本地已 `git` 拉取仓库；服务器已装 Java 17 / Node 18 / Python 3.10 / Nginx / MySQL / Redis。

### 步骤 0 — SSH 就绪（用户操作）
1. 运行 `D:\homework\xind2\setup_ssh_key.bat` 将本地公钥注入服务器 `authorized_keys`。
2. 验证：`ssh root@124.220.37.119`（或对应账号）。

### 步骤 1 — 建库
```bash
scp deploy/db/init.sql root@124.220.37.119:/tmp/init.sql
ssh root@124.220.37.119 "mysql -uroot -pAdmin@123 < /tmp/init.sql"
```

### 步骤 2 — 本地构建（见 §4 build-all.sh；也可手动）
- Java：`cd packages/<m>/backend && mvn -q -DskipTests package` → `target/*.jar`
- 前端：`cd packages/<m>/frontend && npm install && VITE_BASE=/modules/<xx>/ npm run build` → `dist/`
- portal：`VITE_BASE=/ npm run build`

### 步骤 3 — 上传产物到服务器
```bash
# 前端 dist
for m in portal m03 s3 m04 s2 s4 s5; do
  scp -r packages/.../dist root@124.220.37.119:/opt/xind2/dist/$m
done
# Java jar（重命名为 app.jar）
scp packages/m01-auth/backend/target/*.jar root@124.220.37.119:/opt/xind2/backends/m01-auth/app.jar
# ... 其余模块同理
# Node 后端 & Python 引擎：整目录 scp
scp -r packages/s5-construction-monitor/backend root@124.220.37.119:/opt/xind2/backends/s5-construction-monitor
scp -r packages/m03-topology-engine      root@124.220.37.119:/opt/xind2/engines/
# ... 其余引擎同理
# 配置与脚本
scp .env root@124.220.37.119:/opt/xind2/.env
scp -r deploy/scripts root@124.220.37.119:/opt/xind2/scripts
```

### 步骤 4 — 安装 Nginx 配置
```bash
scp deploy/nginx/xind2.conf root@124.220.37.119:/etc/nginx/sites-available/xind2.conf
ssh root@124.220.37.119 "\
  ln -sf /etc/nginx/sites-available/xind2.conf /etc/nginx/sites-enabled/xind2.conf && \
  rm -f /etc/nginx/sites-enabled/default && \
  nginx -t && systemctl reload nginx"
```

### 步骤 5 — 启动后端
```bash
ssh root@124.220.37.119 "bash /opt/xind2/scripts/start-backends.sh"
```

### 步骤 6 — 健康检查（curl）
```bash
# 经 Nginx 公网入口（:80）
curl -fsS -o /dev/null -w "portal=%{http_code}\n" http://124.220.37.119/
curl -fsS -o /dev/null -w "m04=%{http_code}\n"   http://124.220.37.119/modules/m04/
# 直连后端端口
curl -fsS -o /dev/null -w "m01=%{http_code}\n"   http://127.0.0.1:8080/actuator/health
curl -fsS -o /dev/null -w "s2py=%{http_code}\n"  http://127.0.0.1:8092/health
curl -fsS -o /dev/null -w "s4py=%{http_code}\n"  http://127.0.0.1:8100/health
```
> 各 Spring Boot 的健康路径以 `actuator/health` 为准；若未启用 Actuator，可用 `-w "%{http_code}"` 对任意已知接口探测。

### 停止 / 重启
```bash
ssh root@124.220.37.119 "bash /opt/xind2/scripts/stop-backends.sh"
```

---

## 4. 本地构建脚本（build-all.sh）

`./deploy/scripts/build-all.sh` 会遍历全部 Java 后端与 7 个前端并完成构建，最后打印产物路径。
- Linux：使用 `mvn`（需 PATH 中存在）。
- Windows 本地：`MVN="D:/maven/apache-maven-3.9.16-bin/bin/mvn.cmd" bash build-all.sh`。
- **本阶段不实际执行**（依赖/网络可能不可用），仅供后续本地或 CI 使用。

---

## 5. 已知不确定项 / 待确认（Ambiguities）

1. **m07-cv-engine 入口未确认**：仓库 `packages/m07-cv-engine/` 仅含空脚手架（`routers/ models/ tests/ utils/` 均为 `.gitkeep` + `README.md`），**未找到任何 `main.py` / `uvicorn` / `FastAPI` 入口**，故其启动命令与端口（假定 8088）无法从代码确认。已在 `start-backends.sh` 中默认禁用（注释状态），待实现后启用。
2. **screen 存在前端目录**：`packages/screen/frontend/`（含 `src/{assets,components,router,stores,utils,views}`），但本部署计划的 7 个前端未包含 screen。当前仅启动 screen 后端 (:8087) 供内部调用，**未为其配置 Nginx 静态/代理路由**。如需对外提供大屏，需补充 `/modules/screen/` 静态位置与可能的 `/api/screen` 代理。
3. **s3 Python 引擎端口**：`packages/s3-review-engine/rules/main.py` 无显式 `uvicorn.run(port=...)`（无 `if __name__ == "__main__"` 端口定义），按约定 `S3_PYTHON_ENGINE_URL=http://localhost:8000` 假设为 **8000**，由 `uvicorn main:app --port 8000` 启动。
4. **s2 Python 引擎**：代码默认 `host=0.0.0.0, port=8092`；为符合"仅本地"原则，启动脚本已强制 `--host 127.0.0.1 --port 8092`。
5. **硬编码绝对资源路径**：对四个待改前端 `src/` 目录检索 `(['"])/(assets|static|css|js)/`，**未发现**硬编码绝对路径（Vite 默认以 `base` 处理资源，HTML5 子路径下安全）。各 `index.html` 的 `<script src="/src/main.js">` 由 Vite 在 build 时按 `base` 自动改写，无需手动处理。

---

## 6. 已修改的源码文件（可审阅 / 回退）

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
