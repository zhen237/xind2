-- =============================================================================
-- V10：为 m03_design_scheme 增加 pipeline_json 列
--
-- 背景（挑战杯 S1→S4 链路补增）：
--   QGIS 插件在上传设计成果时，body 顶层新增 pipelines 数组（管线工程量，
--   每元素为 Pipeline.to_dict()：pipeline_id/pipeline_type/fiber_type/length_m/coordinates...）。
--   DesignTask.resultJson 里不含管线，故管线单独落库到本列；
--   GET /api/m03/design/tasks/{id}/result 再按任务 task_no 读回并合并进 result.pipelines，
--   供 S4 生成 BOM（物料清单）。
--
-- 契约（冻结）：
--   列名 pipeline_json，TEXT NULL。DesignScheme 实体新增 pipelineJson 字段与之对应。
--   历史行保持 NULL；读侧对 NULL/空白有回退（designSchema.pipelines 保持 null），不会报错。
--
-- 为什么显式写 COLLATE utf8mb4_unicode_ci：
--   V9 已把 m03 全部表统一到 utf8mb4_unicode_ci；新增列必须显式钉死同一 collation，
--   否则会跟随服务端 @@collation_server（生产机实测为 utf8mb4_0900_ai_ci），
--   一旦将来与显式 unicode_ci 的模块做 JOIN/比较即抛
--     1267 Illegal mix of collations。此处显式声明以消除机器依赖性。
--
-- 幂等性说明：MySQL 8 不支持 ADD COLUMN IF NOT EXISTS，故用普通 ALTER。
--   本迁移由 Flyway 保证「仅执行一次」（已入 flyway_schema_history），重复建库场景不会重放。
-- =============================================================================

ALTER TABLE m03_design_scheme
    ADD COLUMN pipeline_json TEXT NULL COLLATE utf8mb4_unicode_ci
    COMMENT '管线工程量JSON快照(QGIS插件上传的DesignData.pipelines序列化)';
