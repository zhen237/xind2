-- =============================================================================
-- V3：s3_design_data —— S1 图纸设计数据永久落库表
--
-- 背景（2026-09-15 生产读接口扫荡发现）：
--   实体 s3/entity/S3DesignData.java（@TableName("s3_design_data")）在代码里被
--   cache/DesignDataCacheService.java 的三级缓存（内存 → Redis → MySQL）读写，
--   但 V1/V2 都没建这张表，且**全仓库没有任何 .sql 定义过它**（只在实体里存在）。
--   属于潜在 500：库为空、缓存命中时看不出来，一旦缓存失效要回 MySQL 恢复就报
--   Table 'comm_platform.s3_design_data' doesn't exist。
--
-- 列名按实体字段推导（驼峰 → 下划线），已用 check_schema_entity.py 复核一致：
--   designTaskId   → design_task_id    （@TableId，String，对应 S1 的图纸标识）
--   designDataJson → design_data_json  （完整 designData JSON，大字段）
--   projectMetaJson→ project_meta_json （工程元信息 JSON）
--   taskId         → task_id           （首次创建该图纸的审查任务 ID）
--   createTime     → create_time
--
-- 幂等性：CREATE TABLE IF NOT EXISTS + 索引并入建表 KEY。
-- 无种子数据：本表是运行期缓存落库，由服务在收到 S1 图纸时写入，不应预置。
-- =============================================================================

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS s3_design_data (
    design_task_id VARCHAR(64) NOT NULL COMMENT 'S1 图纸标识（主键，对应 S1DesignDataDTO.designTaskId）',
    design_data_json LONGTEXT COMMENT 'S1 传入的完整 designData JSON（缓存 wrapper：{"design_data":{...}}）',
    project_meta_json TEXT COMMENT '工程元信息 JSON（projectName/region/designType/deviceCount/layerCounts）',
    task_id BIGINT COMMENT '首次创建该图纸的审查任务 ID（审计用）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (design_task_id),
    KEY idx_s3_design_data_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='S1 图纸设计数据永久落库表';
