-- ====================================================
-- M04 数智化交付模块数据库初始化脚本
-- 使用说明：
-- 1. 确保 MySQL 服务已经启动
-- 2. 使用命令行或 MySQL 客户端执行此脚本
-- 3. 命令示例：mysql -u root -p < scripts/init-m04-simple.sql
-- ====================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS comm_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE comm_platform;

-- ====================================================
-- M04 项目表
-- ====================================================
CREATE TABLE IF NOT EXISTS m04_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_name VARCHAR(200) NOT NULL COMMENT '项目名称',
    project_code VARCHAR(50) NOT NULL UNIQUE COMMENT '项目编号',
    region_code VARCHAR(50) COMMENT '区域编码',
    current_phase VARCHAR(50) DEFAULT 'PLANNING' COMMENT '当前阶段',
    phase_progress DECIMAL(5,2) DEFAULT 0 COMMENT '阶段进度',
    total_progress DECIMAL(5,2) DEFAULT 0 COMMENT '总进度',
    start_date DATE COMMENT '开工日期',
    planned_end_date DATE COMMENT '计划完工日期',
    actual_end_date DATE COMMENT '实际完工日期',
    construction_unit VARCHAR(200) COMMENT '施工单位',
    design_unit VARCHAR(200) COMMENT '设计单位',
    supervision_unit VARCHAR(200) COMMENT '监理单位',
    owner_unit VARCHAR(200) COMMENT '建设单位',
    status INT DEFAULT 1 COMMENT '状态 0:暂停 1:进行中 2:已完成',
    creator_id BIGINT COMMENT '创建人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目信息表';

-- ====================================================
-- M04 工单表
-- ====================================================
CREATE TABLE IF NOT EXISTS m04_work_order (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    order_no VARCHAR(50) NOT NULL UNIQUE COMMENT '工单编号',
    title VARCHAR(200) NOT NULL COMMENT '工单标题',
    type VARCHAR(50) COMMENT '工单类型',
    priority INT DEFAULT 2 COMMENT '优先级 1:高 2:中 3:低',
    status INT DEFAULT 0 COMMENT '状态 0:待处理 1:处理中 2:已完成 3:已关闭',
    station_code VARCHAR(50) COMMENT '站点编码',
    device_code VARCHAR(100) COMMENT '设备编码',
    assignee_id BIGINT COMMENT '处理人ID',
    creator_id BIGINT COMMENT '创建人ID',
    description TEXT COMMENT '工单描述',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单表';

-- ====================================================
-- 插入示例测试数据
-- ====================================================

-- 清空表（如果有旧数据）
-- TRUNCATE TABLE m04_project;
-- TRUNCATE TABLE m04_work_order;

-- 插入示例项目
INSERT INTO m04_project (project_name, project_code, region_code, current_phase, phase_progress, total_progress, start_date, planned_end_date, construction_unit, design_unit, supervision_unit, owner_unit, status) VALUES
('广州天河5G基站建设项目', 'PRJ-2026-001', 'CN_GZ', 'CONSTRUCTION', 65.00, 45.00, '2026-03-01', '2026-08-30', '中通建工有限公司', '华信设计院', '公诚监理', '广东移动', 1),
('深圳南山机房改造工程', 'PRJ-2026-002', 'CN_SZ', 'DESIGN', 90.00, 25.00, '2026-04-15', '2026-10-15', '深圳电信工程', '南方设计院', '深圳监理', '深圳电信', 1),
('北京朝阳管线敷设项目', 'PRJ-2026-003', 'CN_BJ', 'ACCEPTANCE', 95.00, 85.00, '2026-02-10', '2026-06-30', '北京工程局', '北京设计院', '北京监理', '北京移动', 1);

-- 插入示例工单
INSERT INTO m04_work_order (order_no, title, type, priority, status, station_code, device_code, description) VALUES
('WO20260520001', '基站高温告警处理', 'ALERT', 1, 1, 'ST001', 'BTS-1024', '机柜温度超过阈值，需现场检查空调运行状态'),
('WO20260521002', 'RRU驻波比异常排查', 'ALERT', 2, 0, 'ST002', 'BTS-2049', '驻波比超过1.5，需检查天线馈线连接'),
('WO20260522003', '季度安全巡检', 'INSPECTION', 3, 0, 'ST003', NULL, '2026年Q2安全巡检，重点检查防雷接地和临时用电');

-- ====================================================
-- 完成提示
-- ====================================================
SELECT '========================================' AS message;
SELECT 'M04 数据库初始化完成！' AS status;
SELECT '表 m04_project: 已创建 + 3条测试数据' AS info;
SELECT '表 m04_work_order: 已创建 + 3条测试数据' AS info2;
SELECT '现在可以正常使用 M04 功能了' AS next;
SELECT '========================================' AS end;
