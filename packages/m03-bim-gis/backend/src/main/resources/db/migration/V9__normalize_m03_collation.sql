-- =============================================================================
-- V9：把 m03 全部 9 张表的排序规则显式钉死为 utf8mb4_unicode_ci
--
-- 背景（2026-09-15 空库演练 + 生产机探针实测）：
--   V1__init_m03_schema.sql 里 9 张表都只写了 `DEFAULT CHARSET=utf8mb4`、**没写 COLLATE**。
--   MySQL 此时的取值规则是：
--     · 写了 COLLATE        → 用写的那个；
--     · 只写 DEFAULT CHARSET → 取 **服务器变量 collation_server**（不是库默认值！）
--   实测证据（建一张探针表即可复现）：
--     · 生产机：@@collation_server = utf8mb4_0900_ai_ci → m03 九张表实际全是 0900_ai_ci
--     · 库 comm_platform 的默认 collation 却是 utf8mb4_unicode_ci —— 两者不同
--   也就是说：**这些表的排序规则取决于机器配置，同一份迁移在不同机器上结果不同**。
--   一旦将来有人写 m03 与 m04/s2/s3（这些是显式 unicode_ci 的模块）之间的
--   `JOIN ... ON a.col = b.col`，就会抛
--     1267 Illegal mix of collations (utf8mb4_0900_ai_ci) and (utf8mb4_unicode_ci)
--   属于"服务全起来、只有某个接口 500"的隐蔽故障。
--
-- 为什么统一到 utf8mb4_unicode_ci 而不是 0900_ai_ci：
--   ① 本仓库的建库语句（scripts/init-mysql.sql:7、deploy/db/init.sql）声明的是
--      `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`，这是作者的原始意图；
--   ② m01 / m04(s2/s3 同理) 共 25 张表已显式钉死 unicode_ci，统一到它改动面最小
--      （反向统一到 0900 要改 25 张已上线的表）。
--
-- 为什么用 CONVERT TO 而不是 ALTER TABLE ... COLLATE=：
--   `ALTER TABLE t COLLATE=...` 只改**表级默认值**，不会改已有 VARCHAR/TEXT 列的
--   各自 collation；只有 `CONVERT TO CHARACTER SET ... COLLATE ...` 才会连同列一起转换。
--
-- 外键影响：m03_generated_layout.task_id 上有一条外键 fk_m03_layout_task
--   → m03_design_task.id，两侧都是 **BIGINT**。CONVERT TO 只重写字符列，
--   数字列不变，故不会触发 errno 1832（Cannot change column: used in a foreign key）。
--
-- 幂等性：目标 collation 与当前一致时无需重建，可反复执行。
--   数据量：当前均为演示数据（数十行），重建代价可忽略。
-- =============================================================================

ALTER TABLE m03_project             CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_region              CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_device              CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_model               CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_design_scheme       CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_site                CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_parametric_template CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_design_task         CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE m03_generated_layout    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
