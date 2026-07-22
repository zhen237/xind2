#!/bin/bash
# M03 (S1 智能设计) 后端启动脚本
# 用法: bash start-m03.sh

# ---- 数据库配置（服务器实际值）----
export MYSQL_USER='root'
export MYSQL_PASSWORD='CHANGE_ME'   # MySQL root 密码
export MYSQL_URL='jdbc:mysql://localhost:3306/comm_platform?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai'

# ---- Redis 配置 ----
export REDIS_HOST='localhost'
export REDIS_PORT='6379'
export REDIS_DB='3'
export REDIS_PASSWORD=''                     # 宝塔 Redis 若设了密码，填这里

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
