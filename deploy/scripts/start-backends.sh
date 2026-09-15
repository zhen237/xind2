#!/usr/bin/env bash
# =============================================================================
# start-backends.sh  —  xind2 服务端一键启动所有后端（Java / Node / Python）
# 运行环境：Ubuntu 22.04 服务器（本地回环绑定，由 Nginx :80 反代）
# 用法：  sudo bash /opt/xind2/scripts/start-backends.sh
#
# 说明：
#   - 每个进程写入 PID 到 /opt/xind2/run/<name>.pid，便于 stop-backends.sh 精准停止。
#   - Java 后端：nohup java -jar $JAVA_OPTS app.jar --server.port=PORT
#     默认 -Xmx256m（适配 2C4G 机型同时跑 8 个 JVM），可用环境变量 JAVA_OPTS 覆盖。
#   - Node 后端（s5）：node src/server.js，通过 PORT 环境变量指定端口。
#   - Python 引擎：uvicorn <module>:app --host 127.0.0.1 --port PORT
#   - MySQL 密码等敏感配置从 /opt/xind2/.env 注入（Spring Boot 读取环境变量）。
#   - 注意：3455（WorkBuddy）为本地开发工具端口，在服务器上无关，无需开放。
# =============================================================================
set -u

DEPLOY_ROOT="/opt/xind2"
RUN_DIR="$DEPLOY_ROOT/run"
LOG_DIR="$DEPLOY_ROOT/logs"
ENV_FILE="$DEPLOY_ROOT/.env"
JAVA_OPTS="${JAVA_OPTS:--Xmx256m -Xms128m -XX:MaxMetaspaceSize=128m -XX:TieredStopAtLevel=1}"

mkdir -p "$RUN_DIR" "$LOG_DIR"

# 注入环境变量（MYSQL_PASSWORD 等），供 Spring Boot 读取
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi
# 兜底：若 .env 缺失，使用仓库约定的默认凭据（与本地 .env 一致）
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-Admin@123}"
export MYSQL_USER="${MYSQL_USER:-root}"
export MYSQL_URL="${MYSQL_URL:-jdbc:mysql://localhost:3306/comm_platform?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true}"
export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6379}"

echo "==> xind2 后端启动中 (DEPLOY_ROOT=$DEPLOY_ROOT)"

# -----------------------------------------------------------------------------
# Java 后端：<name> <port> <jar相对路径(相对 backends/)>
# -----------------------------------------------------------------------------
start_java() {
  local name="$1" port="$2" jar="$3"
  echo "  >> java  $name  :$port  ($jar)"
  # 所有模块共用 comm_platform 库，且各自开启 baseline-on-migrate。
  # 首个启动的模块会把库变「非空」，后续模块因「库非空但无本模块历史表」
  # 而把 baseline 记在 V1 上 → 跳过 V1 直接执行 V2 的 ALTER → 表不存在报错。
  # 强制 baseline-version=0：baseline 落在 0，V1..Vn 全部照常执行
  # （V1 用 CREATE TABLE IF NOT EXISTS，可重复执行）。
  nohup java $JAVA_OPTS -jar "$DEPLOY_ROOT/backends/$jar" \
    --server.port="$port" \
    --spring.flyway.baseline-version=0 \
    > "$LOG_DIR/$name.out" 2>&1 &
  echo $! > "$RUN_DIR/$name.pid"
}

# Java 后端（s2 默认 8082，但全部前端 /api/s2 指向 8096，故强制 8096）
start_java "m01-auth"           8080 "m01-auth/app.jar"
start_java "m03-bim-gis"        8083 "m03-bim-gis/app.jar"
start_java "m04-delivery"       8084 "m04-delivery/app.jar"
start_java "m05-twin-ops"       8085 "m05-twin-ops/app.jar"
start_java "s2-cad-fusion"      8096 "s2-cad-fusion/app.jar"
start_java "s3-review-engine"   8089 "s3-review-engine/app.jar"
start_java "s4-bom-transform"   8090 "s4-bom-transform/app.jar"
start_java "screen"             8087 "screen/app.jar"   # 后端仅本地调用，无公网路由

# -----------------------------------------------------------------------------
# Node 后端：s5-construction-monitor（端口由 PORT 环境变量决定，默认 8091）
# 说明：直接用 node 拉起以获得干净的 PID；npm start 等价（见 package.json "start"）。
# -----------------------------------------------------------------------------
start_node() {
  local name="$1" port="$2" dir="$3"
  echo "  >> node  $name  :$port  ($dir)"
  cd "$DEPLOY_ROOT/backends/$dir"
  PORT="$port" nohup node src/server.js > "$LOG_DIR/$name.out" 2>&1 &
  echo $! > "$RUN_DIR/$name.pid"
  cd "$DEPLOY_ROOT"
}
start_node "s5-construction-monitor" 8091 "s5-construction-monitor"

# -----------------------------------------------------------------------------
# Python 引擎：仅绑定 127.0.0.1（供同机 Java 后端内部调用，不对外）
#   <name> <port> <源码相对路径(相对 engines/)> <uvicorn模块>
# -----------------------------------------------------------------------------
start_py() {
  local name="$1" port="$2" path="$3" mod="$4"
  echo "  >> python $name  127.0.0.1:$port  ($path : $mod)"
  local eng="$DEPLOY_ROOT/engines/$path"
  if [ ! -d "$eng" ]; then
    echo "     [跳过] 目录不存在: $eng"
    return 0
  fi
  cd "$eng"
  # 优先使用引擎自带 venv 的【解释器】；否则回落系统 python3。
  # 注意：不要用 `source .venv/bin/activate` —— 在 sudo 非交互环境下
  # activate 可能不改变 PATH，导致 python3 仍解析到 /usr/bin/python3，
  # 报 "No module named uvicorn"。直接调用 venv 的 python3 最稳。
  local PY="python3"
  if [ -x "$eng/.venv/bin/python3" ]; then
    PY="$eng/.venv/bin/python3"
  fi
  nohup "$PY" -m uvicorn "$mod:app" --host 127.0.0.1 --port "$port" \
    > "$LOG_DIR/$name.out" 2>&1 &
  echo $! > "$RUN_DIR/$name.pid"
  cd "$DEPLOY_ROOT"
}

start_py "m03-topology-engine" 9001 "m03-topology-engine"        "main"
start_py "m03-llm-service"     9002 "m03-llm-service"            "main"
start_py "s2-engine"           8092 "s2-engine"                  "cad_engine.server"
start_py "s3-rules"            8000 "s3-rules"                   "main"   # S3_PYTHON_ENGINE_URL 默认 http://localhost:8000
start_py "s4-engine"           8100 "s4-engine"                  "main"

# m07-cv-engine (8088)：仓库内未找到可运行的 Python 入口（仅含空脚手架
#   routers/models/tests/utils + README.md），故默认不启动。
#   待实现并确认入口模块后，取消下面注释（将 app.main 替换为实际模块）：
# start_py "m07-cv-engine" 8088 "m07-cv-engine" "app.main"

echo "==> 启动完成。日志见 $LOG_DIR，PID 见 $RUN_DIR"
echo "==> 建议稍候数秒后用 stop/health 检查确认："
echo "    curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/actuator/health"
