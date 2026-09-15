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

echo "[ 数据库排序规则一致性 ]"
# 为什么查这个：建表若只写 `DEFAULT CHARSET=utf8mb4` 而不写 COLLATE，MySQL 取的是
# **服务器变量 collation_server**（不是库默认值）。同一份 DDL 在不同机器上会建出不同
# collation，于是 `JOIN ... ON a.col = b.col` 抛
#   1267 Illegal mix of collations (utf8mb4_0900_ai_ci) and (utf8mb4_unicode_ci)
# 表现为"服务都起来了、只有某个接口 500"。2026-09-15 就是这么发现 m05 的
# `m05_device LEFT JOIN shared_station ON station_code` 坏掉的。
# 这里断言真正参与跨表 JOIN 的两张表 collation 相等。
MYQ="mysql --defaults-file=/etc/mysql/debian.cnf -N -B"
if command -v mysql >/dev/null 2>&1 && $MYQ -e "SELECT 1" >/dev/null 2>&1; then
  C1=$($MYQ -e "SELECT TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA='comm_platform' AND TABLE_NAME='m05_device';" 2>/dev/null | head -1)
  C2=$($MYQ -e "SELECT TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA='comm_platform' AND TABLE_NAME='shared_station';" 2>/dev/null | head -1)
  if [ -n "$C1" ] && [ "$C1" = "$C2" ]; then
    printf "  [ OK ] %-24s m05_device == shared_station (%s)\n" "collation" "$C1"; OK=$((OK+1))
  else
    printf "  [FAIL] %-24s m05_device=%s shared_station=%s → JOIN 会 1267\n" "collation" "${C1:-缺表}" "${C2:-缺表}"; BAD=$((BAD+1))
  fi
  $MYQ -e "SELECT CONCAT('    分布: ', TABLE_COLLATION, '  x', COUNT(*)) FROM information_schema.TABLES WHERE TABLE_SCHEMA='comm_platform' GROUP BY TABLE_COLLATION ORDER BY 1;" 2>/dev/null
else
  printf "  [WARN] %-24s 取不到 MySQL（跳过）\n" "collation"
fi

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
