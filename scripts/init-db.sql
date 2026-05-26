CREATE DATABASE IF NOT EXISTS comm_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE comm_platform;

-- ==================== M01 认证相关表 ====================
CREATE TABLE m01_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    real_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    status TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE m01_role (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_code VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m01_user_role (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE m01_menu (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    parent_id BIGINT DEFAULT 0,
    menu_code VARCHAR(50) NOT NULL UNIQUE,
    menu_name VARCHAR(100) NOT NULL,
    menu_type TINYINT DEFAULT 1 COMMENT '1:目录 2:菜单 3:按钮',
    iframe_url VARCHAR(255) COMMENT '子应用入口URL',
    permission_code VARCHAR(100) COMMENT '权限标识',
    sort_order INT DEFAULT 0,
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m01_role_menu (
    role_id BIGINT NOT NULL,
    menu_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, menu_id)
);

CREATE TABLE m01_operation_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    username VARCHAR(50),
    operation_type VARCHAR(50),
    operation_desc VARCHAR(500),
    module_code VARCHAR(50),
    ip_address VARCHAR(50),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== shared_ 共享表 ====================
CREATE TABLE shared_region (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL UNIQUE,
    region_name VARCHAR(100) NOT NULL,
    parent_code VARCHAR(50),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shared_station (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    station_code VARCHAR(50) NOT NULL UNIQUE,
    station_name VARCHAR(200),
    region_code VARCHAR(50),
    longitude DECIMAL(10,7),
    latitude DECIMAL(10,7),
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== M02 数通网络规划与仿真 ====================
CREATE TABLE m02_plan (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(200),
    plan_desc VARCHAR(500),
    region_code VARCHAR(50),
    status TINYINT DEFAULT 0 COMMENT '0:草稿 1:已发布',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE m02_station_plan (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_id BIGINT,
    station_code VARCHAR(50),
    longitude DECIMAL(10,7),
    latitude DECIMAL(10,7),
    height DECIMAL(5,2),
    antenna_count INT DEFAULT 1,
    azimuth VARCHAR(100),
    downtilt VARCHAR(100),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m02_simulation_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_id BIGINT,
    station_code VARCHAR(50),
    rsrp_value DECIMAL(10,2),
    sinr_value DECIMAL(10,2),
    coverage_type VARCHAR(50),
    sim_time DATETIME,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== M03 BIM+GIS 三维设计 ====================
-- M03表已在 scripts/init-m03.sql 中定义，请先执行 init-m03.sql
-- 此处仅保留跨模块索引

-- ==================== M04 数智化交付与工作流 ====================
CREATE TABLE m04_work_order (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE,
    title VARCHAR(200),
    type VARCHAR(50),
    priority TINYINT DEFAULT 2 COMMENT '1:高 2:中 3:低',
    status TINYINT DEFAULT 0 COMMENT '0:待处理 1:处理中 2:已完成 3:已关闭',
    station_code VARCHAR(50),
    device_code VARCHAR(100),
    assignee_id BIGINT,
    creator_id BIGINT,
    description TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE m04_inspection_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(50),
    inspect_item VARCHAR(200),
    inspect_result TINYINT COMMENT '1:合格 0:不合格',
    problem_desc VARCHAR(500),
    photo_path VARCHAR(500),
    inspector_id BIGINT,
    inspect_time DATETIME,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m04_delivery_package (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    package_no VARCHAR(50) UNIQUE,
    project_id BIGINT,
    status TINYINT DEFAULT 0 COMMENT '0:打包中 1:已归档',
    file_count INT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== M05 数字孪生与智慧运维 ====================
CREATE TABLE m05_device (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_code VARCHAR(100) UNIQUE,
    device_name VARCHAR(200),
    device_type VARCHAR(50),
    station_code VARCHAR(50),
    install_time DATETIME,
    status TINYINT DEFAULT 1 COMMENT '1:在线 0:离线 2:故障',
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m05_alert (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT,
    device_code VARCHAR(100),
    alert_content VARCHAR(500),
    level TINYINT COMMENT '1:紧急 2:重要 3:警告 4:提示',
    status TINYINT DEFAULT 0 COMMENT '0:未处理 1:已确认 2:已解决',
    source VARCHAR(50),
    order_no VARCHAR(50),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE m05_maintenance_plan (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(200),
    device_code VARCHAR(100),
    plan_type VARCHAR(50) COMMENT 'daily/weekly/monthly/yearly',
    next_exec_time DATETIME,
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m05_inspection_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(200),
    station_code VARCHAR(50),
    route_json TEXT,
    assignee_id BIGINT,
    status TINYINT DEFAULT 0 COMMENT '0:待执行 1:执行中 2:已完成',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    execute_time DATETIME
);

-- ==================== M04 项目进程与视频监理 ====================
CREATE TABLE m04_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(200) NOT NULL,
    project_code VARCHAR(50) UNIQUE,
    region_code VARCHAR(50),
    current_phase VARCHAR(50) DEFAULT 'PLANNING' COMMENT 'PLANNING/DESIGN/CONSTRUCTION/ACCEPTANCE/OPS',
    phase_progress DECIMAL(5,2) DEFAULT 0 COMMENT '当前阶段进度百分比',
    total_progress DECIMAL(5,2) DEFAULT 0 COMMENT '总进度百分比',
    start_date DATE,
    planned_end_date DATE,
    actual_end_date DATE,
    construction_unit VARCHAR(200) COMMENT '施工单位',
    design_unit VARCHAR(200) COMMENT '设计单位',
    supervision_unit VARCHAR(200) COMMENT '监理单位',
    owner_unit VARCHAR(200) COMMENT '建设单位',
    status TINYINT DEFAULT 1 COMMENT '0:暂停 1:进行中 2:已完成',
    creator_id BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 人员证书验证记录
CREATE TABLE m04_cert_verification (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    person_name VARCHAR(100) NOT NULL COMMENT '人员姓名',
    id_card VARCHAR(18) COMMENT '身份证号',
    cert_type VARCHAR(50) NOT NULL COMMENT '电工证/登高证/安全员证/焊工证',
    cert_number VARCHAR(100) COMMENT '证书编号',
    issuing_authority VARCHAR(200) COMMENT '发证机关',
    valid_from DATE COMMENT '有效期起',
    valid_to DATE COMMENT '有效期止',
    photo_distance VARCHAR(500) COMMENT '远拍照片MinIO路径',
    photo_close VARCHAR(500) COMMENT '证件特写照片MinIO路径',
    video_path VARCHAR(500) COMMENT '视频片段MinIO路径',
    verify_result TINYINT DEFAULT 0 COMMENT '0:待审核 1:通过 2:不通过',
    verify_comment VARCHAR(500),
    verify_by BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 安全防护检查记录
CREATE TABLE m04_safety_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    check_date DATE NOT NULL,
    equipment_type VARCHAR(50) NOT NULL COMMENT 'HELMET/BELT/FALL_ARRESTER/INSULATED_SHOES/INSULATED_GLOVES',
    brand_model VARCHAR(200) COMMENT '品牌型号',
    production_date DATE COMMENT '生产日期',
    valid_date DATE COMMENT '有效期',
    last_test_date DATE COMMENT '最近检测日期',
    test_report_no VARCHAR(100) COMMENT '检测报告编号',
    quantity INT DEFAULT 1 COMMENT '数量',
    appearance_status VARCHAR(20) COMMENT 'GOOD/DAMAGED/EXPIRED',
    photo_path VARCHAR(500) COMMENT '照片MinIO路径(含日期特写)',
    check_result TINYINT COMMENT '0:不合格 1:合格',
    check_by BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 施工总体情况记录
CREATE TABLE m04_construction_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    responsible_person VARCHAR(100) NOT NULL COMMENT '现场负责人',
    work_date DATE NOT NULL COMMENT '施工日期',
    work_content TEXT COMMENT '当日工作内容',
    construction_units TEXT COMMENT '参建单位JSON(建设/设计/施工/监理)',
    environment_assessment TINYINT COMMENT '0:有隐患 1:无隐患',
    hazard_description VARCHAR(500) COMMENT '隐患描述',
    video_path VARCHAR(500) COMMENT '视频路径',
    photo_panorama VARCHAR(500) COMMENT '全景照片路径',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 安全围栏及警示标志检查
CREATE TABLE m04_barrier_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    check_date DATE NOT NULL,
    barrier_integrity TINYINT COMMENT '0:不合格 1:合格(围挡完整/高度达标)',
    sign_list TEXT COMMENT '警示标志清单JSON',
    night_light_status TINYINT COMMENT '0:故障 1:正常',
    road_photo VARCHAR(500) COMMENT '道路角度照片MinIO路径',
    environment_risk VARCHAR(500) COMMENT '周围环境风险评估',
    check_conclusion TINYINT COMMENT '0:不合格 1:合格',
    check_by BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 临时用电检查记录
CREATE TABLE m04_electricity_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    check_date DATE NOT NULL,
    distribution_box_no VARCHAR(100) COMMENT '配电箱编号',
    circuit_count INT COMMENT '回路数量',
    leakage_protector_model VARCHAR(100) COMMENT '漏电保护器型号',
    leakage_protector_count INT COMMENT '漏电保护器数量',
    one_machine_one_switch TINYINT COMMENT '一机一闸一漏一箱: 0:不合格 1:合格',
    cable_status VARCHAR(20) COMMENT '线缆状态: GOOD/DAMAGED/EXPOSED',
    ground_resistance DECIMAL(5,2) COMMENT '接地电阻值(Ω)',
    box_surrounding VARCHAR(20) COMMENT '配电箱周围环境: CLEAR/OBSTRUCTED',
    photo_path VARCHAR(500) COMMENT '照片MinIO路径',
    check_conclusion TINYINT COMMENT '0:不合格 1:合格',
    check_by BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 索引 ====================
CREATE INDEX idx_m01_username ON m01_user(username);
CREATE INDEX idx_m01_user_status ON m01_user(status);
CREATE INDEX idx_m03_device_type ON m03_device(device_type);
CREATE INDEX idx_m03_device_project ON m03_device(project_id);
CREATE INDEX idx_m04_project_phase ON m04_project(current_phase);
CREATE INDEX idx_m04_project_status ON m04_project(status);
CREATE INDEX idx_m04_workorder_status ON m04_work_order(status);
CREATE INDEX idx_m04_workorder_assignee ON m04_work_order(assignee_id);
CREATE INDEX idx_m04_cert_project ON m04_cert_verification(project_id);
CREATE INDEX idx_m04_safety_project ON m04_safety_check(project_id);
CREATE INDEX idx_m04_barrier_project ON m04_barrier_check(project_id);
CREATE INDEX idx_m04_electricity_project ON m04_electricity_check(project_id);
CREATE INDEX idx_m05_device_station ON m05_device(station_code);
CREATE INDEX idx_m05_device_status ON m05_device(status);
CREATE INDEX idx_m05_alert_status ON m05_alert(status);
CREATE INDEX idx_m05_alert_level ON m05_alert(level);
CREATE INDEX idx_m05_alert_device ON m05_alert(device_code);
CREATE INDEX idx_shared_station_region ON shared_station(region_code);

-- ==================== 创建M05专用数据库用户 ====================
CREATE USER IF NOT EXISTS 'appuser'@'localhost' IDENTIFIED WITH mysql_native_password BY 'apppass123';
CREATE USER IF NOT EXISTS 'appuser'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY 'apppass123';
GRANT SELECT, INSERT, UPDATE, DELETE ON comm_platform.m05_device TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE, DELETE ON comm_platform.m05_alert TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE, DELETE ON comm_platform.m05_maintenance_plan TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE, DELETE ON comm_platform.m05_inspection_task TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
GRANT SELECT ON comm_platform.shared_station TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
GRANT SELECT ON comm_platform.shared_region TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
GRANT SELECT ON comm_platform.m03_model TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE ON comm_platform.m04_work_order TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
FLUSH PRIVILEGES;

-- ==================== 初始化数据 ====================
-- 初始化用户（密码为 BCrypt 加密后的 admin123）
INSERT INTO m01_user (username, password, real_name, email, status) VALUES 
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '超级管理员', 'admin@example.com', 1),
('operator', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '运维人员', 'operator@example.com', 1),
('designer', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '设计人员', 'designer@example.com', 1),
('planner', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '规划人员', 'planner@example.com', 1);

INSERT INTO m01_role (role_code, role_name, description) VALUES 
('admin', '超级管理员', '系统超级管理员'),
('operator', '运维人员', '日常运维操作人员'),
('designer', '设计人员', 'BIM设计人员'),
('planner', '规划人员', '网络规划人员');

INSERT INTO m01_menu (parent_id, menu_code, menu_name, menu_type, iframe_url, permission_code, sort_order) VALUES 
(0, 'system', '系统管理', 1, NULL, 'system:view', 1),
(1, 'system_user', '用户管理', 2, '/modules/m01/user.html', 'system:user:view', 1),
(1, 'system_role', '角色管理', 2, '/modules/m01/role.html', 'system:role:view', 2),
(1, 'system_menu', '菜单管理', 2, '/modules/m01/menu.html', 'system:menu:view', 3),
(0, 'simulation', '网络规划', 1, NULL, 'simulation:view', 2),
(5, 'sim_plan', '规划方案', 2, '/modules/m02/plan.html', 'simulation:plan:view', 1),
(5, 'sim_simulation', '覆盖仿真', 2, '/modules/m02/simulation.html', 'simulation:sim:view', 2),
(0, 'design', '三维设计', 1, NULL, 'design:view', 3),
(8, 'design_project', '项目管理', 2, '/modules/m03/project.html', 'design:project:view', 1),
(8, 'design_model', '模型管理', 2, '/modules/m03/model.html', 'design:model:view', 2),
(8, 'design_collision', '碰撞检测', 2, '/modules/m03/collision.html', 'design:collision:view', 3),
(0, 'delivery', '数智交付', 1, NULL, 'delivery:view', 4),
(11, 'delivery_order', '工单管理', 2, '/modules/m04/order.html', 'delivery:order:view', 1),
(11, 'delivery_inspection', '验收管理', 2, '/modules/m04/inspection.html', 'delivery:inspection:view', 2),
(11, 'delivery_package', '交付包管理', 2, '/modules/m04/package.html', 'delivery:package:view', 3),
(0, 'twin', '数字孪生', 1, NULL, 'twin:view', 5),
(14, 'twin_monitor', '实时监控', 2, '/modules/m05/monitor.html', 'twin:monitor:view', 1),
(14, 'twin_alert', '告警管理', 2, '/modules/m05/alert.html', 'twin:alert:view', 2),
(14, 'twin_device', '设备管理', 2, '/modules/m05/device.html', 'twin:device:view', 3),
(14, 'twin_screen', '大屏中心', 2, '/modules/screen/index.html', 'twin:screen:view', 4);

INSERT INTO shared_region (region_code, region_name, parent_code) VALUES 
('CN', '中国', NULL),
('CN_BJ', '北京市', 'CN'),
('CN_SH', '上海市', 'CN'),
('CN_GD', '广东省', 'CN'),
('CN_GZ', '广州市', 'CN_GD'),
('CN_SZ', '深圳市', 'CN_GD');

INSERT INTO shared_station (station_code, station_name, region_code, longitude, latitude) VALUES
('ST001', '广州天河基站', 'CN_GZ', 113.33, 23.13),
('ST002', '深圳南山基站', 'CN_SZ', 113.92, 22.54),
('ST003', '北京朝阳基站', 'CN_BJ', 116.47, 39.90);

-- 角色-菜单关联（admin拥有所有菜单）
INSERT INTO m01_role_menu (role_id, menu_id)
SELECT r.id, m.id FROM m01_role r, m01_menu m WHERE r.role_code = 'admin';

-- 分配用户角色
INSERT INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r
WHERE u.username = 'admin' AND r.role_code = 'admin';

INSERT INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r
WHERE u.username = 'operator' AND r.role_code = 'operator';

INSERT INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r
WHERE u.username = 'designer' AND r.role_code = 'designer';

INSERT INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r
WHERE u.username = 'planner' AND r.role_code = 'planner';

-- M03 区域初始数据
INSERT INTO m03_region (region_code, region_name, parent_code, center_coord) VALUES
('CN', '中国', NULL, '104.0,35.0'),
('CN_BJ', '北京市', 'CN', '116.47,39.90'),
('CN_GD', '广东省', 'CN', '113.27,23.13'),
('CN_GZ', '广州市', 'CN_GD', '113.33,23.13'),
('CN_SZ', '深圳市', 'CN_GD', '113.92,22.54');

-- M04 示例项目
INSERT INTO m04_project (project_name, project_code, region_code, current_phase, phase_progress, total_progress, start_date, planned_end_date, construction_unit, design_unit, supervision_unit, owner_unit) VALUES
('广州天河5G基站建设项目', 'PRJ-2026-001', 'CN_GZ', 'CONSTRUCTION', 65.00, 45.00, '2026-03-01', '2026-08-30', '中通建工有限公司', '华信设计院', '公诚监理', '广东移动'),
('深圳南山机房改造工程', 'PRJ-2026-002', 'CN_SZ', 'DESIGN', 90.00, 25.00, '2026-04-15', '2026-10-15', '深圳电信工程', '南方设计院', '深圳监理', '深圳电信'),
('北京朝阳管线敷设项目', 'PRJ-2026-003', 'CN_BJ', 'ACCEPTANCE', 95.00, 85.00, '2026-02-10', '2026-06-30', '北京工程局', '北京设计院', '北京监理', '北京移动');

-- M05 示例设备
INSERT INTO m05_device (device_code, device_name, device_type, station_code, install_time, status, manufacturer, model) VALUES
('BTS-1024', '华为AAU5313', 'AAU', 'ST001', '2026-03-15', 1, '华为', 'AAU5313'),
('BTS-1025', '中兴RRU-A100', 'RRU', 'ST001', '2026-03-15', 1, '中兴', 'RRU-A100'),
('BTS-2048', '华为BBU5900', 'BBU', 'ST002', '2026-04-20', 1, '华为', 'BBU5900'),
('BTS-2049', '爱立信RDS-6601', 'RRU', 'ST002', '2026-04-20', 2, '爱立信', 'RDS-6601'),
('BTS-3072', '华为AAU5333', 'AAU', 'ST003', '2026-02-28', 0, '华为', 'AAU5333');

-- M05 示例告警
INSERT INTO m05_alert (device_id, device_code, alert_content, level, status, source) VALUES
(1, 'BTS-1024', 'AAU温度超过75°C阈值', 1, 0, 'MQTT'),
(4, 'BTS-2049', 'RRU驻波比异常', 2, 1, 'MQTT'),
(5, 'BTS-3072', 'AAU光模块接收功率过低', 1, 2, 'MQTT');

-- M04 示例工单
INSERT INTO m04_work_order (order_no, title, type, priority, status, station_code, device_code, description) VALUES
('WO20260520001', '基站高温告警处理', 'ALERT', 1, 1, 'ST001', 'BTS-1024', '机柜温度超过阈值，需现场检查空调运行状态'),
('WO20260521002', 'RRU驻波比异常排查', 'ALERT', 2, 0, 'ST002', 'BTS-2049', '驻波比超过1.5，需检查天线馈线连接'),
('WO20260522003', '季度安全巡检', 'INSPECTION', 3, 0, 'ST003', NULL, '2026年Q2安全巡检，重点检查防雷接地和临时用电');
