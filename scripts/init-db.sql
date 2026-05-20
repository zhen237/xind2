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
CREATE TABLE m03_bim_model (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(200),
    file_path VARCHAR(500),
    file_size BIGINT,
    project_id BIGINT,
    station_code VARCHAR(50),
    model_type VARCHAR(50),
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m03_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(200),
    project_code VARCHAR(50) UNIQUE,
    region_code VARCHAR(50),
    status TINYINT DEFAULT 0 COMMENT '0:设计中 1:已交付',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE m03_collision_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT,
    model_id BIGINT,
    collision_type VARCHAR(50) COMMENT 'hard/soft',
    collision_desc VARCHAR(500),
    position_info VARCHAR(200),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

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

-- ==================== 初始化数据 ====================
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
