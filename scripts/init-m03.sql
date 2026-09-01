USE comm_platform;

-- ==================== M03 BIM+GIS 设计模块 ====================
-- 项目表
CREATE TABLE IF NOT EXISTS m03_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(200) NOT NULL,
    project_code VARCHAR(50) NOT NULL UNIQUE,
    region_code VARCHAR(50),
    description VARCHAR(500),
    status TINYINT DEFAULT 0 COMMENT '0:草稿 1:进行中 2:已完成',
    creator_id BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 设备表
CREATE TABLE IF NOT EXISTS m03_device (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_code VARCHAR(100) NOT NULL UNIQUE,
    device_name VARCHAR(200),
    device_type VARCHAR(50) COMMENT '基站/天线/电源',
    station_code VARCHAR(50),
    longitude DECIMAL(12,8),
    latitude DECIMAL(12,8),
    height DECIMAL(10,2) COMMENT '安装高度(米)',
    status VARCHAR(20) DEFAULT 'normal' COMMENT 'normal/abnormal/maintenance',
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    installation_time VARCHAR(50),
    remark VARCHAR(500),
    project_id BIGINT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 区域表
CREATE TABLE IF NOT EXISTS m03_region (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL UNIQUE,
    region_name VARCHAR(100) NOT NULL,
    parent_code VARCHAR(50),
    bounds TEXT COMMENT '边界坐标JSON',
    center_coord VARCHAR(100) COMMENT '中心点坐标',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 三维模型表
CREATE TABLE IF NOT EXISTS m03_model (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(200) NOT NULL,
    model_code VARCHAR(50) NOT NULL UNIQUE,
    model_type VARCHAR(50) COMMENT '基站/天线/建筑物',
    file_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    scale DECIMAL(10,4) DEFAULT 1.0,
    description VARCHAR(500),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 碰撞检测结果表
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

-- 初始化基础数据
INSERT IGNORE INTO m03_region (region_code, region_name, parent_code, bounds, center_coord) VALUES 
('CN_GZ', '广州市', 'CN', '[[112.93,22.82],[113.65,23.57]]', '113.23,23.19'),
('CN_SZ', '深圳市', 'CN', '[[113.72,22.45],[114.48,22.88]]', '114.05,22.66'),
('CN_BJ', '北京市', 'CN', '[[116.0,39.6],[116.8,40.2]]', '116.40,39.90');

INSERT IGNORE INTO m03_model (model_name, model_code, model_type, description) VALUES 
('基站模型-A', 'BS-A001', '基站', '标准基站三维模型'),
('天线模型-A', 'ANT-A001', '天线', '标准天线三维模型'),
('电源柜模型', 'PWR-001', '电源', '标准电源柜三维模型'),
('建筑物模型', 'BLD-001', '建筑物', '通用建筑物模型');