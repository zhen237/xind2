#!/bin/bash
# M03 拓扑规划引擎启动脚本 (Linux / Rocky 9.x)
# 用法: ./start.sh   (生产建议 nohup ./start.sh > topo.log 2>&1 &)
set -e

cd "$(dirname "$0")"

# 优先使用系统 python3；无则退回 python
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  echo "[错误] 未找到 python3，请先安装 Python 3.10+"
  exit 1
fi

# 首次运行建 venv 并装依赖
if [ ! -d .venv ]; then
  echo "[1/3] 创建虚拟环境 ..."
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/3] 安装依赖 ..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "[3/3] 启动拓扑引擎 (127.0.0.1:9001) ..."
# 仅监听本机回环：引擎只供同机 M03 后端调用，不暴露公网
exec uvicorn main:app --host 127.0.0.1 --port 9001
