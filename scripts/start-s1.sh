#!/bin/bash
# S1 子赛题演示一键启动 (Linux / Rocky 9.x, 无图形界面)
# 启动: 拓扑引擎(9001) + LLM服务(9002) + M03后端(8083) + M03前端(9000)
# 前置: MySQL/Redis 已运行 (docker-compose up -d 或单独部署)
# 用法: ./start-s1.sh
set -u
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
LOG="/tmp/s1_demo_$(date +%Y%m%d).log"
echo "S1 演示启动中，日志见 $LOG" | tee -a "$LOG"

run_bg() {
  local name="$1"; local cmd="$2"
  echo "[启动] $name ..." | tee -a "$LOG"
  nohup bash -c "cd '$PROJECT_ROOT' && $cmd" >> "$LOG" 2>&1 &
  echo "       pid=$!"
}

# 1. 拓扑引擎 (端口 9001, 引擎只监听本机回环)
if [ -f packages/m03-topology-engine/start.sh ]; then
  run_bg "拓扑引擎(9001)" "bash packages/m03-topology-engine/start.sh"
else
  echo "[跳过] 未找到 packages/m03-topology-engine/start.sh"
fi

# 2. LLM 服务 (端口 9002)
if [ -d packages/m03-llm-service ]; then
  run_bg "LLM服务(9002)" "cd packages/m03-llm-service && { [ -d .venv ] || python3 -m venv .venv; } && source .venv/bin/activate && pip install -q -r requirements.txt && python main.py"
else
  echo "[跳过] 未找到 packages/m03-llm-service"
fi

# 3. M03 后端 (端口 8083)
if [ -d packages/m03-bim-gis/backend ]; then
  run_bg "M03后端(8083)" "cd packages/m03-bim-gis/backend && mvn -q spring-boot:run -Dspring-boot.run.arguments=--server.port=8083"
else
  echo "[跳过] 未找到 packages/m03-bim-gis/backend"
fi

# 4. M03 前端 (端口 9000)
if [ -d packages/m03-bim-gis/frontend ]; then
  run_bg "M03前端(9000)" "cd packages/m03-bim-gis/frontend && { [ -d node_modules ] || npm install; } && npm run dev"
else
  echo "[跳过] 未找到 packages/m03-bim-gis/frontend"
fi

echo "" | tee -a "$LOG"
echo "全部后台启动完成。检查: curl http://127.0.0.1:9001/health ; curl http://127.0.0.1:8083/actuator/health" | tee -a "$LOG"
echo "停止: pkill -f 'uvicorn main:app --host 127.0.0.1 --port 9001' ; pkill -f 'packages/m03-bim-gis/backend' ; pkill -f 'vite'" | tee -a "$LOG"
