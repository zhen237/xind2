-- m03-bim-gis 数据库初始化脚本
-- 执行: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS comm_platform DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_general_ci;
USE comm_platform;

-- 项目表
CREATE TABLE IF NOT EXISTS m03_project (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  project_name VARCHAR(200) COMMENT '项目名称',
  project_code VARCHAR(100) COMMENT '项目编码',
  description TEXT COMMENT '项目描述',
  status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/archived',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BIM-GIS项目表';

-- 设备表
CREATE TABLE IF NOT EXISTS m03_device (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_code VARCHAR(100) COMMENT '设备编码',
  device_name VARCHAR(200) COMMENT '设备名称',
  device_type VARCHAR(50) COMMENT '设备类型: station/antenna/rru',
  station_code VARCHAR(100) COMMENT '所属基站编码',
  longitude DOUBLE COMMENT '经度',
  latitude DOUBLE COMMENT '纬度',
  height DOUBLE DEFAULT 0 COMMENT '高度(米)',
  status VARCHAR(20) DEFAULT 'normal' COMMENT '状态: normal/fault/offline',
  manufacturer VARCHAR(100) COMMENT '制造商',
  model VARCHAR(100) COMMENT '型号',
  installation_time VARCHAR(50) COMMENT '安装时间',
  remark TEXT COMMENT '备注',
  project_id BIGINT COMMENT '所属项目ID',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备表';

-- 3D模型表
CREATE TABLE IF NOT EXISTS m03_model (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  model_name VARCHAR(200) COMMENT '模型名称',
  model_type VARCHAR(50) COMMENT '模型类型: glb/gltf/3dtiles',
  file_path VARCHAR(500) COMMENT '文件路径',
  file_size BIGINT COMMENT '文件大小(字节)',
  description TEXT COMMENT '模型描述',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='3D模型表';

-- 区域表
CREATE TABLE IF NOT EXISTS m03_region (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  region_name VARCHAR(200) COMMENT '区域名称',
  region_code VARCHAR(100) COMMENT '区域编码',
  parent_code VARCHAR(100) COMMENT '父区域编码',
  level INT DEFAULT 1 COMMENT '层级',
  longitude DOUBLE COMMENT '中心经度',
  latitude DOUBLE COMMENT '中心纬度',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='区域表';

-- 插入示例数据
INSERT INTO m03_device (device_code, device_name, device_type, longitude, latitude, height, status, manufacturer) VALUES
('ST-001', '北京协和医院基站', 'station', 116.397428, 39.90923, 100, 'normal', '华为'),
('ST-002', '北京站基站', 'station', 116.427428, 39.90423, 80, 'normal', '中兴'),
('ST-003', '国家体育场基站', 'station', 116.397428, 39.94423, 120, 'normal', '华为'),
('ST-004', '北京大学基站', 'station', 116.317428, 39.98923, 60, 'normal', '爱立信'),
('ST-005', '首都国际机场基站', 'station', 116.587428, 40.07923, 150, 'normal', '华为'),
('ST-006', '北京友谊医院基站', 'station', 116.357428, 39.93923, 90, 'normal', '中兴'),
('ST-007', '北京南站基站', 'station', 116.387428, 39.86423, 110, 'normal', '华为'),
('ST-008', '清华大学基站', 'station', 116.327428, 39.99923, 75, 'normal', '爱立信');
