-- =============================================================================
-- V2：把 s4 两张表的排序规则显式钉死为 utf8mb4_unicode_ci
--
-- 背景（2026-09-15 空库演练 + 生产机探针实测）：
--   V1__s4_init.sql 里的 s4_bom_task / s4_bom_item 只写了 `DEFAULT CHARSET=utf8mb4`、
--   **没写 COLLATE**。MySQL 此时取的是**服务器变量 collation_server**，不是库默认值，
--   导致同一份迁移在不同机器上建出的 collation 不同（生产机实测为 utf8mb4_0900_ai_ci，
--   而库默认是 utf8mb4_unicode_ci）。一旦与显式 unicode_ci 的模块（m01/m04/s2/s3）
--   发生 `JOIN ... ON a.col = b.col`，就会抛
--     1267 Illegal mix of collations (utf8mb4_0900_ai_ci) and (utf8mb4_unicode_ci)
--
-- 统一到 utf8mb4_unicode_ci 的理由与 m03 V9 相同：
--   ① 建库语句（scripts/init-mysql.sql:7、deploy/db/init.sql）声明的就是 unicode_ci；
--   ② 仓库中已有 25 张表显式钉死 unicode_ci，统一到它改动面最小。
--
-- 为什么用 CONVERT TO 而不是 ALTER TABLE ... COLLATE=：
--   后者只改表级默认值，不改变已有 VARCHAR/TEXT 列的 collation。
--
-- 外键：s4 两张表均无外键，转换无约束风险。
-- 幂等性：目标 collation 一致时无需重建，可反复执行。
-- =============================================================================

ALTER TABLE s4_bom_task CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE s4_bom_item CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
