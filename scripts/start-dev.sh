#!/bin/bash
# 一键启动脚本 - Linux/Mac
# 使用方法: ./start-dev.sh

set -e

echo "======================================"
echo "  通信基建数智化平台 - 一键启动"
echo "======================================"
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 1. 检查 Docker 是否运行
echo "[1/5] 检查 Docker 状态..."
if ! docker info > /dev/null 2>&1; then
    echo "  [错误] Docker 未运行，请先启动 Docker"
    exit 1
fi
echo "  Docker 运行正常"

# 2. 启动 Docker Compose 服务
echo "[2/5] 启动数据库和中间件服务..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "  [错误] Docker Compose 启动失败"
    exit 1
fi
echo "  Docker Compose 服务启动成功"

# 等待 MySQL 启动
echo "  等待 MySQL 启动..."
sleep 10

# 3. 初始化数据库
echo "[3/5] 初始化数据库..."
docker exec -i comm-mysql mysql -uroot -proot123 < "$PROJECT_ROOT/scripts/init-db.sql"
echo "  数据库初始化成功"

# 4. 启动后端服务
echo "[4/5] 启动后端服务..."

# M01 认证服务
echo "  启动 M01 认证服务 (端口 8080)..."
gnome-terminal -- bash -c "cd '$PROJECT_ROOT/packages/m01-auth/backend'; mvn spring-boot:run; exec bash" 2>/dev/null || \
xterm -e "cd '$PROJECT_ROOT/packages/m01-auth/backend' && mvn spring-boot:run" 2>/dev/null || \
echo "  请手动运行: cd $PROJECT_ROOT/packages/m01-auth/backend && mvn spring-boot:run"

# M05 运维服务
echo "  启动 M05 智慧运维服务 (端口 8085)..."
gnome-terminal -- bash -c "cd '$PROJECT_ROOT/packages/m05-twin-ops/backend'; mvn spring-boot:run; exec bash" 2>/dev/null || \
xterm -e "cd '$PROJECT_ROOT/packages/m05-twin-ops/backend' && mvn spring-boot:run" 2>/dev/null || \
echo "  请手动运行: cd $PROJECT_ROOT/packages/m05-twin-ops/backend && mvn spring-boot:run"

# 5. 启动前端
echo "[5/5] 启动前端门户..."

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "  [错误] Node.js 未安装"
    exit 1
fi

echo "  安装前端依赖..."
cd "$PROJECT_ROOT/packages/m06-portal"
npm install

echo "  启动前端开发服务器 (端口 5173)..."
gnome-terminal -- bash -c "cd '$PROJECT_ROOT/packages/m06-portal'; npm run dev; exec bash" 2>/dev/null || \
xterm -e "cd '$PROJECT_ROOT/packages/m06-portal' && npm run dev" 2>/dev/null || \
echo "  请手动运行: cd $PROJECT_ROOT/packages/m06-portal && npm run dev"

# 完成
echo ""
echo "======================================"
echo "  启动完成！"
echo "======================================"
echo ""
echo "访问地址："
echo "  - 前端门户: http://localhost:5173"
echo "  - M01 API:  http://localhost:8080"
echo "  - M05 API:  http://localhost:8085"
echo "  - MinIO:    http://localhost:9001"
echo "  - EMQX:     http://localhost:18083"
echo ""
echo "默认账号: admin / admin123"
echo ""

# 保持脚本运行
echo "按 Ctrl+C 停止所有服务"
trap "echo '正在停止所有服务...'; docker-compose down; exit" SIGINT SIGTERM
wait
