#!/usr/bin/env bash
# =============================================================================
# health.sh  —  xind2 一键健康检查（后端端口 + 前端页面 + 资源占用）
# 用法：  bash /opt/xind2/scripts/health.sh
# 退出码： 0 = 全部正常；1 = 有服务异常
# =============================================================================
set -u

JAVA_SVC=(
  "m01-auth:8080" "m03-bim-gis:8083" "m04-delivery:8084" "m05-twin-ops:8085"
  "screen:8087" "s3-review-engine:8089" "s4-bom-transform:8090" "s2-cad-fusion:8096"
)
NODE_SVC=( "s5-construction-monitor:8091" )
PY_SVC=(
  "s3-rules:8000" "s2-engine:8092" "s4-engine:8100"
  "m03-topology-engine:9001" "m03-llm-service:9002"
)
FRONT=(
  "/:portal" "/modules/m03/:m03" "/modules/m04/:m04" "/modules/s2/:s2"
  "/modules/s3/:s3" "/modules/s4/:s4" "/modules/s5/:s5"
)

OK=0; BAD=0

probe_port() { # <name> <port>
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "http://127.0.0.1:$2/" 2>/dev/null)
  if [ -n "$code" ] && [ "$code" != "000" ]; then
    printf "  [ OK ] %-24s :%-5s  HTTP %s\n" "$1" "$2" "$code"; OK=$((OK+1))
  else
    printf "  [FAIL] %-24s :%-5s  无响应\n" "$1" "$2"; BAD=$((BAD+1))
  fi
}

probe_front() { # <path> <name>
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 6 "http://127.0.0.1$1" 2>/dev/null)
  if [ "$code" = "200" ]; then
    printf "  [ OK ] %-24s %-18s HTTP %s\n" "$2" "$1" "$code"; OK=$((OK+1))
  else
    printf "  [FAIL] %-24s %-18s HTTP %s\n" "$2" "$1" "${code:-无响应}"; BAD=$((BAD+1))
  fi
}

echo "=============================================="
echo " xind2 健康检查  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

echo "[ Java 后端 ]"
for s in "${JAVA_SVC[@]}"; do probe_port "${s%%:*}" "${s##*:}"; done

echo "[ Node 后端 ]"
for s in "${NODE_SVC[@]}"; do probe_port "${s%%:*}" "${s##*:}"; done

echo "[ Python 引擎 (仅 127.0.0.1) ]"
for s in "${PY_SVC[@]}"; do probe_port "${s%%:*}" "${s##*:}"; done

echo "[ 前端 (经 nginx :80) ]"
for s in "${FRONT[@]}"; do probe_front "${s%%:*}" "${s##*:}"; done

echo "[ 基础设施 ]"
for c in nginx mysql redis-server fail2ban; do
  st=$(systemctl is-active "$c" 2>/dev/null || echo unknown)
  if [ "$st" = "active" ]; then printf "  [ OK ] %-24s %s\n" "$c" "$st"; OK=$((OK+1));
  else printf "  [FAIL] %-24s %s\n" "$c" "$st"; BAD=$((BAD+1)); fi
done

echo "[ 资源 ]"
free -m | awk '/^Mem:/{printf "  内存: 已用 %s MB / 共 %s MB\n", $3, $2}'
free -m | awk '/^Swap:/{printf "  Swap: 已用 %s MB / 共 %s MB\n", $3, $2}'
df -h / | awk 'NR==2{printf "  磁盘: 已用 %s / 共 %s (%s)\n", $3, $2, $5}'
echo "  末尾异常日志（若有）:"
for f in /opt/xind2/logs/*.out; do
  n=$(basename "$f" .out)
  last=$(grep -iE "error|exception|traceback|refused" "$f" 2>/dev/null | tail -1)
  [ -n "$last" ] && printf "    %-24s %s\n" "$n" "${last:0:110}"
done

echo "=============================================="
echo " 通过 $OK 项，异常 $BAD 项"
echo "=============================================="
[ "$BAD" -eq 0 ] || exit 1
