-- ====================================================
-- 通信基建数智化平台 - MySQL数据库初始化脚本
-- 使用说明：mysql -u root -p < scripts/init-mysql.sql
-- 包含：M01认证 + M02规划 + M03设计 + M04交付 + M05运维 + 8个虚拟基站测试数据
-- ====================================================

CREATE DATABASE IF NOT EXISTS comm_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE comm_platform;

-- ==================== M01 认证相关表 ====================
CREATE TABLE IF NOT EXISTS m01_user (
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

CREATE TABLE IF NOT EXISTS m01_role (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_code VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS m01_user_role (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS m01_menu (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    parent_id BIGINT DEFAULT 0,
    menu_code VARCHAR(50) NOT NULL UNIQUE,
    menu_name VARCHAR(100) NOT NULL,
    menu_type TINYINT DEFAULT 1 COMMENT '1:目录 2:菜单 3:按钮',
    iframe_url VARCHAR(255),
    permission_code VARCHAR(100),
    sort_order INT DEFAULT 0,
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS m01_role_menu (
    role_id BIGINT NOT NULL,
    menu_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, menu_id)
);

CREATE TABLE IF NOT EXISTS m01_operation_log (
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
CREATE TABLE IF NOT EXISTS shared_region (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL UNIQUE,
    region_name VARCHAR(100) NOT NULL,
    parent_code VARCHAR(50),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shared_station (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    station_code VARCHAR(50) NOT NULL UNIQUE,
    station_name VARCHAR(200),
    region_code VARCHAR(50),
    longitude DECIMAL(12,8),
    latitude DECIMAL(12,8),
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== M02 数通网络规划与仿真 ====================
CREATE TABLE IF NOT EXISTS m02_plan (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(200),
    plan_desc VARCHAR(500),
    region_code VARCHAR(50),
    status TINYINT DEFAULT 0 COMMENT '0:草稿 1:已发布',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS m02_station_plan (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_id BIGINT,
    station_code VARCHAR(50),
    longitude DECIMAL(12,8),
    latitude DECIMAL(12,8),
    height DECIMAL(5,2),
    antenna_count INT DEFAULT 1,
    azimuth VARCHAR(100),
    downtilt VARCHAR(100),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS m02_simulation_result (
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
CREATE TABLE IF NOT EXISTS m03_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(200) NOT NULL,
    project_code VARCHAR(50) NOT NULL UNIQUE,
    region_code VARCHAR(50),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' COMMENT 'active/archived',
    creator_id BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BIM-GIS项目表';

CREATE TABLE IF NOT EXISTS m03_device (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_code VARCHAR(100) NOT NULL UNIQUE,
    device_name VARCHAR(200),
    device_type VARCHAR(50) COMMENT 'station/antenna/rru',
    station_code VARCHAR(100),
    longitude DOUBLE,
    latitude DOUBLE,
    height DOUBLE COMMENT '安装高度(米)',
    status VARCHAR(20) DEFAULT 'active' COMMENT 'active/inactive/maintenance',
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    installation_time DATETIME,
    remark TEXT,
    project_id BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备表';

CREATE TABLE IF NOT EXISTS m03_region (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL UNIQUE,
    region_name VARCHAR(100) NOT NULL,
    parent_code VARCHAR(50),
    bounds TEXT COMMENT '边界坐标JSON',
    center_coord VARCHAR(100) COMMENT '中心点坐标',
    level INT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='区域表';

CREATE TABLE IF NOT EXISTS m03_model (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(200) NOT NULL,
    model_code VARCHAR(50) NOT NULL UNIQUE,
    model_type VARCHAR(50) COMMENT 'glb/gltf/3dtiles',
    file_path VARCHAR(500),
    file_size BIGINT,
    thumbnail_path VARCHAR(500),
    scale DOUBLE DEFAULT 1.0,
    description TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='3D模型表';

CREATE TABLE IF NOT EXISTS m03_design_scheme (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL COMMENT '项目ID',
    scheme_name VARCHAR(200) COMMENT '方案名称',
    frequency_band VARCHAR(50) COMMENT '频段',
    tower_height DECIMAL(10,2) COMMENT '塔高(米)',
    grid_size VARCHAR(50) COMMENT '网格大小',
    total_sites INT COMMENT '总站点数',
    valid_sites INT COMMENT '有效站点数',
    invalid_sites INT COMMENT '无效站点数',
    avg_rsrp DECIMAL(10,2) COMMENT '平均RSRP(dBm)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设计方案表';

CREATE TABLE IF NOT EXISTS m03_site (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_id BIGINT NOT NULL COMMENT '方案ID',
    site_id VARCHAR(50) COMMENT '站点ID',
    site_name VARCHAR(200) COMMENT '站点名称',
    longitude DECIMAL(12,8) COMMENT '经度',
    latitude DECIMAL(12,8) COMMENT '纬度',
    tower_height DECIMAL(10,2) COMMENT '塔高(米)',
    site_type VARCHAR(50) COMMENT '站点类型',
    scenario VARCHAR(50) COMMENT '场景',
    rsrp DECIMAL(10,2) COMMENT 'RSRP(dBm)',
    is_valid TINYINT DEFAULT 1 COMMENT '是否有效(0:无效,1:有效)',
    invalid_reason VARCHAR(500) COMMENT '无效原因',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点数据表';

CREATE TABLE IF NOT EXISTS m03_collision_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT,
    device_id1 BIGINT,
    device_id2 BIGINT,
    distance DECIMAL(10,4) COMMENT '距离(米)',
    level TINYINT COMMENT '1:安全 2:警告 3:碰撞',
    description VARCHAR(500),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== M04 数智化交付与工作流 ====================
CREATE TABLE IF NOT EXISTS m04_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_name VARCHAR(200) NOT NULL COMMENT '项目名称',
    project_code VARCHAR(50) NOT NULL UNIQUE COMMENT '项目编号',
    region_code VARCHAR(50) COMMENT '区域编码',
    current_phase VARCHAR(50) DEFAULT 'PLANNING' COMMENT 'PLANNING/DESIGN/CONSTRUCTION/ACCEPTANCE/OPS',
    phase_progress DECIMAL(5,2) DEFAULT 0 COMMENT '阶段进度',
    total_progress DECIMAL(5,2) DEFAULT 0 COMMENT '总进度',
    start_date DATE COMMENT '开工日期',
    planned_end_date DATE COMMENT '计划完工日期',
    actual_end_date DATE COMMENT '实际完工日期',
    construction_unit VARCHAR(200) COMMENT '施工单位',
    design_unit VARCHAR(200) COMMENT '设计单位',
    supervision_unit VARCHAR(200) COMMENT '监理单位',
    owner_unit VARCHAR(200) COMMENT '建设单位',
    status INT DEFAULT 1 COMMENT '0:暂停 1:进行中 2:已完成',
    creator_id BIGINT COMMENT '创建人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目信息表';

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

CREATE TABLE IF NOT EXISTS m04_inspection_record (
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

CREATE TABLE IF NOT EXISTS m04_delivery_package (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    package_name VARCHAR(200) COMMENT '交付包名称',
    package_type VARCHAR(50) COMMENT '交付包类型',
    status INT DEFAULT 0 COMMENT '0-待打包 1-已打包 2-已归档',
    file_count INT DEFAULT 0 COMMENT '文件数量',
    total_size BIGINT DEFAULT 0 COMMENT '总大小(字节)',
    minio_path VARCHAR(500) COMMENT 'MinIO存储路径',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交付包表';

CREATE TABLE IF NOT EXISTS m04_delivery_file (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    package_id BIGINT NOT NULL COMMENT '交付包ID',
    file_name VARCHAR(200) COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
    file_type VARCHAR(50) COMMENT '文件类型',
    md5 VARCHAR(32) COMMENT '文件MD5',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交付文件明细表';

CREATE TABLE IF NOT EXISTS m04_acceptance_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    task_name VARCHAR(200) COMMENT '验收任务名称',
    task_type VARCHAR(50) COMMENT '任务类型',
    status INT DEFAULT 0 COMMENT '0-待验收 1-验收中 2-已通过 3-未通过',
    acceptance_standard TEXT COMMENT '验收标准',
    result_description TEXT COMMENT '验收结果描述',
    problem_count INT DEFAULT 0 COMMENT '问题数量',
    acceptance_by BIGINT COMMENT '验收人ID',
    acceptance_time DATETIME COMMENT '验收时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验收任务表';

CREATE TABLE IF NOT EXISTS m04_acceptance_problem (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_id BIGINT NOT NULL COMMENT '验收任务ID',
    problem_title VARCHAR(200) COMMENT '问题标题',
    problem_level INT DEFAULT 1 COMMENT '问题级别 1-一般 2-严重 3-重大',
    problem_description TEXT COMMENT '问题描述',
    photo_path VARCHAR(500) COMMENT '问题照片路径',
    status INT DEFAULT 0 COMMENT '0-待整改 1-整改中 2-已整改 3-已复查',
    rectify_deadline DATE COMMENT '整改截止日期',
    rectify_result TEXT COMMENT '整改结果',
    rectify_by BIGINT COMMENT '整改人ID',
    review_by BIGINT COMMENT '复查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验收问题表';

-- ==================== M04 安全监管模块 ====================
CREATE TABLE IF NOT EXISTS m04_cert_verification (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
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
    verify_result INT DEFAULT 0 COMMENT '0-待审核 1-通过 2-不通过',
    verify_comment VARCHAR(500),
    verify_by BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资质验证表';

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
    check_result INT DEFAULT 0 COMMENT '0-不合格 1-合格',
    check_by BIGINT COMMENT '检查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='安全检查表';

CREATE TABLE IF NOT EXISTS m04_construction_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    responsible_person VARCHAR(100) COMMENT '负责人',
    work_date DATE COMMENT '施工日期',
    work_content TEXT COMMENT '施工内容',
    construction_units VARCHAR(500) COMMENT '施工班组',
    environment_assessment INT DEFAULT 0 COMMENT '0-有隐患 1-无隐患',
    hazard_description TEXT COMMENT '危险源描述',
    video_path VARCHAR(500) COMMENT '视频路径',
    photo_panorama VARCHAR(500) COMMENT '全景照片路径',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='施工记录表';

CREATE TABLE IF NOT EXISTS m04_barrier_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    check_date DATE COMMENT '检查日期',
    barrier_integrity INT DEFAULT 0 COMMENT '围挡完整性 0-完整 1-破损',
    sign_list TEXT COMMENT '标识清单JSON',
    night_light_status INT DEFAULT 0 COMMENT '夜间照明状态 0-正常 1-异常',
    road_photo VARCHAR(500) COMMENT '道路照片路径',
    environment_risk VARCHAR(500) COMMENT '环境风险',
    check_conclusion INT DEFAULT 0 COMMENT '0-不合格 1-合格',
    check_by BIGINT COMMENT '检查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='围挡检查表';

CREATE TABLE IF NOT EXISTS m04_electricity_check (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_id BIGINT NOT NULL COMMENT '项目ID',
    check_date DATE COMMENT '检查日期',
    distribution_box_no VARCHAR(50) COMMENT '配电箱编号',
    circuit_count INT DEFAULT 0 COMMENT '回路数量',
    leakage_protector_model VARCHAR(100) COMMENT '漏电保护器型号',
    leakage_protector_count INT DEFAULT 0 COMMENT '漏电保护器数量',
    one_machine_one_switch INT DEFAULT 0 COMMENT '一机一闸一漏一箱 0-不合格 1-合格',
    cable_status VARCHAR(200) COMMENT '电缆状态',
    ground_resistance DECIMAL(10,2) COMMENT '接地电阻值(Ω)',
    box_surrounding VARCHAR(200) COMMENT '箱体周边环境',
    photo_path VARCHAR(500) COMMENT '照片路径',
    check_conclusion INT DEFAULT 0 COMMENT '0-不合格 1-合格',
    check_by BIGINT COMMENT '检查人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用电检查表';

-- ==================== M05 数字孪生与智慧运维 ====================
CREATE TABLE IF NOT EXISTS m05_device (
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

CREATE TABLE IF NOT EXISTS m05_alert (
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

CREATE TABLE IF NOT EXISTS m05_maintenance_plan (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(200),
    device_code VARCHAR(100),
    plan_type VARCHAR(50) COMMENT 'daily/weekly/monthly/yearly',
    next_exec_time DATETIME,
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS m05_inspection_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(200),
    station_code VARCHAR(50),
    route_json TEXT,
    assignee_id BIGINT,
    status TINYINT DEFAULT 0 COMMENT '0:待执行 1:执行中 2:已完成',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    execute_time DATETIME
);

-- ==================== 索引 ====================
CREATE INDEX IF NOT EXISTS idx_m01_username ON m01_user(username);
CREATE INDEX IF NOT EXISTS idx_m01_user_status ON m01_user(status);
CREATE INDEX IF NOT EXISTS idx_shared_station_region ON shared_station(region_code);

CREATE INDEX IF NOT EXISTS idx_m03_device_project_id ON m03_device(project_id);
CREATE INDEX IF NOT EXISTS idx_m03_device_station_code ON m03_device(station_code);
CREATE INDEX IF NOT EXISTS idx_m03_device_type ON m03_device(device_type);
CREATE INDEX IF NOT EXISTS idx_m03_model_type ON m03_model(model_type);
CREATE INDEX IF NOT EXISTS idx_m03_region_parent ON m03_region(parent_code);
CREATE INDEX IF NOT EXISTS idx_m03_design_scheme_project ON m03_design_scheme(project_id);
CREATE INDEX IF NOT EXISTS idx_m03_site_scheme ON m03_site(scheme_id);
CREATE INDEX IF NOT EXISTS idx_m03_collision_project ON m03_collision_record(project_id);

CREATE INDEX IF NOT EXISTS idx_m04_project_code ON m04_project(project_code);
CREATE INDEX IF NOT EXISTS idx_m04_project_region ON m04_project(region_code);
CREATE INDEX IF NOT EXISTS idx_m04_work_order_status ON m04_work_order(status);
CREATE INDEX IF NOT EXISTS idx_m04_work_order_type ON m04_work_order(type);
CREATE INDEX IF NOT EXISTS idx_m04_safety_check_project ON m04_safety_check(project_id);
CREATE INDEX IF NOT EXISTS idx_m04_cert_project ON m04_cert_verification(project_id);
CREATE INDEX IF NOT EXISTS idx_m04_construction_project ON m04_construction_record(project_id);
CREATE INDEX IF NOT EXISTS idx_m04_barrier_project ON m04_barrier_check(project_id);
CREATE INDEX IF NOT EXISTS idx_m04_electricity_project ON m04_electricity_check(project_id);
CREATE INDEX IF NOT EXISTS idx_m04_delivery_package_project ON m04_delivery_package(project_id);
CREATE INDEX IF NOT EXISTS idx_m04_delivery_file_package ON m04_delivery_file(package_id);
CREATE INDEX IF NOT EXISTS idx_m04_acceptance_task_project ON m04_acceptance_task(project_id);
CREATE INDEX IF NOT EXISTS idx_m04_acceptance_problem_task ON m04_acceptance_problem(task_id);

CREATE INDEX IF NOT EXISTS idx_m05_device_station ON m05_device(station_code);
CREATE INDEX IF NOT EXISTS idx_m05_device_status ON m05_device(status);
CREATE INDEX IF NOT EXISTS idx_m05_alert_status ON m05_alert(status);
CREATE INDEX IF NOT EXISTS idx_m05_alert_level ON m05_alert(level);
CREATE INDEX IF NOT EXISTS idx_m05_alert_device ON m05_alert(device_code);

-- ==================== 初始化数据 ====================

-- M01 用户（密码 BCrypt 加密后的 admin123）
INSERT IGNORE INTO m01_user (username, password, real_name, email, status) VALUES 
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '超级管理员', 'admin@example.com', 1),
('operator', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '运维人员', 'operator@example.com', 1),
('designer', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '设计人员', 'designer@example.com', 1),
('planner', '$2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq', '规划人员', 'planner@example.com', 1);

INSERT IGNORE INTO m01_role (role_code, role_name, description) VALUES 
('admin', '超级管理员', '系统超级管理员'),
('operator', '运维人员', '日常运维操作人员'),
('designer', '设计人员', 'BIM设计人员'),
('planner', '规划人员', '网络规划人员');

INSERT IGNORE INTO m01_menu (parent_id, menu_code, menu_name, menu_type, iframe_url, permission_code, sort_order) VALUES 
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

INSERT IGNORE INTO m01_role_menu (role_id, menu_id)
SELECT r.id, m.id FROM m01_role r, m01_menu m WHERE r.role_code = 'admin';

INSERT IGNORE INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r WHERE u.username = 'admin' AND r.role_code = 'admin';
INSERT IGNORE INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r WHERE u.username = 'operator' AND r.role_code = 'operator';
INSERT IGNORE INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r WHERE u.username = 'designer' AND r.role_code = 'designer';
INSERT IGNORE INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u, m01_role r WHERE u.username = 'planner' AND r.role_code = 'planner';

-- 共享区域
INSERT IGNORE INTO shared_region (region_code, region_name, parent_code) VALUES 
('CN', '中国', NULL),
('CN_BJ', '北京市', 'CN'),
('CN_SH', '上海市', 'CN'),
('CN_GD', '广东省', 'CN'),
('CN_GZ', '广州市', 'CN_GD'),
('CN_SZ', '深圳市', 'CN_GD'),
('CN_HZ', '杭州市', 'CN'),
('CN_CD', '成都市', 'CN'),
('CN_XA', '西安市', 'CN'),
('CN_DL', '大连市', 'CN');

-- ==================== 8个虚拟基站样例（覆盖不同场景） ====================
INSERT IGNORE INTO shared_station (station_code, station_name, region_code, longitude, latitude) VALUES
('ST001', '广州天河CBD基站', 'CN_GZ', 113.3386, 23.1238),
('ST002', '深圳南山科技园基站', 'CN_SZ', 113.9358, 22.5354),
('ST003', '北京中关村核心基站', 'CN_BJ', 116.3035, 39.9987),
('ST004', '杭州西湖风景区基站', 'CN_HZ', 120.1546, 30.2741),
('ST005', '成都天府新区基站', 'CN_CD', 104.0535, 30.5728),
('ST006', '西安大唐不夜城基站', 'CN_XA', 108.9543, 34.2247),
('ST007', '上海陆家嘴金融中心基站', 'CN_SH', 121.5168, 31.2397),
('ST008', '大连星海广场基站', 'CN_DL', 121.5852, 38.9149);

-- M03 区域初始数据
INSERT IGNORE INTO m03_region (region_code, region_name, parent_code, bounds, center_coord, level) VALUES 
('CN', '中国', NULL, '[[73.0,18.0],[135.0,54.0]]', '104.0,35.0', 1),
('CN_BJ', '北京市', 'CN', '[[116.0,39.6],[116.8,40.2]]', '116.4,39.9', 2),
('CN_GD', '广东省', 'CN', '[[110.5,20.9],[117.0,25.5]]', '113.7,23.2', 2),
('CN_GZ', '广州市', 'CN_GD', '[[112.93,22.82],[113.65,23.57]]', '113.29,23.19', 3),
('CN_SZ', '深圳市', 'CN_GD', '[[113.72,22.45],[114.48,22.88]]', '114.10,22.66', 3),
('CN_HZ', '杭州市', 'CN', '[[119.4,29.8],[120.8,30.5]]', '120.1,30.2', 3),
('CN_CD', '成都市', 'CN', '[[103.3,30.0],[104.7,31.0]]', '104.0,30.5', 3),
('CN_XA', '西安市', 'CN', '[[108.5,33.7],[109.2,34.5]]', '108.9,34.2', 3),
('CN_SH', '上海市', 'CN', '[[121.0,30.8],[121.8,31.5]]', '121.4,31.2', 3),
('CN_DL', '大连市', 'CN', '[[121.1,38.5],[121.9,39.3]]', '121.5,38.9', 3);

-- M03 模型数据
INSERT IGNORE INTO m03_model (model_name, model_code, model_type, description) VALUES 
('基站模型-A', 'BS-A001', '基站', '标准基站三维模型'),
('天线模型-A', 'ANT-A001', '天线', '标准天线三维模型'),
('电源柜模型', 'PWR-001', '电源', '标准电源柜三维模型'),
('建筑物模型', 'BLD-001', '建筑物', '通用建筑物模型'),
('AAU模型', 'AAU-001', 'AAU', '5G AAU设备模型'),
('BBU模型', 'BBU-001', 'BBU', 'BBU基带单元模型'),
('RRU模型', 'RRU-001', 'RRU', 'RRU射频单元模型');

-- ==================== M04 项目（关联8个基站） ====================
INSERT IGNORE INTO m04_project (project_name, project_code, region_code, current_phase, phase_progress, total_progress, start_date, planned_end_date, construction_unit, design_unit, supervision_unit, owner_unit, status) VALUES
('广州天河5G覆盖提升项目', 'PRJ-2026-001', 'CN_GZ', 'CONSTRUCTION', 65.00, 45.00, '2026-03-01', '2026-08-30', '中通建工有限公司', '华信设计院', '公诚监理', '广东移动', 1),
('深圳南山科技园扩容工程', 'PRJ-2026-002', 'CN_SZ', 'DESIGN', 90.00, 25.00, '2026-04-15', '2026-10-15', '深圳电信工程', '南方设计院', '深圳监理', '深圳电信', 1),
('北京中关村核心区优化项目', 'PRJ-2026-003', 'CN_BJ', 'ACCEPTANCE', 95.00, 85.00, '2026-02-10', '2026-06-30', '北京工程局', '北京设计院', '北京监理', '北京移动', 1),
('杭州西湖景区5G覆盖项目', 'PRJ-2026-004', 'CN_HZ', 'CONSTRUCTION', 40.00, 30.00, '2026-05-01', '2026-11-30', '浙江建工集团', '浙江设计院', '浙江监理', '浙江移动', 1),
('成都天府新区新基建项目', 'PRJ-2026-005', 'CN_CD', 'PLANNING', 20.00, 10.00, '2026-06-15', '2027-03-15', '四川建工集团', '四川设计院', '四川监理', '四川移动', 1),
('西安文旅5G智慧项目', 'PRJ-2026-006', 'CN_XA', 'DESIGN', 70.00, 20.00, '2026-04-01', '2026-12-01', '陕西建工集团', '西北设计院', '陕西监理', '陕西移动', 1),
('上海陆家嘴金融区5G专网', 'PRJ-2026-007', 'CN_SH', 'CONSTRUCTION', 80.00, 55.00, '2026-02-20', '2026-09-20', '上海建工集团', '华东设计院', '上海监理', '上海电信', 1),
('大连沿海经济带通信项目', 'PRJ-2026-008', 'CN_DL', 'PLANNING', 15.00, 8.00, '2026-07-01', '2027-02-28', '辽宁建工集团', '东北设计院', '辽宁监理', '辽宁移动', 1);

-- ==================== M03 设计方案 + 站点（关联8个基站） ====================
INSERT IGNORE INTO m03_design_scheme (project_id, scheme_name, frequency_band, tower_height, grid_size, total_sites, valid_sites, invalid_sites, avg_rsrp) VALUES
(1, '天河CBD 5G覆盖方案', '3.5GHz', 35.00, '50m', 12, 10, 2, -85.50),
(2, '南山科技园优化方案', '2.6GHz', 28.00, '40m', 8, 8, 0, -78.30),
(3, '中关村核心区补盲方案', '3.5GHz', 42.00, '60m', 6, 5, 1, -82.10),
(4, '西湖景区景观融合方案', '3.5GHz', 20.00, '80m', 15, 13, 2, -88.70),
(5, '天府新区规划方案', '4.9GHz', 50.00, '100m', 20, 18, 2, -86.20),
(6, '大唐不夜城智慧方案', '3.5GHz', 25.00, '50m', 10, 9, 1, -81.40),
(7, '陆家嘴金融专网方案', '2.6GHz', 45.00, '30m', 16, 15, 1, -75.80),
(8, '大连沿海覆盖方案', '2.1GHz', 38.00, '120m', 18, 16, 2, -89.30);

INSERT IGNORE INTO m03_site (scheme_id, site_id, site_name, longitude, latitude, tower_height, site_type, scenario, rsrp, is_valid, invalid_reason) VALUES
(1, 'GZ-TH-001', '天河城基站', 113.3286, 23.1268, 35.00, 'macro', 'urban', -78.50, 1, NULL),
(1, 'GZ-TH-002', '珠江新城基站', 113.3395, 23.1189, 40.00, 'macro', 'urban', -75.30, 1, NULL),
(2, 'SZ-NS-001', '科技园南区基站', 113.9245, 22.5345, 28.00, 'macro', 'industrial', -72.80, 1, NULL),
(2, 'SZ-NS-002', '深大北门基站', 113.9387, 22.5467, 32.00, 'macro', 'campus', -76.20, 1, NULL),
(3, 'BJ-ZG-001', '中关村软件园基站', 116.2954, 40.0056, 42.00, 'macro', 'commercial', -79.40, 1, NULL),
(3, 'BJ-ZG-002', '海淀黄庄基站', 116.3123, 39.9923, 38.00, 'macro', 'urban', -85.60, 0, '周边高楼遮挡'),
(4, 'HZ-XH-001', '断桥残雪基站', 120.1423, 30.2786, 18.00, 'micro', 'scenic', -86.70, 1, NULL),
(4, 'HZ-XH-002', '雷峰塔基站', 120.1587, 30.2567, 22.00, 'micro', 'scenic', -89.20, 1, NULL),
(5, 'CD-TF-001', '天府广场基站', 104.0635, 30.5712, 50.00, 'macro', 'urban', -83.50, 1, NULL),
(5, 'CD-TF-002', '高新区基站', 104.0423, 30.5687, 45.00, 'macro', 'industrial', -87.20, 1, NULL),
(6, 'XA-DT-001', '大雁塔基站', 108.9567, 34.2156, 25.00, 'micro', 'cultural', -79.80, 1, NULL),
(6, 'XA-DT-002', '大唐芙蓉园基站', 108.9423, 34.2289, 28.00, 'micro', 'cultural', -82.30, 1, NULL),
(7, 'SH-LJ-001', '东方明珠基站', 121.5234, 31.2456, 45.00, 'macro', 'commercial', -72.50, 1, NULL),
(7, 'SH-LJ-002', '陆家嘴中心基站', 121.5189, 31.2345, 50.00, 'macro', 'commercial', -74.60, 1, NULL),
(8, 'DL-XH-001', '星海广场基站', 121.5876, 38.9123, 38.00, 'macro', 'coastal', -86.70, 1, NULL),
(8, 'DL-XH-002', '东港商务区基站', 121.6034, 38.9256, 42.00, 'macro', 'coastal', -88.90, 0, '海面反射干扰');

-- ==================== M03 设备（关联8个基站） ====================
INSERT IGNORE INTO m03_device (device_code, device_name, device_type, station_code, longitude, latitude, height, status, manufacturer, model) VALUES
('DEV-GZ-001', '天河城AAU', 'AAU', 'ST001', 113.3286, 23.1268, 35.00, 'active', '华为', 'AAU5313'),
('DEV-GZ-002', '天河城BBU', 'BBU', 'ST001', 113.3286, 23.1268, 1.50, 'active', '华为', 'BBU5900'),
('DEV-GZ-003', '珠江新城AAU', 'AAU', 'ST001', 113.3395, 23.1189, 40.00, 'active', '中兴', 'AAU5313'),
('DEV-SZ-001', '科技园AAU', 'AAU', 'ST002', 113.9245, 22.5345, 28.00, 'active', '华为', 'AAU5639'),
('DEV-SZ-002', '科技园BBU', 'BBU', 'ST002', 113.9245, 22.5345, 1.80, 'active', '华为', 'BBU3910'),
('DEV-BJ-001', '中关村AAU', 'AAU', 'ST003', 116.2954, 40.0056, 42.00, 'active', '爱立信', 'RDS-6601'),
('DEV-BJ-002', '中关村RRU', 'RRU', 'ST003', 116.2954, 40.0056, 40.00, 'maintenance', '爱立信', 'RRU6601'),
('DEV-HZ-001', '西湖AAU', 'AAU', 'ST004', 120.1423, 30.2786, 18.00, 'active', '华为', 'AAU5333'),
('DEV-HZ-002', '西湖BBU', 'BBU', 'ST004', 120.1423, 30.2786, 1.20, 'active', '华为', 'BBU5900'),
('DEV-CD-001', '天府AAU', 'AAU', 'ST005', 104.0635, 30.5712, 50.00, 'active', '大唐', 'DTAAU-1'),
('DEV-CD-002', '天府BBU', 'BBU', 'ST005', 104.0635, 30.5712, 2.00, 'active', '大唐', 'DTBBU-1'),
('DEV-XA-001', '大雁塔AAU', 'AAU', 'ST006', 108.9567, 34.2156, 25.00, 'active', '华为', 'AAU5313'),
('DEV-XA-002', '大雁塔BBU', 'BBU', 'ST006', 108.9567, 34.2156, 1.50, 'active', '华为', 'BBU5900'),
('DEV-SH-001', '陆家嘴AAU', 'AAU', 'ST007', 121.5234, 31.2456, 45.00, 'active', '中兴', 'AAU5639'),
('DEV-SH-002', '陆家嘴BBU', 'BBU', 'ST007', 121.5234, 31.2456, 1.80, 'active', '中兴', 'ZXBTS-B1'),
('DEV-DL-001', '大连AAU', 'AAU', 'ST008', 121.5876, 38.9123, 38.00, 'active', '华为', 'AAU5313'),
('DEV-DL-002', '大连BBU', 'BBU', 'ST008', 121.5876, 38.9123, 1.50, 'inactive', '华为', 'BBU5900');

-- ==================== M05 设备（关联8个基站） ====================
INSERT IGNORE INTO m05_device (device_code, device_name, device_type, station_code, install_time, status, manufacturer, model) VALUES
('BTS-GZ-001', '天河城AAU5313', 'AAU', 'ST001', '2026-03-15', 1, '华为', 'AAU5313'),
('BTS-GZ-002', '天河城BBU5900', 'BBU', 'ST001', '2026-03-15', 1, '华为', 'BBU5900'),
('BTS-GZ-003', '天河城RRU5301', 'RRU', 'ST001', '2026-03-15', 1, '华为', 'RRU5301'),
('BTS-SZ-001', '科技园AAU5639', 'AAU', 'ST002', '2026-04-20', 1, '华为', 'AAU5639'),
('BTS-SZ-002', '科技园BBU3910', 'BBU', 'ST002', '2026-04-20', 2, '华为', 'BBU3910'),
('BTS-SZ-003', '科技园RRU5301', 'RRU', 'ST002', '2026-04-20', 1, '华为', 'RRU5301'),
('BTS-BJ-001', '中关村AAU6601', 'AAU', 'ST003', '2026-02-28', 1, '爱立信', 'RDS-6601'),
('BTS-BJ-002', '中关村BBU6601', 'BBU', 'ST003', '2026-02-28', 1, '爱立信', 'BBU6601'),
('BTS-BJ-003', '中关村RRU6601', 'RRU', 'ST003', '2026-02-28', 1, '爱立信', 'RRU6601'),
('BTS-HZ-001', '西湖AAU5333', 'AAU', 'ST004', '2026-05-10', 1, '华为', 'AAU5333'),
('BTS-HZ-002', '西湖BBU5900', 'BBU', 'ST004', '2026-05-10', 1, '华为', 'BBU5900'),
('BTS-CD-001', '天府AAU-DT1', 'AAU', 'ST005', '2026-06-01', 0, '大唐', 'DTAAU-1'),
('BTS-CD-002', '天府BBU-DT1', 'BBU', 'ST005', '2026-06-01', 0, '大唐', 'DTBBU-1'),
('BTS-XA-001', '大雁塔AAU5313', 'AAU', 'ST006', '2026-04-15', 1, '华为', 'AAU5313'),
('BTS-XA-002', '大雁塔BBU5900', 'BBU', 'ST006', '2026-04-15', 1, '华为', 'BBU5900'),
('BTS-SH-001', '陆家嘴AAU5639', 'AAU', 'ST007', '2026-03-01', 1, '中兴', 'AAU5639'),
('BTS-SH-002', '陆家嘴BBU-ZXB1', 'BBU', 'ST007', '2026-03-01', 1, '中兴', 'ZXBTS-B1'),
('BTS-DL-001', '大连AAU5313', 'AAU', 'ST008', '2026-06-10', 1, '华为', 'AAU5313'),
('BTS-DL-002', '大连BBU5900', 'BBU', 'ST008', '2026-06-10', 1, '华为', 'BBU5900');

-- ==================== M05 告警（关联设备） ====================
INSERT IGNORE INTO m05_alert (device_id, device_code, alert_content, level, status, source) VALUES
(1, 'BTS-GZ-001', 'AAU温度超过75°C阈值', 1, 0, 'MQTT'),
(5, 'BTS-SZ-002', 'BBU风扇故障告警', 2, 1, 'MQTT'),
(12, 'BTS-CD-001', '设备离线告警', 1, 0, 'MQTT'),
(13, 'BTS-CD-002', '设备离线告警', 1, 0, 'MQTT'),
(3, 'BTS-GZ-003', 'RRU驻波比异常', 2, 2, 'MQTT'),
(7, 'BTS-BJ-001', '光模块接收功率偏低', 3, 0, 'MQTT'),
(15, 'BTS-XA-001', 'AAU上行干扰', 3, 1, 'MQTT'),
(17, 'BTS-SH-001', '设备运行正常提醒', 4, 2, 'MQTT');

-- ==================== M04 工单（关联基站和设备） ====================
INSERT IGNORE INTO m04_work_order (order_no, title, type, priority, status, station_code, device_code, description) VALUES
('WO20260520001', '天河城基站高温告警处理', 'ALERT', 1, 1, 'ST001', 'BTS-GZ-001', '机柜温度超过阈值，需现场检查空调运行状态'),
('WO20260521002', '科技园BBU风扇故障排查', 'ALERT', 2, 0, 'ST002', 'BTS-SZ-002', 'BBU风扇转速异常，需更换风扇模块'),
('WO20260522003', '中关村光功率检测', 'INSPECTION', 3, 0, 'ST003', 'BTS-BJ-001', '光模块接收功率低于-28dBm，需检查光纤链路'),
('WO20260523004', '天府新区设备调试', 'MAINTENANCE', 2, 0, 'ST005', 'BTS-CD-001', '新设备上线，需进行远程配置和测试'),
('WO20260524005', '大雁塔上行干扰排查', 'ALERT', 2, 1, 'ST006', 'BTS-XA-001', '检测到上行干扰信号，需进行频谱分析'),
('WO20260525006', '陆家嘴季度巡检', 'INSPECTION', 3, 2, 'ST007', 'BTS-SH-001', 'Q2安全巡检，重点检查防雷接地和设备状态'),
('WO20260526007', '大连基站开通验收', 'ACCEPTANCE', 2, 0, 'ST008', 'BTS-DL-001', '新基站开通后验收，检查设备运行状态'),
('WO20260527008', '西湖景区设备维护', 'MAINTENANCE', 3, 0, 'ST004', 'BTS-HZ-001', '定期维护，清洁设备灰尘，检查天线方向');

-- ==================== M04 安全监管测试数据 ====================
INSERT IGNORE INTO m04_safety_check (project_id, check_date, equipment_type, brand_model, production_date, valid_date, quantity, appearance_status, photo_path, check_result, check_by) VALUES
(1, '2026-05-20', 'HELMET', '3M-X500', '2025-03-15', '2027-03-15', 10, 'GOOD', 'safety/PRJ-2026-001/helmet-001.jpg', 1, 1),
(1, '2026-05-20', 'BELT', '恒丰-HF-5000', '2025-06-20', '2027-06-20', 8, 'GOOD', 'safety/PRJ-2026-001/belt-001.jpg', 1, 1),
(2, '2026-05-21', 'HELMET', '代尔塔-V900', '2024-12-01', '2026-11-30', 12, 'EXPIRED', 'safety/PRJ-2026-002/helmet-002.jpg', 0, 1),
(3, '2026-05-22', 'INSULATED_GLOVES', '双安-SA-200', '2025-08-10', '2027-08-10', 6, 'GOOD', 'safety/PRJ-2026-003/gloves-001.jpg', 1, 1);

INSERT IGNORE INTO m04_cert_verification (project_id, person_name, id_card, cert_type, cert_number, issuing_authority, valid_from, valid_to, verify_result) VALUES
(1, '张三', '110101199001011234', '登高证', 'DG2023001234', '北京市应急管理局', '2023-06-01', '2025-05-31', 2),
(1, '李四', '110102199203155678', '电工证', 'DG2024005678', '北京市应急管理局', '2024-01-10', '2027-01-09', 1),
(2, '王五', '440301198807209012', '安全员证', 'AQ2023009012', '深圳市应急管理局', '2023-09-15', '2026-09-14', 1),
(3, '赵六', '110103199511053456', '焊工证', 'HG2024003456', '北京市应急管理局', '2024-03-01', '2027-02-28', 0);

INSERT IGNORE INTO m04_barrier_check (project_id, check_date, barrier_integrity, sign_list, night_light_status, road_photo, check_conclusion, check_by) VALUES
(1, '2026-05-20', 1, '[\"施工警示\",\"禁止入内\",\"注意安全\"]', 1, 'barrier/PRJ-2026-001/road-001.jpg', 1, 1),
(2, '2026-05-21', 0, '[\"施工警示\"]', 1, 'barrier/PRJ-2026-002/road-002.jpg', 0, 1),
(3, '2026-05-22', 1, '[\"施工警示\",\"禁止入内\",\"注意安全\",\"限速5\"]', 0, 'barrier/PRJ-2026-003/road-003.jpg', 0, 1);

INSERT IGNORE INTO m04_electricity_check (project_id, check_date, distribution_box_no, circuit_count, leakage_protector_count, one_machine_one_switch, cable_status, ground_resistance, box_surrounding, check_conclusion, check_by) VALUES
(1, '2026-05-20', 'DX-001', 6, 6, 1, 'GOOD', 4.50, 'CLEAR', 1, 1),
(2, '2026-05-21', 'DX-002', 4, 3, 0, 'DAMAGED', 8.20, 'OBSTRUCTED', 0, 1),
(3, '2026-05-22', 'DX-003', 8, 8, 1, 'GOOD', 3.80, 'CLEAR', 1, 1);

INSERT IGNORE INTO m04_construction_record (project_id, responsible_person, work_date, work_content, environment_assessment, hazard_description) VALUES
(1, '张工', '2026-05-20', '完成天河城基站AAU安装调试，信号覆盖测试通过', 1, NULL),
(2, '李工', '2026-05-21', '科技园基站BBU更换，风扇模块故障已修复', 1, NULL),
(3, '王工', '2026-05-22', '中关村基站光功率检测，发现链路衰减需整改', 0, '光纤链路衰减超过15dB，需重新熔接');

-- ==================== M02 规划方案（关联8个基站） ====================
INSERT IGNORE INTO m02_plan (plan_name, plan_desc, region_code, status) VALUES
('广州天河5G覆盖规划', '天河CBD区域5G信号覆盖优化规划方案，提升楼宇深度覆盖', 'CN_GZ', 1),
('深圳南山科技园扩容规划', '南山科技园区域5G容量扩容规划，满足企业园区高带宽需求', 'CN_SZ', 1),
('北京中关村核心区补盲规划', '中关村核心区信号盲区补盲规划，改善室内覆盖质量', 'CN_BJ', 1),
('杭州西湖景区5G规划', '西湖景区5G信号覆盖规划，兼顾景观保护与通信需求', 'CN_HZ', 1),
('成都天府新区新基建规划', '天府新区5G新基建规划，支撑数字城市建设', 'CN_CD', 0),
('西安文旅智慧通信规划', '西安文旅景区智慧通信规划，提升游客体验', 'CN_XA', 0),
('上海陆家嘴金融专网规划', '陆家嘴金融区5G专网规划，保障金融业务低时延需求', 'CN_SH', 1),
('大连沿海经济带覆盖规划', '大连沿海经济带5G覆盖规划，服务港口与工业园区', 'CN_DL', 0);

INSERT IGNORE INTO m02_station_plan (plan_id, station_code, longitude, latitude, height, antenna_count, azimuth, downtilt) VALUES
(1, 'ST001', 113.3286, 23.1268, 35.00, 3, '0,120,240', '3,3,3'),
(1, 'GZ-TH-002', 113.3395, 23.1189, 40.00, 3, '30,150,270', '4,4,4'),
(1, 'GZ-TH-003', 113.3456, 23.1324, 32.00, 3, '60,180,300', '3,3,3'),
(2, 'ST002', 113.9245, 22.5345, 28.00, 3, '0,120,240', '3,3,3'),
(2, 'SZ-NS-002', 113.9387, 22.5467, 32.00, 3, '45,165,285', '4,4,4'),
(3, 'ST003', 116.2954, 40.0056, 42.00, 3, '0,120,240', '2,2,2'),
(3, 'BJ-ZG-002', 116.3123, 39.9923, 38.00, 3, '30,150,270', '3,3,3'),
(4, 'ST004', 120.1423, 30.2786, 18.00, 2, '0,180', '5,5'),
(4, 'HZ-XH-002', 120.1587, 30.2567, 22.00, 2, '90,270', '4,4'),
(5, 'ST005', 104.0635, 30.5712, 50.00, 3, '0,120,240', '2,2,2'),
(5, 'CD-TF-002', 104.0423, 30.5687, 45.00, 3, '60,180,300', '3,3,3'),
(6, 'ST006', 108.9567, 34.2156, 25.00, 2, '0,180', '4,4'),
(6, 'XA-DT-002', 108.9423, 34.2289, 28.00, 2, '90,270', '5,5'),
(7, 'ST007', 121.5234, 31.2456, 45.00, 3, '0,120,240', '2,2,2'),
(7, 'SH-LJ-002', 121.5189, 31.2345, 50.00, 3, '45,165,285', '3,3,3'),
(8, 'ST008', 121.5876, 38.9123, 38.00, 3, '0,120,240', '3,3,3'),
(8, 'DL-XH-002', 121.6034, 38.9256, 42.00, 3, '60,180,300', '4,4,4');

INSERT IGNORE INTO m02_simulation_result (plan_id, station_code, rsrp_value, sinr_value, coverage_type, sim_time) VALUES
(1, 'ST001', -78.50, 22.30, 'excellent', '2026-05-15 10:00:00'),
(1, 'GZ-TH-002', -75.30, 25.10, 'excellent', '2026-05-15 10:00:00'),
(1, 'GZ-TH-003', -82.10, 18.50, 'good', '2026-05-15 10:00:00'),
(2, 'ST002', -72.80, 28.40, 'excellent', '2026-05-16 14:00:00'),
(2, 'SZ-NS-002', -76.20, 23.80, 'excellent', '2026-05-16 14:00:00'),
(3, 'ST003', -79.40, 21.60, 'excellent', '2026-05-17 09:00:00'),
(3, 'BJ-ZG-002', -85.60, 15.20, 'fair', '2026-05-17 09:00:00'),
(4, 'ST004', -86.70, 16.80, 'fair', '2026-05-18 11:00:00'),
(4, 'HZ-XH-002', -89.20, 13.50, 'fair', '2026-05-18 11:00:00'),
(5, 'ST005', -83.50, 19.20, 'good', '2026-05-19 15:00:00'),
(5, 'CD-TF-002', -87.20, 14.80, 'fair', '2026-05-19 15:00:00'),
(6, 'ST006', -79.80, 22.10, 'excellent', '2026-05-20 10:00:00'),
(6, 'XA-DT-002', -82.30, 18.90, 'good', '2026-05-20 10:00:00'),
(7, 'ST007', -72.50, 29.60, 'excellent', '2026-05-21 14:00:00'),
(7, 'SH-LJ-002', -74.60, 26.30, 'excellent', '2026-05-21 14:00:00'),
(8, 'ST008', -86.70, 16.20, 'fair', '2026-05-22 09:00:00'),
(8, 'DL-XH-002', -88.90, 13.80, 'fair', '2026-05-22 09:00:00');

-- ==================== M05 维护计划（关联8个基站设备） ====================
INSERT IGNORE INTO m05_maintenance_plan (plan_name, device_code, plan_type, next_exec_time, status) VALUES
('天河城AAU季度巡检', 'BTS-GZ-001', 'monthly', '2026-06-15 09:00:00', 1),
('天河城BBU月度检查', 'BTS-GZ-002', 'monthly', '2026-06-15 09:00:00', 1),
('科技园BBU故障维修', 'BTS-SZ-002', 'daily', '2026-05-28 10:00:00', 1),
('中关村光模块更换', 'BTS-BJ-001', 'weekly', '2026-05-30 09:00:00', 1),
('西湖设备年度保养', 'BTS-HZ-001', 'yearly', '2026-12-01 09:00:00', 1),
('天府新区设备开通', 'BTS-CD-001', 'daily', '2026-05-28 14:00:00', 1),
('大雁塔AAU季度校准', 'BTS-XA-001', 'monthly', '2026-06-15 09:00:00', 1),
('陆家嘴设备半年检测', 'BTS-SH-001', 'monthly', '2026-07-01 09:00:00', 1),
('大连设备季度巡检', 'BTS-DL-001', 'monthly', '2026-06-10 09:00:00', 1);

-- ==================== M05 巡检任务（关联8个基站） ====================
INSERT IGNORE INTO m05_inspection_task (task_name, station_code, route_json, assignee_id, status, execute_time) VALUES
('天河城基站日常巡检', 'ST001', '[{"lat":23.1268,"lng":113.3286},{"lat":23.1189,"lng":113.3395},{"lat":23.1324,"lng":113.3456}]', 2, 2, '2026-05-25 10:00:00'),
('科技园基站故障排查', 'ST002', '[{"lat":22.5345,"lng":113.9245},{"lat":22.5467,"lng":113.9387}]', 2, 1, '2026-05-28 09:00:00'),
('中关村基站专项检查', 'ST003', '[{"lat":40.0056,"lng":116.2954},{"lat":39.9923,"lng":116.3123}]', 2, 0, NULL),
('西湖景区基站巡检', 'ST004', '[{"lat":30.2786,"lng":120.1423},{"lat":30.2567,"lng":120.1587}]', 2, 2, '2026-05-26 14:00:00'),
('天府新区基站验收', 'ST005', '[{"lat":30.5712,"lng":104.0635},{"lat":30.5687,"lng":104.0423}]', 2, 1, '2026-05-28 14:00:00'),
('大雁塔基站例行巡检', 'ST006', '[{"lat":34.2156,"lng":108.9567},{"lat":34.2289,"lng":108.9423}]', 2, 0, NULL),
('陆家嘴金融区巡检', 'ST007', '[{"lat":31.2456,"lng":121.5234},{"lat":31.2345,"lng":121.5189}]', 2, 2, '2026-05-24 09:00:00'),
('大连沿海基站巡检', 'ST008', '[{"lat":38.9123,"lng":121.5876},{"lat":38.9256,"lng":121.6034}]', 2, 0, NULL);

-- ==================== M04 验收任务与问题（关联项目） ====================
INSERT IGNORE INTO m04_acceptance_task (project_id, task_name, task_type, status, acceptance_standard, problem_count, acceptance_by, acceptance_time) VALUES
(1, '天河城基站设备验收', 'DEVICE', 2, '1.设备安装牢固\n2.信号覆盖达标\n3.安全防护到位', 0, 1, '2026-05-20 16:00:00'),
(2, '科技园基站设计验收', 'DESIGN', 1, '1.设计方案符合规范\n2.覆盖仿真达标\n3.成本预算合理', 2, 1, NULL),
(3, '中关村基站工程验收', 'CONSTRUCTION', 2, '1.工程质量合格\n2.资料齐全\n3.试运行通过', 0, 1, '2026-05-22 17:00:00'),
(4, '西湖景区基站景观验收', 'LANDSCAPE', 1, '1.设备隐蔽性达标\n2.景观协调\n3.环境影响评估通过', 1, 1, NULL);

INSERT IGNORE INTO m04_acceptance_problem (task_id, problem_title, problem_level, problem_description, status, rectify_deadline, rectify_by) VALUES
(2, '部分区域RSRP未达标', 2, '科技园南区部分楼宇深度覆盖不足，RSRP低于-95dBm', 1, '2026-06-15', 3),
(2, '供电容量不足', 2, '部分站点供电容量不足以支持新增设备', 0, '2026-06-10', 3),
(4, '设备外观影响景观', 1, '雷峰塔附近设备外观颜色与环境不协调', 0, '2026-06-20', 3);

-- ==================== 创建数据库用户 ====================
CREATE USER IF NOT EXISTS 'appuser'@'localhost' IDENTIFIED WITH mysql_native_password BY 'apppass123';
CREATE USER IF NOT EXISTS 'appuser'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY 'apppass123';
GRANT SELECT, INSERT, UPDATE, DELETE ON comm_platform.* TO 'appuser'@'localhost', 'appuser'@'127.0.0.1';
FLUSH PRIVILEGES;

SELECT '========================================' AS message;
SELECT 'MySQL数据库初始化完成！' AS status;
SELECT '数据库: comm_platform' AS info;
SELECT '用户: appuser / apppass123' AS info2;
SELECT '8个虚拟基站已创建，覆盖广州/深圳/北京/杭州/成都/西安/上海/大连' AS info3;
SELECT '========================================' AS end;