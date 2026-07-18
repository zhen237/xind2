#!/usr/bin/env bash
# ============================================================
# M03 (S1) 一键部署脚本 —— 本地构建 + 推送到服务器（替代手动传 zip）
# 用法（在 Git Bash 里运行）：
#   cd /d/homework/xind2/xind2
#   bash deploy-s1.sh
# 前提：
#   1) 本机已装 node + rsync（Git Bash 自带 ssh/rsync）
#   2) 已把阿里云 root 的公钥加到服务器 ~/.ssh/authorized_keys（或用 ssh-copy-id）
#   3) 服务器安全组已放行 22 端口（SSH）
# ============================================================
set -e

SERVER="root@47.122.117.17"
FRONTEND_DIR="packages/m03-bim-gis/frontend"
REMOTE_DIST="/www/wwwroot/portal/modules/m03"
REMOTE_BACKEND_DIR="/www/wwwroot/xind2-backend"
MYSQL_PWD="da8ba69fb2ca6cff"

echo "==> [1/3] 本地构建前端"
cd "$(dirname "$0")"
( cd "$FRONTEND_DIR" && npm run build )

echo "==> [2/3] 同步 dist 到服务器 $REMOTE_DIST"
rsync -avz --delete "$FRONTEND_DIR/dist/" "$SERVER:$REMOTE_DIST/"

# 后端若也有改动，取消下面这段注释（前提是本机也能打 jar）
# echo "==> [2.5/3] 同步后端 jar"
# scp packages/m03-bim-gis/backend/target/m03-bim-gis-1.0.0.jar "$SERVER:$REMOTE_BACKEND_DIR/m03-backend.jar"
# ssh "$SERVER" "pkill -f m03-backend.jar || true; sleep 2; cd $REMOTE_BACKEND_DIR && export MYSQL_PASSWORD=$MYSQL_PWD && nohup java -jar m03-backend.jar --server.port=8083 > m03-backend.log 2>&1 &"

echo "==> [3/3] 完成 ✅  浏览器 Ctrl+Shift+R 强刷即可"
