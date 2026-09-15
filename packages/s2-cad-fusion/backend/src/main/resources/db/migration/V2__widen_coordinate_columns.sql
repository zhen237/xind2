-- 修复：s2_gis_feature 坐标列宽度不足导致融合落库失败
-- 原 DECIMAL(12,8) 最大仅约 99999.99，无法容纳投影坐标（EPSG:3857 量级约 1.2e7）
-- 改为 DOUBLE，兼容任意坐标系（经纬度 / 米制投影）的坐标值
ALTER TABLE s2_gis_feature
    MODIFY COLUMN coordinate_x DOUBLE COMMENT 'X坐标(经度或投影X，要素中心点)',
    MODIFY COLUMN coordinate_y DOUBLE COMMENT 'Y坐标(纬度或投影Y，要素中心点)',
    MODIFY COLUMN coordinate_z DOUBLE DEFAULT 0 COMMENT 'Z坐标(高度)';
