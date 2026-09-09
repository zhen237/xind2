#!/usr/bin/env bash
# =============================================================================
# build-all.sh  —  本地构建全部 Java 后端 + 前端（在 Git Bash / Linux 下运行）
# -----------------------------------------------------------------------------
# 重要：
#   - 本脚本【不】在服务器上执行，仅用于部署前在本地/CI 构建产物。
#   - 不会真正运行（无网络/依赖时勿执行）；此处仅供审阅与本地使用。
#   - Windows 本地 Maven 路径：D:\maven\apache-maven-3.9.16-bin\bin\mvn.cmd
#       将下方 MVN 变量改为该 .cmd 路径即可在 Windows Git Bash 使用。
#
# 产物：
#   Java   -> packages/<module>/backend/target/*.jar
#   前端   -> packages/<module>/frontend/dist
# =============================================================================
set -u

# 脚本位于 deploy/scripts/，上两级即仓库根（含 packages/）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Linux 用 mvn；Windows 本地请设： MVN="D:/maven/apache-maven-3.9.16-bin/bin/mvn.cmd"
MVN="${MVN:-mvn}"

echo "REPO_ROOT = $REPO_ROOT"

# -----------------------------------------------------------------------------
# 1) Java 后端（mvn package，跳过测试）
# -----------------------------------------------------------------------------
echo "===== [1/2] Java 后端 (mvn -q -DskipTests package) ====="
MVN_MODS=(
  "m01-auth/backend"
  "m03-bim-gis/backend"
  "m04-delivery/backend"
  "m05-twin-ops/backend"
  "s2-cad-fusion/backend"
  "s3-review-engine/backend"
  "s4-bom-transform/backend"
  "screen/backend"
)
for m in "${MVN_MODS[@]}"; do
  echo ">> mvn package: $m"
  ( cd "$REPO_ROOT/packages/$m" && $MVN -q -DskipTests package )
done

# -----------------------------------------------------------------------------
# 2) 前端（vite build，按部署子路径设置 VITE_BASE）
#    格式：<module前端相对路径>|<VITE_BASE>
# -----------------------------------------------------------------------------
echo "===== [2/2] 前端 (npm install && VITE_BASE=... npm run build) ====="
FE_MODS=(
  "m06-portal|:/"
  "m03-bim-gis/frontend|:/modules/m03/"
  "s3-review-engine/frontend|:/modules/s3/"
  "m04-delivery/frontend|:/modules/m04/"
  "s2-cad-fusion/frontend|:/modules/s2/"
  "s4-bom-transform/frontend|:/modules/s4/"
  "s5-construction-monitor/frontend|:/modules/s5/"
)
for entry in "${FE_MODS[@]}"; do
  mod="${entry%%|*}"
  base="${entry##*|}"
  echo ">> vite build: $mod  (VITE_BASE=$base)"
  ( cd "$REPO_ROOT/packages/$mod" && npm install && VITE_BASE="$base" npm run build )
done

# -----------------------------------------------------------------------------
# 产物汇总
# -----------------------------------------------------------------------------
echo "===== 构建产物汇总 ====="
echo "[JARs]"
find "$REPO_ROOT/packages" -path "*/target/*.jar" -not -path "*/original-*" 2>/dev/null
echo "[DISTs]"
for entry in "${FE_MODS[@]}"; do
  mod="${entry%%|*}"
  echo "  $REPO_ROOT/packages/$mod/dist"
done
echo "===== 完成 ====="
