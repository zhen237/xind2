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
MYSQL_PWD="CHANGE_ME"

echo "==> [1/3] 本地构建前端"
cd "$(dirname "$0")"
( cd "$FRONTEND_DIR" && npm run build )

echo "==> [2/3] 同步 dist 到服务器 $REMOTE_DIST"
rsync -avz --delete "$FRONTEND_DIR/dist/" "$SERVER:$REMOTE_DIST/"

# 后端若也有改动，取消下面这段注释（前提是本机也能打 jar）
# echo "==> [2.5/3] 同步后端 jar"
# scp packages/m03-bim-gis/backend/target/m03-bim-gis-1.0.0.jar "$SERVER:$REMOTE_BACKEND_DIR/m03-backend.jar"
# ssh "$SERVER" "pkill -f m03-backend.jar || true; sleep 2; cd $REMOTE_BACKEND_DIR && export MYSQL_PASSWORD=$MYSQL_PWD && nohup java -jar m03-backend.jar --server.port=8083 > m03-backend.log 2>&1 &"

echo "==> [2.6/3] 校验 nginx 站点配置含 /modules/m03 location（防配置被改脏，非破坏性）"
NGINX_SRC="scripts/nginx.conf"
if [ -f "$NGINX_SRC" ]; then
  scp "$NGINX_SRC" "$SERVER:/tmp/xind2-nginx-clean.conf"
  # 远端：在整棵 nginx 配置树(含 include 引入的文件)中定位承载 /modules/m03 的站点文件。
  # 采用「非破坏性」策略：已含正确 location 则视为健康、不改动(幂等)；整段缺失才补回，
  # 绝不整体覆盖站点文件(避免冲掉生产域名/SSL 及其他 location)。
  ssh "$SERVER" bash -s <<'REMOTE'
SITE=$(grep -rl "modules/m03" /www/server/nginx/conf 2>/dev/null | head -1)
if [ -z "$SITE" ]; then
  echo "  [warn] 未在 nginx 配置树(/www/server/nginx/conf)中找到含 modules/m03 的站点配置，跳过 nginx 校验"
  echo "         请按 docs/S1-Cesium线上可视化修复.md 手动处理"
  exit 0
fi
echo "  定位到站点配置文件: $SITE"
if grep -q "location[[:space:]]*/modules/m03/" "$SITE"; then
  echo "  [ok] 生产配置已包含 /modules/m03 location，未改动（幂等）"
else
  echo "  [warn] 生产配置缺失 /modules/m03 location，尝试非破坏性补回…"
  awk '/location[[:space:]]*\/modules\/m03\//{f=1} f{print} f&&/}/{exit}' /tmp/xind2-nginx-clean.conf >> "$SITE"
  if nginx -t >/tmp/nginx-t.out 2>&1; then
    nginx -s reload
    echo "  [ok] 已补回 /modules/m03 location 并热重载"
  else
    echo "  [fail] nginx -t 校验失败，请手动检查：$SITE"
    cat /tmp/nginx-t.out
    exit 1
  fi
fi
REMOTE
else
  echo "  [warn] 未找到 $NGINX_SRC，跳过 nginx 校验"
fi

echo "==> [2.7/3] 清理无效 cesium 软链（index.html 实际引用 /modules/m03/cesium，根 /cesium 软链无用）"
ssh "$SERVER" "test -L /www/wwwroot/portal/cesium && rm -f /www/wwwroot/portal/cesium && echo '  已删除无效软链 /www/wwwroot/portal/cesium' || echo '  无无效软链，跳过'"

echo "==> [3/3] 完成  浏览器 Ctrl+Shift+R 强刷即可"
