-- M02 CAD Fusion 数据库表结构
-- 多源异构数据融合服务

-- CAD文件表
CREATE TABLE IF NOT EXISTS m02_cad_file (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    file_name VARCHAR(200) NOT NULL COMMENT '存储文件名',
    original_name VARCHAR(500) NOT NULL COMMENT '原始文件名',
    file_path VARCHAR(1000) NOT NULL COMMENT '文件存储路径',
    file_type VARCHAR(20) NOT NULL COMMENT '文件类型(dwg/dxf)',
    file_size BIGINT COMMENT '文件大小(字节)',
    project_id BIGINT COMMENT '关联项目ID',
    uploaded_by BIGINT COMMENT '上传用户ID',
    source_epsg VARCHAR(50) DEFAULT 'EPSG:4326' COMMENT '源坐标系',
    target_epsg VARCHAR(50) DEFAULT 'EPSG:4326' COMMENT '目标坐标系',
    parse_status TINYINT DEFAULT 0 COMMENT '解析状态: 0待解析 1已解析 2解析失败',
    parse_result VARCHAR(1000) COMMENT '解析结果信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_project_id (project_id),
    INDEX idx_uploaded_by (uploaded_by),
    INDEX idx_parse_status (parse_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CAD文件表';

-- 坐标系配置表
CREATE TABLE IF NOT EXISTS m02_coordinate_system (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    epsg_code VARCHAR(20) NOT NULL COMMENT 'EPSG编码',
    name VARCHAR(100) NOT NULL COMMENT '坐标系名称',
    type VARCHAR(50) COMMENT '坐标系类型(GEOGRAPHIC/PROJECTED)',
    projection VARCHAR(200) COMMENT '投影方式',
    datum VARCHAR(100) COMMENT '大地基准',
    parameters TEXT COMMENT '投影参数JSON',
    is_preset TINYINT DEFAULT 0 COMMENT '是否预置',
    description VARCHAR(500) COMMENT '描述说明',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_epsg_code (epsg_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='坐标系配置表';

-- 融合任务表
CREATE TABLE IF NOT EXISTS m02_fusion_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_name VARCHAR(200) NOT NULL COMMENT '任务名称',
    project_id BIGINT COMMENT '关联项目ID',
    source_file_id BIGINT NOT NULL COMMENT '源CAD文件ID',
    source_epsg VARCHAR(50) DEFAULT 'EPSG:4326' COMMENT '源坐标系',
    target_epsg VARCHAR(50) DEFAULT 'EPSG:4326' COMMENT '目标坐标系',
    transformation_type VARCHAR(50) DEFAULT 'AUTO' COMMENT '转换类型',
    status TINYINT DEFAULT 0 COMMENT '状态: 0待处理 1融合中 2已完成 3失败',
    result_file_path VARCHAR(1000) COMMENT '结果文件路径',
    feature_count INT DEFAULT 0 COMMENT '生成要素数量',
    error_message VARCHAR(1000) COMMENT '错误信息',
    created_by BIGINT COMMENT '创建用户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_project_id (project_id),
    INDEX idx_source_file_id (source_file_id),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='融合任务表';

-- GIS要素表
CREATE TABLE IF NOT EXISTS m02_gis_feature (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    fusion_task_id BIGINT NOT NULL COMMENT '融合任务ID',
    feature_id VARCHAR(100) COMMENT '要素ID',
    feature_type VARCHAR(50) COMMENT '要素类型(building/road/pipeline等)',
    geometry_type VARCHAR(50) COMMENT '几何类型(Point/LineString/Polygon)',
    coordinate_x DECIMAL(12, 8) COMMENT 'X坐标(经度)',
    coordinate_y DECIMAL(12, 8) COMMENT 'Y坐标(纬度)',
    coordinate_z DECIMAL(12, 8) DEFAULT 0 COMMENT 'Z坐标(高度)',
    properties_json TEXT COMMENT '属性JSON',
    source_layer VARCHAR(100) COMMENT '源图层名',
    target_layer VARCHAR(100) COMMENT '目标图层名',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_fusion_task_id (fusion_task_id),
    INDEX idx_feature_type (feature_type),
    INDEX idx_geometry_type (geometry_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GIS要素表';

-- 初始化预置坐标系数据
INSERT INTO m02_coordinate_system (epsg_code, name, type, projection, datum, is_preset, description) VALUES
('EPSG:4326', 'WGS 84', 'GEOGRAPHIC', NULL, 'WGS_1984', 1, '全球定位系统标准坐标系，GPS默认使用'),
('EPSG:4490', 'CGCS2000', 'GEOGRAPHIC', NULL, 'CGCS2000', 1, '中国大地坐标系2000，国家法定坐标系'),
('EPSG:4214', 'Beijing 1954', 'GEOGRAPHIC', NULL, 'Beijing_1954', 1, '北京1954坐标系，早期测绘使用'),
('EPSG:4610', 'Xi''an 1980', 'GEOGRAPHIC', NULL, 'Xian_1980', 1, '西安1980坐标系，中国常用坐标系'),
('EPSG:3857', 'Web Mercator', 'PROJECTED', 'Mercator_1SP', 'WGS_1984', 1, 'Web地图投影坐标系，Google Maps/Bing Maps使用'),
('EPSG:4547', 'CGCS2000 / 3-degree GK zone 39°N', 'PROJECTED', 'Gauss-Krüger', 'CGCS2000', 1, 'CGCS2000三度带投影，常用工程坐标系'),
('EPSG:4549', 'CGCS2000 / 3-degree GK zone 41°N', 'PROJECTED', 'Gauss-Krüger', 'CGCS2000', 1, 'CGCS2000三度带投影，武汉市所在带');
