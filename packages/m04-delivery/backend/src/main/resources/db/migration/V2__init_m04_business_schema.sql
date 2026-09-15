-- =============================================================================
-- V2：M04 交付模块业务表补全（9 张）
--
-- 背景（2026-09-15 生产读接口扫荡发现）：
--   m04 的 V1 只建了 m04_acceptance_task / m04_acceptance_problem 两张表，
--   其余 9 张业务表只写在遗留脚本 scripts/init-m04.sql 与 scripts/init-mysql.sql 里，
--   **从未进迁移链**。结果生产/本地都缺这 9 张表 → 17 个读接口 500：
--     Table 'comm_platform.m04_project' doesn't exist 等 8 张表同款报错 +
--     大屏 /api/screen/* 因 M04 来源数据取不到而静默归零。
--
-- 表结构来源：scripts/init-m04.sql（与 scripts/init-mysql.sql 中的定义一致），
--   已用 check_schema_entity.py 逐表比对 m04 实体字段，9 张表全部
--   「实体列数 == DDL 列数」，无缺列，可安全移植。
--
-- 幂等性：CREATE TABLE IF NOT EXISTS + 索引并入建表 KEY 子句
--   （遗留脚本里的独立 CREATE INDEX 不是幂等的，MySQL 8 无 CREATE INDEX IF NOT EXISTS）。
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- 项目
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_name VARCHAR(200) NOT NULL COMMENT '项目名称',
    project_code VARCHAR(50) NOT NULL COMMENT '项目编号',
    region_code VARCHAR(20) COMMENT '区域编码',
    current_phase VARCHAR(50) COMMENT '当前阶段',
    phase_progress DECIMAL(5,2) DEFAULT 0 COMMENT '阶段进度',
    total_progress DECIMAL(5,2) DEFAULT 0 COMMENT '总进度',
    start_date DATE COMMENT '开工日期',
    planned_end_date DATE COMMENT '计划完工日期',
    actual_end_date DATE COMMENT '实际完工日期',
    construction_unit VARCHAR(200) COMMENT '施工单位',
    design_unit VARCHAR(200) COMMENT '设计单位',
    supervision_unit VARCHAR(200) COMMENT '监理单位',
    owner_unit VARCHAR(200) COMMENT '建设单位',
    status INT DEFAULT 0 COMMENT '状态 0-在建 1-竣工 2-验收',
    creator_id BIGINT COMMENT '创建人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_m04_project_code (project_code),
    KEY idx_m04_project_region (region_code),
    KEY idx_m04_project_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目信息表';

-- -----------------------------------------------------------------------------
-- 工单
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_work_order (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    order_no VARCHAR(50) NOT NULL COMMENT '工单编号',
    title VARCHAR(200) NOT NULL COMMENT '工单标题',
    type VARCHAR(50) COMMENT '工单类型',
    priority INT DEFAULT 1 COMMENT '优先级 1-低 2-中 3-高',
    status INT DEFAULT 0 COMMENT '状态 0-待处理 1-处理中 2-已完成 3-已关闭',
    station_code VARCHAR(50) COMMENT '站点编码',
    device_code VARCHAR(50) COMMENT '设备编码',
    assignee_id BIGINT COMMENT '处理人ID',
    creator_id BIGINT COMMENT '创建人ID',
    description TEXT COMMENT '工单描述',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_m04_work_order_no (order_no),
    KEY idx_m04_work_order_status (status),
    KEY idx_m04_work_order_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单表';

-- -----------------------------------------------------------------------------
-- 交付包
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_delivery_package (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    package_name VARCHAR(200) COMMENT '交付包名称',
    package_type VARCHAR(50) COMMENT '交付包类型',
    status INT DEFAULT 0 COMMENT '状态 0-待打包 1-已打包 2-已归档',
    file_count INT DEFAULT 0 COMMENT '文件数量',
    total_size BIGINT DEFAULT 0 COMMENT '总大小(字节)',
    minio_path VARCHAR(500) COMMENT 'MinIO存储路径',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    KEY idx_m04_delivery_package_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交付包表';

-- -----------------------------------------------------------------------------
-- 交付文件明细
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_delivery_file (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    package_id BIGINT NOT NULL COMMENT '交付包ID',
    file_name VARCHAR(200) COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
    file_type VARCHAR(50) COMMENT '文件类型',
    md5 VARCHAR(32) COMMENT '文件MD5',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_m04_delivery_file_package (package_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交付文件明细表';

-- -----------------------------------------------------------------------------
-- 资质验证（安全监管）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_cert_verification (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    person_name VARCHAR(100) COMMENT '人员姓名',
    id_card VARCHAR(20) COMMENT '身份证号',
    cert_type VARCHAR(50) COMMENT '证件类型',
    cert_number VARCHAR(50) COMMENT '证件编号',
    issuing_authority VARCHAR(200) COMMENT '发证机关',
    valid_from DATE COMMENT '有效期起',
    valid_to DATE COMMENT '有效期至',
    photo_distance VARCHAR(500) COMMENT '远景照片路径',
    photo_close VARCHAR(500) COMMENT '近景照片路径',
    video_path VARCHAR(500) COMMENT '视频路径',
    verify_result INT DEFAULT 0 COMMENT '验证结果 0-通过 1-不通过',
    verify_comment TEXT COMMENT '验证备注',
    verify_by BIGINT COMMENT '验证人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_m04_cert_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资质验证表';

-- -----------------------------------------------------------------------------
-- 安全检查
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_safety_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    check_date DATE COMMENT '检查日期',
    equipment_type VARCHAR(100) COMMENT '设备类型',
    brand_model VARCHAR(100) COMMENT '品牌型号',
    production_date DATE COMMENT '生产日期',
    valid_date DATE COMMENT '有效期至',
    last_test_date DATE COMMENT '上次检测日期',
    test_report_no VARCHAR(50) COMMENT '检测报告编号',
    quantity INT DEFAULT 0 COMMENT '数量',
    appearance_status VARCHAR(200) COMMENT '外观状态',
    photo_path VARCHAR(500) COMMENT '照片路径',
    check_result INT DEFAULT 0 COMMENT '检查结果 0-合格 1-不合格',
    check_by BIGINT COMMENT '检查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_m04_safety_check_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='安全检查表';

-- -----------------------------------------------------------------------------
-- 施工记录
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_construction_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    responsible_person VARCHAR(100) COMMENT '负责人',
    work_date DATE COMMENT '施工日期',
    work_content TEXT COMMENT '施工内容',
    construction_units VARCHAR(500) COMMENT '施工班组',
    environment_assessment INT DEFAULT 0 COMMENT '环境评估 0-正常 1-异常',
    hazard_description TEXT COMMENT '危险源描述',
    video_path VARCHAR(500) COMMENT '视频路径',
    photo_panorama VARCHAR(500) COMMENT '全景照片路径',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_m04_construction_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='施工记录表';

-- -----------------------------------------------------------------------------
-- 围挡检查
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_barrier_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    check_date DATE COMMENT '检查日期',
    barrier_integrity INT DEFAULT 0 COMMENT '围挡完整性 0-完整 1-破损',
    sign_list TEXT COMMENT '标识清单',
    night_light_status INT DEFAULT 0 COMMENT '夜间照明状态 0-正常 1-异常',
    road_photo VARCHAR(500) COMMENT '道路照片路径',
    environment_risk VARCHAR(500) COMMENT '环境风险',
    check_conclusion INT DEFAULT 0 COMMENT '检查结论 0-合格 1-不合格',
    check_by BIGINT COMMENT '检查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_m04_barrier_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='围挡检查表';

-- -----------------------------------------------------------------------------
-- 用电检查
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m04_electricity_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    check_date DATE COMMENT '检查日期',
    distribution_box_no VARCHAR(50) COMMENT '配电箱编号',
    circuit_count INT DEFAULT 0 COMMENT '回路数量',
    leakage_protector_model VARCHAR(100) COMMENT '漏电保护器型号',
    leakage_protector_count INT DEFAULT 0 COMMENT '漏电保护器数量',
    one_machine_one_switch INT DEFAULT 0 COMMENT '一机一闸 0-是 1-否',
    cable_status VARCHAR(200) COMMENT '电缆状态',
    ground_resistance DECIMAL(10,2) COMMENT '接地电阻值',
    box_surrounding VARCHAR(200) COMMENT '箱体周边环境',
    photo_path VARCHAR(500) COMMENT '照片路径',
    check_conclusion INT DEFAULT 0 COMMENT '检查结论 0-合格 1-不合格',
    check_by BIGINT COMMENT '检查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_m04_electricity_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用电检查表';


-- =============================================================================
-- 初始化数据：8 个演示项目（与遗留脚本 scripts/init-mysql.sql 一致）
-- 幂等：m04_project.project_code 有 UNIQUE 约束，INSERT IGNORE 生效
-- =============================================================================
INSERT IGNORE INTO m04_project
    (project_name, project_code, region_code, current_phase, phase_progress, total_progress,
     start_date, planned_end_date, construction_unit, design_unit, supervision_unit, owner_unit, status)
VALUES
('广州天河5G覆盖提升项目',    'PRJ-2026-001', 'CN_GZ', 'CONSTRUCTION', 65.00, 45.00, '2026-03-01', '2026-08-30', '中通建工有限公司', '华信设计院', '公诚监理',   '广东移动', 1),
('深圳南山科技园扩容工程',    'PRJ-2026-002', 'CN_SZ', 'DESIGN',       90.00, 25.00, '2026-04-15', '2026-10-15', '深圳电信工程',     '南方设计院', '深圳监理',   '深圳电信', 1),
('北京中关村核心区优化项目',  'PRJ-2026-003', 'CN_BJ', 'ACCEPTANCE',   95.00, 85.00, '2026-02-10', '2026-06-30', '北京工程局',       '北京设计院', '北京监理',   '北京移动', 1),
('杭州西湖景区5G覆盖项目',    'PRJ-2026-004', 'CN_HZ', 'CONSTRUCTION', 40.00, 30.00, '2026-05-01', '2026-11-30', '浙江建工集团',     '浙江设计院', '浙江监理',   '浙江移动', 1),
('成都天府新区新基建项目',    'PRJ-2026-005', 'CN_CD', 'PLANNING',     20.00, 10.00, '2026-06-15', '2027-03-15', '四川建工集团',     '四川设计院', '四川监理',   '四川移动', 1),
('西安文旅5G智慧项目',        'PRJ-2026-006', 'CN_XA', 'DESIGN',       70.00, 20.00, '2026-04-01', '2026-12-01', '陕西建工集团',     '西北设计院', '陕西监理',   '陕西移动', 1),
('上海陆家嘴金融区5G专网',    'PRJ-2026-007', 'CN_SH', 'CONSTRUCTION', 80.00, 55.00, '2026-02-20', '2026-09-20', '上海建工集团',     '华东设计院', '上海监理',   '上海电信', 1),
('大连沿海经济带通信项目',    'PRJ-2026-008', 'CN_DL', 'PLANNING',     15.00,  8.00, '2026-07-01', '2027-02-28', '辽宁建工集团',     '东北设计院', '辽宁监理',   '辽宁移动', 1);
