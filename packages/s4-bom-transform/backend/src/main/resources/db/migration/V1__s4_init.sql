-- ============================================================
-- S4 施工指令转化（BOM）— 数据库建表 DDL
-- 数据库: comm_platform | 表前缀: s4_
-- ============================================================

-- 1. BOM 任务表
CREATE TABLE IF NOT EXISTS s4_bom_task (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    task_id         VARCHAR(64)     NOT NULL UNIQUE          COMMENT '任务 ID（UUID）',
    design_task_id  VARCHAR(64)                              COMMENT '关联 S1 设计任务 ID',
    project_id      VARCHAR(64)                              COMMENT '项目 ID',
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending' COMMENT 'pending / running / done / failed',
    error_message   VARCHAR(512)                             COMMENT '失败时的错误信息',
    total_categories INT            DEFAULT 0                COMMENT '总类目数',
    total_qty       INT             DEFAULT 0                COMMENT '总数量',
    main_device_qty INT             DEFAULT 0                COMMENT '主设备数量',
    auxiliary_qty   INT             DEFAULT 0                COMMENT '辅材数量',
    cable_qty       INT             DEFAULT 0                COMMENT '线缆数量',
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    finished_at     DATETIME                                 COMMENT '完成时间',
    process_requirements TEXT                                COMMENT '关键工序工艺要求（JSON）',
    fiber_allocation     TEXT                                COMMENT '纤芯分配表（JSON）',
    INDEX idx_project (project_id),
    INDEX idx_design  (design_task_id),
    INDEX idx_status  (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BOM 任务表';

-- 2. BOM 物料明细表
CREATE TABLE IF NOT EXISTS s4_bom_item (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    task_id         VARCHAR(64)     NOT NULL                 COMMENT '关联 BOM 任务 taskId',
    material_code   VARCHAR(32)     NOT NULL                 COMMENT '物料编码（如 M-ANT-001）',
    material_name   VARCHAR(128)    NOT NULL                 COMMENT '物料名称',
    spec            VARCHAR(128)                             COMMENT '规格型号',
    unit            VARCHAR(16)                              COMMENT '单位（套/根/包/件）',
    qty             INT             NOT NULL DEFAULT 0       COMMENT '数量',
    single_length   DECIMAL(10,2)                            COMMENT '单根长度（米，线缆专用）',
    total_length    DECIMAL(10,2)                            COMMENT '总长度（米，线缆专用）',
    category        VARCHAR(20)     NOT NULL                 COMMENT 'main_device / auxiliary / cable',
    device_name     VARCHAR(128)                             COMMENT '关联设备名称（如 AAU-扇区1）',
    device_type     VARCHAR(32)                              COMMENT '关联设备类型（如 antenna / rru / bbu）',
    INDEX idx_task_id (task_id),
    INDEX idx_material_code (material_code),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BOM 物料明细表';
