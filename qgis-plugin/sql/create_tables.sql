-- M03 设计数据表
-- 创建时间：2026-06-05
-- 负责人：人A

-- 设计方案表
CREATE TABLE IF NOT EXISTS m03_design_scheme (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL COMMENT '项目ID',
    scheme_name VARCHAR(200) COMMENT '方案名称',
    frequency_band VARCHAR(50) COMMENT '频段',
    tower_height DECIMAL(8,2) COMMENT '塔高(米)',
    grid_size VARCHAR(20) COMMENT '网格大小',
    total_sites INT COMMENT '总站点数',
    valid_sites INT COMMENT '有效站点数',
    invalid_sites INT COMMENT '无效站点数',
    avg_rsrp DECIMAL(10,2) COMMENT '平均RSRP(dBm)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设计方案表';

-- 站点数据表
CREATE TABLE IF NOT EXISTS m03_site (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_id BIGINT NOT NULL COMMENT '方案ID',
    site_id VARCHAR(50) COMMENT '站点ID',
    site_name VARCHAR(100) COMMENT '站点名称',
    longitude DECIMAL(10,7) COMMENT '经度',
    latitude DECIMAL(10,7) COMMENT '纬度',
    tower_height DECIMAL(8,2) COMMENT '塔高(米)',
    site_type VARCHAR(50) COMMENT '站点类型',
    scenario VARCHAR(50) COMMENT '场景',
    rsrp DECIMAL(10,2) COMMENT 'RSRP(dBm)',
    is_valid TINYINT DEFAULT 1 COMMENT '是否有效(0:无效,1:有效)',
    invalid_reason VARCHAR(200) COMMENT '无效原因',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_scheme_id (scheme_id),
    INDEX idx_site_id (site_id),
    INDEX idx_project_id (scheme_id, site_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点数据表';
