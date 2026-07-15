-- V2: 添加机房位置字段（QGIS插件同步）
-- 用于存储 QGIS 插件确定的机房坐标，S1 门户据此绘制基站→机房管线

ALTER TABLE m03_design_scheme
  ADD COLUMN room_longitude DECIMAL(12, 8) COMMENT '机房经度(QGIS同步)' AFTER avg_rsrp,
  ADD COLUMN room_latitude DECIMAL(12, 8) COMMENT '机房纬度(QGIS同步)' AFTER room_longitude,
  ADD COLUMN room_name VARCHAR(100) COMMENT '机房名称' AFTER room_latitude,
  ADD COLUMN route_type VARCHAR(32) COMMENT '管线路由类型(direct=直线,manhattan=曼哈顿)' AFTER room_name;
