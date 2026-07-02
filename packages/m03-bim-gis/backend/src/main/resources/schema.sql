-- M03 BIM-GIS 模块数据库初始化脚本
-- 数据库: comm_platform

USE comm_platform;

-- 项目表
CREATE TABLE IF NOT EXISTS m03_project (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  project_name VARCHAR(200) COMMENT '项目名称',
  project_code VARCHAR(100) COMMENT '项目编码',
  region_code VARCHAR(100) COMMENT '区域编码',
  description TEXT COMMENT '项目描述',
  status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/archived',
  creator_id BIGINT COMMENT '创建者ID',
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
  height DOUBLE COMMENT '高度(米)',
  status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/inactive/maintenance',
  manufacturer VARCHAR(100) COMMENT '厂商',
  model VARCHAR(100) COMMENT '型号',
  installation_time DATETIME COMMENT '安装时间',
  remark TEXT COMMENT '备注',
  project_id BIGINT COMMENT '所属项目ID',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备表';

-- 3D模型表
CREATE TABLE IF NOT EXISTS m03_model (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  model_name VARCHAR(200) COMMENT '模型名称',
  model_code VARCHAR(100) COMMENT '模型编码',
  model_type VARCHAR(50) COMMENT '模型类型: glb/gltf/3dtiles',
  file_path VARCHAR(500) COMMENT '文件路径',
  file_size BIGINT COMMENT '文件大小(字节)',
  thumbnail_path VARCHAR(500) COMMENT '缩略图路径',
  scale DOUBLE DEFAULT 1.0 COMMENT '缩放比例',
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
  bounds TEXT COMMENT '边界坐标JSON',
  center_coord VARCHAR(200) COMMENT '中心坐标',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='区域表';

-- 设计方案表
CREATE TABLE IF NOT EXISTS m03_design_scheme (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  project_id BIGINT COMMENT '项目ID',
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

-- 站点表
CREATE TABLE IF NOT EXISTS m03_site (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  scheme_id BIGINT COMMENT '方案ID',
  site_id VARCHAR(100) COMMENT '站点ID',
  site_name VARCHAR(200) COMMENT '站点名称',
  longitude DECIMAL(12,6) COMMENT '经度',
  latitude DECIMAL(12,6) COMMENT '纬度',
  tower_height DECIMAL(10,2) COMMENT '塔高(米)',
  site_type VARCHAR(50) COMMENT '站点类型',
  scenario VARCHAR(50) COMMENT '场景',
  rsrp DECIMAL(10,2) COMMENT 'RSRP(dBm)',
  is_valid TINYINT DEFAULT 1 COMMENT '是否有效(0:无效,1:有效)',
  invalid_reason VARCHAR(500) COMMENT '无效原因',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点表';

-- 示例数据
INSERT INTO m03_device (device_code, device_name, device_type, station_code, longitude, latitude, height, status, manufacturer, model) VALUES
('DEV-001', '基站A-天线1', 'antenna', 'STA-001', 116.397, 39.908, 30, 'active', '华为', 'AAU5639'),
('DEV-002', '基站A-天线2', 'antenna', 'STA-001', 116.397, 39.908, 30, 'active', '华为', 'AAU5639'),
('DEV-003', '基站A-RRU', 'rru', 'STA-001', 116.397, 39.908, 25, 'active', '华为', 'RRU5301'),
('DEV-004', '基站B-天线1', 'antenna', 'STA-002', 116.405, 39.915, 35, 'active', '中兴', 'AAU5313'),
('DEV-005', '基站B-RRU', 'rru', 'STA-002', 116.405, 39.915, 30, 'active', '中兴', 'RRU5301'),
('DEV-006', '基站C-天线1', 'antenna', 'STA-003', 116.412, 39.920, 40, 'active', '华为', 'AAU5313'),
('DEV-007', '基站C-天线2', 'antenna', 'STA-003', 116.412, 39.920, 40, 'maintenance', '华为', 'AAU5313'),
('DEV-008', '基站D-天线1', 'antenna', 'STA-004', 116.385, 39.900, 25, 'active', '大唐', 'RRU5301');

-- 索引
CREATE INDEX idx_m03_device_project_id ON m03_device(project_id);
CREATE INDEX idx_m03_device_station_code ON m03_device(station_code);
CREATE INDEX idx_m03_device_type ON m03_device(device_type);
CREATE INDEX idx_m03_model_type ON m03_model(model_type);
CREATE INDEX idx_m03_region_parent ON m03_region(parent_code);
CREATE INDEX idx_m03_design_scheme_project ON m03_design_scheme(project_id);
CREATE INDEX idx_m03_site_scheme ON m03_site(scheme_id);
