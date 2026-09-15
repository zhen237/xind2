-- =============================================================================
-- ⚠️ DEPRECATED（2026-09-15）—— 请勿启用本脚本
--
-- 本文件是早期用来手工建 m04 两张表的残留，现在**已不该再被执行**：
--   - 建表职责已由 Flyway 迁移承担：
--     db/migration/V1__init_m04_schema.sql（内容与本文件的 CREATE 部分一致）
--   - application.yml 里 spring.sql.init.mode = never，即本文件不会运行
--
-- 为什么必须保持 never —— 本文件开头就是两条破坏性语句：
--   DROP TABLE IF EXISTS m04_acceptance_task;
--   DROP TABLE IF EXISTS m04_acceptance_problem;
-- 一旦有人把 mode 改成 always，Spring Boot 会在每次启动时先 DROP 再重建这两张表，
-- **验收任务与问题记录会被无条件清空**（且 Flyway 侧无任何提示）。
--
-- 历史背景：生产库长期只靠本文件兜住建表，而 Flyway 的 V1 因 baseline-version 默认值
-- 1 被打成 BASELINE 记录、从未真正执行（见
-- docs/数据库迁移遗留问题-修复方案.md 新发现 N1）。2026-09-15 全库重建后已彻底
-- 收敛到 Flyway 单一路径，本文件不再是任何环境的依赖。
--
-- 若要清理：建议直接删除本文件，并同步移除 application.yml 里的 sql.init 配置节。
-- =============================================================================

DROP TABLE IF EXISTS m04_acceptance_task;
DROP TABLE IF EXISTS m04_acceptance_problem;

CREATE TABLE IF NOT EXISTS m04_acceptance_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT COMMENT '项目ID',
    task_name VARCHAR(200) NOT NULL COMMENT '任务名称',
    task_type VARCHAR(50) COMMENT '任务类型',
    status INT DEFAULT 0 COMMENT '状态：0-待验收，1-验收中，2-已通过，3-未通过',
    acceptance_standard TEXT COMMENT '验收标准',
    result_description TEXT COMMENT '结果描述',
    problem_count INT DEFAULT 0 COMMENT '问题数量',
    acceptance_by BIGINT COMMENT '验收人ID',
    acceptance_time DATETIME COMMENT '验收时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_project_id (project_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验收任务表';

CREATE TABLE IF NOT EXISTS m04_acceptance_problem (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT NOT NULL COMMENT '验收任务ID',
    problem_title VARCHAR(200) NOT NULL COMMENT '问题标题',
    problem_level INT DEFAULT 1 COMMENT '问题级别：1-一般，2-严重，3-重大',
    problem_description TEXT COMMENT '问题描述',
    photo_path VARCHAR(500) COMMENT '问题照片路径',
    status INT DEFAULT 0 COMMENT '状态：0-待整改，1-整改中，2-已整改，3-已复查',
    rectify_deadline DATE COMMENT '整改截止日期',
    rectify_result TEXT COMMENT '整改结果',
    rectify_by BIGINT COMMENT '整改人ID',
    review_by BIGINT COMMENT '复查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_task_id (task_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验收问题表';