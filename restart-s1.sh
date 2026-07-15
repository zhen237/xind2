#!/usr/bin/env bash
# ============================================================
# 一键重启 S1 (M03 BIM-GIS) 前后端
# 用法：在 Git Bash 里 cd 到项目根目录后执行  bash restart-s1.sh
# ⚠️ 不会杀 3455 端口（那是 WorkBuddy 自身进程）
# ============================================================
set -e

ROOT=/d/homework/xind2/xind2
BE=$ROOT/packages/m03-bim-gis/backend
FE=$ROOT/packages/m03-bim-gis/frontend
ENV=$ROOT/.env
MVN="D:/maven/apache-maven-3.9.16-bin/bin/mvn.cmd"

echo "== 1. 停掉旧的 8083/9000 进程（绝不碰 3455）=="
for port in 8083 9000; do
  pids=$(netstat -ano 2>/dev/null | grep -E ":$port " | grep LISTENING | awk '{print $5}')
  for pid in $pids; do
    if [ "$pid" != "3455" ]; then
      taskkill /F /PID "$pid" /T >/dev/null 2>&1 && echo "  killed PID $pid on :$port" || echo "  :$port 无进程"
    fi
  done
done
sleep 2

echo "== 2. 注入 .env（跳过 # 注释行，否则会启动失败）=="
while IFS='=' read -r k v; do
  case "$k" in \#*|'') continue ;; esac
  [ -n "$k" ] && [ -n "$v" ] && export "$k=$v"
done < "$ENV"
echo "  MYSQL_PASSWORD=${MYSQL_PASSWORD:0:3}*** 已注入"

echo "== 3. 后台启动后端 8083 =="
cd "$BE"
"$MVN" spring-boot:run -Dspring-boot.run.arguments="--server.port=8083" > /tmp/m03-be.log 2>&1 &
echo "  后端编译+启动中（首次约 2-4 分钟），日志: /tmp/m03-be.log"

echo "== 4. 后台启动前端 9000 =="
cd "$FE"
npm run dev > /tmp/m03-fe.log 2>&1 &
echo "  前端启动中，日志: /tmp/m03-fe.log"

echo ""
echo "== 完成。等约 2 分钟后验证：=="
echo "  后端:  curl http://localhost:8083/api/m03/health   (应返回 200)"
echo "  前端:  浏览器打开 http://localhost:9000/modules/m03/"
echo "  看后端日志:  tail -f /tmp/m03-be.log"
