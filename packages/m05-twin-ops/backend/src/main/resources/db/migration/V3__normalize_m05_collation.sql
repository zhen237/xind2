-- =============================================================================
-- V3：把 m05 三张表的排序规则显式统一为 utf8mb4_unicode_ci
--
-- 背景（2026-09-15 空库演练 + 生产机实测）：
--   V1 的 m05_device / m05_alert 建表时只写了 `DEFAULT CHARSET=utf8mb4`、**没写 COLLATE**，
--   而 MySQL 此时取的是**服务器变量 collation_server**，不是数据库默认排序规则。
--   后果是同一份 DDL 在不同机器上建出不同的 collation：
--     · 本地演练机 collation_server = utf8mb4_0900_ai_ci → 表为 0900_ai_ci
--     · 生产机     collation_server = utf8mb4_0900_ai_ci → 表为 0900_ai_ci
--     （若某台机器改成 unicode_ci，同一条迁移就会建出 unicode_ci —— 不可控）
--   而 V2 新建的 shared_station 显式写了 utf8mb4_unicode_ci，
--   于是 `LEFT JOIN shared_station s ON d.station_code = s.station_code`
--   在**两台机器上都会**抛：
--     error 1267 Illegal mix of collations (utf8mb4_0900_ai_ci,IMPLICIT)
--                                      and (utf8mb4_unicode_ci,IMPLICIT) for operation '='
--   受影响接口：/api/m05/internal/screen/station-device-count、m05 设备详情。
--
-- 为什么用 CONVERT TO 而不是 ALTER TABLE ... COLLATE=：
--   `ALTER TABLE t COLLATE=utf8mb4_unicode_ci` 只改**表级默认值**，
--   **不会**改变已有 VARCHAR/TEXT 列各自的 collation；只有
--   `ALTER TABLE t CONVERT TO CHARACTER SET ... COLLATE ...` 才会把列一并转换。
--
-- 幂等性：目标 collation 与当前一致时 MySQL 直接跳过重建，可反复执行。
--   三张表由 V1 / V2 保证存在（本模块迁移链内，顺序确定）。
-- 数据量：m05 与 shared_station 目前均为演示数据（数十行），重建代价可忽略。
-- =============================================================================

ALTER TABLE m05_device     CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m05_alert      CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE shared_station CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
