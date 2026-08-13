# S1 安全整改 · 服务器落地运维清单（闭环用）

> 配套提交：`feat/s1-parametric-design` 的 `425310a`(安全7项) → 已 git-filter-repo 擦除历史 → `18cbb32`(干净) → `d971f10`(LLM骨架)
> 代码层已 100% 完成并推送。**本清单是"最后一公里"：让服务器/账号不再用泄露凭据。**
> 填 `<...>` 占位处时，请先在【步骤0】生成全新值，**不要复用任何曾进过 git 的密码**。

---

## ⚠️ 当前真实风险（先读这段）

| 项 | 状态 |
|----|------|
| 代码里是否有明文密钥 | 已无（git 全程擦除，`-S` 扫描为空） |
| 服务器 MySQL root 实际密码 | **仍是泄露的旧值 `da8ba69fb2ca6cff`**（从未真正 `ALTER USER`） |
| GitHub 远端历史 | 干净（force-push 后无密钥） |
| `.env.example` 默认值 | `CHANGE_ME`（占位，安全） |

→ 结论：**不执行本清单，服务器等于还在用泄露密码跑着**。请按顺序执行。

---

## 步骤0 · 生成三套全新凭据（从未进过 git）

在**本地**或跳板机执行，生成后**只抄到对应位置，不要提交**：

```bash
# 1) MySQL root 新密码（32字节hex）
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
#    → 记为 <MYSQL_NEW_PWD>

# 2) M03 内部 API Key（design 写删接口 X-API-Key 校验用）
node -e "console.log('m03-internal-'+require('crypto').randomBytes(12).toString('hex'))"
#    → 记为 <M03_API_KEY>

# 3) 大模型服务 Key（仅服务器本地 llm-service 环境变量，不进 git/不进 GitHub）
#    这串直接去你的云端 LLM 控制台拿，例如 OpenAI/Azure/DeepSeek 的 sk-...
#    → 记为 <LLM_API_KEY>
```

> 把这三个值记到密码管理器/记事本，**不要贴进任何 .md / 截图 / 聊天**。

---

## 步骤1 · GitHub 仓库 Secrets（仅需 1 项）

路径：仓库 `Settings → Secrets and variables → Actions → New repository secret`

| Name | Value |
|------|-------|
| `MYSQL_PASSWORD` | `<MYSQL_NEW_PWD>`（步骤0第1个） |

- ❌ **不要** 加 `M03_API_KEY` 到 GitHub Secrets —— 它只在服务器本地 `.env`，CI 不引用。
- `deploy.yml:199` 会把它注入部署 shell 的 `MYSQL_PASSWORD` 环境变量，启动时 `start-m03.sh` 优先读它。

---

## 步骤2 · 服务器 MySQL 密码轮换 + 部署 .env

> 环境：阿里云 ECS `47.122.117.17`（Linux）。以下在服务器上跑。

```bash
# 2.1 登服务器后，先改 MySQL root 密码为全新值
mysql -u root -p
# 输入当前旧密码（da8ba69fb2ca6cff）登录后执行：
ALTER USER 'root'@'localhost' IDENTIFIED BY '<MYSQL_NEW_PWD>';
FLUSH PRIVILEGES;
EXIT;

# 2.2 在 start-m03.sh 同目录创建 .env（已被 gitignore，不会入库）
#     位置：仓库根目录（start-m03.sh 的 SCRIPT_DIR）
cat > /path/to/xind2/.env <<'EOF'
MYSQL_PWD=<MYSQL_NEW_PWD>
M03_API_KEY=<M03_API_KEY>
EOF
chmod 600 /path/to/xind2/.env

# 2.3 验证 M03 能连库（看启动日志有无 1045）
cd /path/to/xind2
bash start-m03.sh
sleep 8
curl -s http://127.0.0.1:8083/api/m03/health ; echo
#   期望：返回 health OK（非 500）
```

回填位置小结：
- `<MYSQL_NEW_PWD>` → GitHub Secrets `MYSQL_PASSWORD` **且** 服务器 MySQL root **且** 服务器 `.env` 的 `MYSQL_PWD`
- `<M03_API_KEY>` → 服务器 `.env` 的 `M03_API_KEY` **且** QGIS 插件运行环境的环境变量（见步骤5）

---

## 步骤3 · 生产 CORS 白名单（防跨域滥用）

`application.yml` 默认白名单是 `localhost`，公网部署必须覆盖：

```bash
# 在 start-m03.sh 同目录的 .env 追加一行（或在启动环境 export）
# 多个源用逗号分隔，写你真实的前端域名/IP
echo 'CORS_ALLOWED_ORIGINS=https://your-frontend.domain,http://47.122.117.17:8080' >> /path/to/xind2/.env
# 改完重启 M03（见 2.3 的 start-m03.sh 流程）
```

> 注意：目前 `/api/m03/design/**` 写删接口仍走 `permit-paths` 免 JWT，由 `DesignApiKeyInterceptor` 校验 `X-API-Key`。公网暴露前务必确认 QGIS/内部服务都带对了 Key，否则接口对全网开放。

---

## 步骤4（可选但推荐）· HTTPS（nginx TLS）

让 QGIS 链路走 https，消灭明文传输：

```bash
# 4.1 nginx 已装前提下，加 server 块监听 443，反向代理到 127.0.0.1:8083
#     ssl_certificate / ssl_certificate_key 用你的证书（Let's Encrypt 或自有）
# 4.2 重启 nginx： nginx -s reload
# 4.3 QGIS 侧改用 https（见步骤5 环境变量）
```

---

## 步骤5 · 本地 QGIS 插件环境变量（Windows 工作站）

QGIS 插件（`qgis-plugin/design_engine/data_sync.py`、`ui/design_dock.py`）现在从环境变量读：

- `M03_API_URL`：默认 `http://47.122.117.17:8083`，配了 HTTPS 后改为 `https://47.122.117.17`
- `M03_API_KEY`：填 **步骤0 的 `<M03_API_KEY>`**（与服务器 `.env` 一致，否则 design 接口 401）

设置方式（Windows，让 QGIS 启动进程能读到）：
```powershell
# 系统环境变量（控制面板→高级→环境变量）新增：
#   变量名 M03_API_KEY   值 <M03_API_KEY>
#   变量名 M03_API_URL   值 https://47.122.117.17
# 设完重启 QGIS 生效
```
验证：在 QGIS 里跑一次"上传设计/生成"操作，后端日志无 401 即通。

---

## 步骤6 · 大模型服务上线（服务器本地，仅本机 127.0.0.1:9002）

```bash
# 6.1 服务器装依赖（用 venv 隔离）
cd /path/to/xind2/packages/m03-llm-service
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 6.2 注入 Key 后启动（LLM_API_KEY 仅此处，前端不持有）
export LLM_API_KEY=<LLM_API_KEY>          # 你的云端 sk-...
export LLM_BASE_URL=https://api.openai.com/v1   # 换厂商改这里
export LLM_MODEL=gpt-4o-mini              # 换模型改这里
nohup python main.py > /www/wwwroot/xind2-backend/llm-service.log 2>&1 &

# 6.3 探活
curl -s http://127.0.0.1:9002/health ; echo
#   配了 Key 后 configured 应为 true
```

> M03 后端 `LlmController` 已暴露 `/api/m03/llm/**`，强制 JWT + 限流；前端/插件经 JWT 网关调用，永远不直接持 LLM Key。

---

## 步骤7 · 通知队友重新 clone（历史已重写）

```bash
# 队友机器上（旧仓库不能继续 pull，会冲突）：
# 1) 备份旧仓库个人改动后删除
# 2) 重新 clone
git clone ssh://git@ssh.github.com:443/zhen237/xind2.git
git checkout feat/s1-parametric-design
```

---

## ✅ 闭环验证清单

| 验证项 | 命令 / 位置 | 期望 |
|--------|-------------|------|
| 服务器 MySQL 已不用旧密码 | `mysql -u root -p` 用旧密码 `da8ba69…` 登录 | **失败**（证明已轮换） |
| M03 能连库 | `curl 127.0.0.1:8083/api/m03/health` | 200，无 Flyway 1045 |
| design 接口需 Key | QGIS 不带 `X-API-Key` 调 design | 401 |
| CORS 生产白名单生效 | 跨域请求非白名单源 | 被拦 |
| LLM 服务探活 | `curl 127.0.0.1:9002/health` | configured=true（配Key后） |
| git 历史无密钥 | 本机 `git log --all -S'da8ba69...'` | 空 |

---

## 🔙 回滚 / 备份

- 擦除前整仓镜像备份：`D:/homework/xind2/xind2-pre-scrub-backup`（含旧历史）。
- 若需回退到擦除前：用该备份 `git clone --mirror` 恢复，再重新走本清单（届时旧密码已泄露，必须换全新值）。
- 服务器 `.env` 已 `chmod 600`，属未跟踪文件，重装系统/迁移时注意备份。

---

## 一句话执行顺序

**生成新凭据 → GitHub 加 MYSQL_PASSWORD → 服务器 ALTER USER + 写 .env + 重启 M03 → 配 CORS/HTTPS → QGIS 设环境变量 → llm-service 注入 Key 启动 → 队友重 clone → 跑验证清单。**
