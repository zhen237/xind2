#!/usr/bin/env bash
# =============================================================
#  子赛题进度看板 · 阿里云 ECS 一键部署脚本
#  在服务器（ECS）上以 root 运行：  bash deploy.sh
#  作用：装 nginx → git 拉取项目 → 拷贝看板 → 配 nginx → 重载
# =============================================================
set -e

REPO="https://github.com/zhen237/xind2.git"
BRANCH="feat/s1-parametric-design"   # 看板随 S1 分支提交，确保含 progress-board/
LOCAL_DIR="/opt/xind2"
NGINX_HTML="/usr/share/nginx/html"
BOARD_DIR="$NGINX_HTML/progress-board"

echo "==> [1/5] 安装 nginx（若未安装）"
if ! command -v nginx >/dev/null 2>&1; then
  if command -v yum >/dev/null 2>&1; then
    yum install -y nginx
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update && apt-get install -y nginx
  else
    echo "未检测到 yum/apt，请手动安装 nginx 后重试"; exit 1
  fi
fi
systemctl enable nginx 2>/dev/null || true
systemctl start  nginx 2>/dev/null || true

echo "==> [2/5] 拉取代码（首次 clone，之后 pull）"
if [ -d "$LOCAL_DIR/.git" ]; then
  git -C "$LOCAL_DIR" checkout "$BRANCH" 2>/dev/null || true
  git -C "$LOCAL_DIR" pull --ff-only
else
  git clone --branch "$BRANCH" --single-branch "$REPO" "$LOCAL_DIR"
fi

echo "==> [3/5] 拷贝看板到 nginx 目录"
mkdir -p "$BOARD_DIR"
cp -r "$LOCAL_DIR/progress-board/." "$BOARD_DIR/"

echo "==> [4/5] 写入 nginx 配置"
cat > /etc/nginx/conf.d/progress-board.conf <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    location /progress-board/ {
        alias /usr/share/nginx/html/progress-board/;
        try_files $uri $uri/ /progress-board/index.html;
    }
    autoindex off;
}
EOF

echo "==> [5/5] 校验并重载 nginx"
nginx -t
systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null || true

echo ""
echo "✅ 部署完成！"
echo "   本机访问： http://localhost/progress-board/"
echo "   公网访问： http://<你的ECS公网IP>/progress-board/"
echo ""
echo "⚠️  阿里云控制台 → 安全组 → 入方向放行 TCP 80（HTTP）。"
echo "🔄 之后更新进度：改 progress.json 后，服务器执行："
echo "    cd $LOCAL_DIR && git pull --ff-only && cp -r progress-board/. $BOARD_DIR/"
