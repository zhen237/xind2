#!/usr/bin/env bash
# =============================================================================
# stop-backends.sh  —  停止 xind2 所有后端（与 start-backends.sh 配对）
# 运行环境：Ubuntu 22.04 服务器
# 用法：  sudo bash /opt/xind2/scripts/stop-backends.sh
#
# 策略：
#   1) 优先按 start-backends.sh 写入的 PID 文件精准停止；
#   2) 兜底 pkill 清理可能残留的 uvicorn / java -jar / node server.js 进程。
# =============================================================================
set -u

DEPLOY_ROOT="/opt/xind2"
RUN_DIR="$DEPLOY_ROOT/run"

echo "==> xind2 后端停止中"

if [ -d "$RUN_DIR" ]; then
  for pidf in "$RUN_DIR"/*.pid; do
    [ -e "$pidf" ] || continue
    pid="$(cat "$pidf" 2>/dev/null || echo "")"
    name="$(basename "$pidf" .pid)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "  >> stopping $name (pid $pid)"
      kill "$pid" 2>/dev/null
      # 给 5 秒优雅退出，否则强杀
      for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
    else
      echo "  >> $name 未运行（或 PID 失效）"
    fi
    rm -f "$pidf"
  done
fi

# 兜底清理（专用服务器上安全；如需更精确可移除下面三行）
# 注意 Node 的匹配式：start-backends.sh 用 start_node "s5-construction-monitor" 8091 拉起，
# 实际命令行是 `node src/server.js`、工作目录 /opt/xind2/backends/s5-construction-monitor，
# 所以进程 cmdline 里**不含** "backend/" 这一段。旧写法
# "s5-construction-monitor/backend/src/server.js" 永远匹配不到，PID 文件失效时杀不掉 Node。
pkill -f "uvicorn"                                  2>/dev/null || true
pkill -f "backends/.*app.jar"                       2>/dev/null || true
pkill -f "s5-construction-monitor/.*server\.js"     2>/dev/null || true

echo "==> 停止完成"
