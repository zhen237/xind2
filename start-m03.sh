#!/bin/bash
# M03 (S1 智能设计) 后端启动脚本
# 用法: bash start-m03.sh

# ---- 敏感配置：从 .env / .env.example 读取，禁止硬编码明文 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
load_env() {
  for f in "$SCRIPT_DIR/.env" "$SCRIPT_DIR/.env.example"; do
    [ -f "$f" ] || continue
    while IFS='=' read -r k v || [ -n "$k" ]; do
      case "$k" in ''|\#*) continue ;; esac
      v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"   # 去引号
      export "$k=$v"
    done < "$f"
  done
}
load_env

# ---- 数据库配置（密码从 .env 读取，不再硬编码）----
export MYSQL_USER="${MYSQL_USER:-root}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-${MYSQL_PWD:-CHANGE_ME}}"
export MYSQL_URL="${MYSQL_URL:-jdbc:mysql://localhost:3306/comm_platform?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai}"

# ---- Redis 配置 ----
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_DB="${REDIS_DB:-3}"
export REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# ---- 端口（务必用 CLI 参数，避开 WorkBuddy 占用的 3455）----
PORT=8083
JAR=/www/wwwroot/xind2-backend/m03-backend.jar
LOG=/www/wwwroot/xind2-backend/m03-backend.log

# 杀掉旧进程（同端口）
OLD_PID=$(lsof -ti tcp:$PORT 2>/dev/null)
if [ -n "$OLD_PID" ]; then
  echo "停止旧 M03 进程 PID=$OLD_PID"
  kill $OLD_PID 2>/dev/null
  sleep 2
fi

echo "启动 M03 后端 (port=$PORT) ..."
nohup java -jar "$JAR" --server.port=$PORT \
  > "$LOG" 2>&1 &

echo "已启动，日志: $LOG"
echo "健康检查: curl http://127.0.0.1:$PORT/api/m03/health"
