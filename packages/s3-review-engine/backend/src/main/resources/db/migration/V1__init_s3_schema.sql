-- V1: S3 审查引擎表结构（Flyway 迁移，禁止 DROP TABLE，全部 IF NOT EXISTS）
-- 运行于已选中的 comm_platform 库；每模块独立历史表 flyway_schema_history_s3

CREATE TABLE IF NOT EXISTS s3_safety_rule (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    rule_code VARCHAR(64) NOT NULL COMMENT '规则编号',
    rule_name VARCHAR(128) NOT NULL COMMENT '规则名称',
    category VARCHAR(64) NOT NULL COMMENT '规则分类',
    threshold VARCHAR(256) COMMENT '阈值条件',
    risk_level VARCHAR(32) NOT NULL COMMENT '风险等级 critical/error/warning',
    suggestion TEXT COMMENT '整改建议',
    status INT DEFAULT 1 COMMENT '状态 0禁用 1启用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_rule_code (rule_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='安全审查规则表';

CREATE TABLE IF NOT EXISTS s3_review_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    design_task_id VARCHAR(64) NOT NULL COMMENT '设计任务ID',
    task_name VARCHAR(128) NOT NULL COMMENT '任务名称',
    task_status VARCHAR(32) DEFAULT 'pending' COMMENT '任务状态 pending/running/completed/failed',
    coverage_rate DECIMAL(5,2) DEFAULT 0 COMMENT '覆盖率',
    total_count INT DEFAULT 0 COMMENT '总检查项数',
    critical_count INT DEFAULT 0 COMMENT '严重违规数',
    error_count INT DEFAULT 0 COMMENT '错误违规数',
    warning_count INT DEFAULT 0 COMMENT '警告违规数',
    create_by VARCHAR(64) COMMENT '创建人',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_design_task_id (design_task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审查任务主表';

CREATE TABLE IF NOT EXISTS s3_review_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    rule_id BIGINT NOT NULL COMMENT '规则ID',
    rule_code VARCHAR(64) NOT NULL COMMENT '规则编号',
    rule_name VARCHAR(128) NOT NULL COMMENT '规则名称',
    actual_value VARCHAR(256) COMMENT '实际值',
    standard_value VARCHAR(256) COMMENT '标准值',
    coordinates VARCHAR(256) COMMENT '三维坐标 [x,y,z]',
    risk_level VARCHAR(32) NOT NULL COMMENT '风险等级 critical/error/warning',
    remark TEXT COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_task_id (task_id),
    INDEX idx_rule_id (rule_id),
    INDEX idx_risk_level (risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='违规明细表';
