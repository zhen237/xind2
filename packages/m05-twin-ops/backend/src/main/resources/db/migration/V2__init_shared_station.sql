-- =============================================================================
-- V2：shared_station 共享站点表 + 8 个演示站点
--
-- 背景（2026-09-15 生产读接口扫荡发现）：
--   m05 的两个接口用裸 SQL 显式 JOIN 了 shared_station，但该表只写在遗留脚本
--   scripts/init-mysql.sql 里，**从未进迁移链**，任何环境都没有它：
--     m05/ScreenInternalController.java:51
--       SELECT d.station_code, s.station_name, COUNT(*) FROM m05_device d
--       LEFT JOIN shared_station s ON d.station_code = s.station_code ...
--     m05/mapper/DeviceMapper.java:19
--       SELECT d.*, s.station_name FROM m05_device d
--       LEFT JOIN shared_station s ON d.station_code = s.station_code WHERE d.id = #{id}
--   结果：/api/m05/internal/screen/station-device-count 等接口 500。
--
-- 【表归属说明｜需留意】shared_ 前缀的表在语义上属"跨模块共享"，但本仓库没有任何
--   独立运行的 shared 应用进程（shared-backend 是被各模块依赖的库，不跑 Flyway），
--   所以必须挂在某个具体模块的迁移链上才建得出来。经扫描确认当前**唯一**的使用方是
--   m05（两条裸 SQL），故暂由 m05 承担建表职责；将来若有第二个模块要用，请把建表
--   迁移移到该模块之前的启动顺序上，或改为在启动脚本里前置执行，避免"谁先启动谁建表"
--   的隐式依赖。
--
-- 幂等性：CREATE TABLE IF NOT EXISTS + 索引并入建表 KEY；
--   种子用 INSERT IGNORE（station_code 有 UNIQUE 约束，是真幂等）。
-- =============================================================================

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS shared_station (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    station_code VARCHAR(50) NOT NULL COMMENT '站点编码',
    station_name VARCHAR(200) COMMENT '站点名称',
    region_code VARCHAR(50) COMMENT '所属区域编码',
    -- 注意：这里是经纬度（度），DECIMAL(12,8) 的 4 位整数位足够容纳 ±180。
    -- 不要复用给投影坐标（EPSG:3857 量级约 1.2e7，会溢出——s2 曾踩过这个坑，见 V2__widen_coordinate_columns.sql）。
    longitude DECIMAL(12,8) COMMENT '经度',
    latitude DECIMAL(12,8) COMMENT '纬度',
    status TINYINT DEFAULT 1 COMMENT '1:启用 0:停用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_shared_station_code (station_code),
    KEY idx_shared_station_region (region_code)
-- 【排序规则｜必须与 m05_device 一致，不可单边改】
--   本表与 m05_device / m05_alert 之间做的是**跨表等值 JOIN**
--   （LEFT JOIN ... ON d.station_code = s.station_code）。MySQL 的取值规则是：
--     · 建表写了 COLLATE  → 表就用写的那个；
--     · 只写 DEFAULT CHARSET=utf8mb4 → 取 **服务器变量 collation_server**
--       （不是库默认值；2026-09-15 在生产机与本地机用探针表实测确认）。
--   两边写法不一致就会抛 1267
--   "Illegal mix of collations (utf8mb4_0900_ai_ci) and (utf8mb4_unicode_ci)"。
--   实测本机 `collation_server` 与库默认**不同**（库 unicode_ci / 服务器 0900），
--   而生产机 `collation_server` = 0900 → 若这里写 unicode_ci，**生产与本地都会炸**。
--   → 这里显式钉死 `utf8mb4_unicode_ci`，并由紧随其后的 V3 把 m05_device /
--     m05_alert（原为无 COLLATE → 跟随 collation_server）一并 CONVERT 成同一个值，
--     使 m05 三张表在**任何机器**上都确定相等，不再依赖服务器变量。
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='共享站点表';

-- 8 个演示站点（与遗留脚本 scripts/init-mysql.sql 一致）
INSERT IGNORE INTO shared_station (station_code, station_name, region_code, longitude, latitude) VALUES
('ST001', '广州天河CBD基站',        'CN_GZ', 113.3386, 23.1238),
('ST002', '深圳南山科技园基站',      'CN_SZ', 113.9358, 22.5354),
('ST003', '北京中关村核心基站',      'CN_BJ', 116.3035, 39.9987),
('ST004', '杭州西湖风景区基站',      'CN_HZ', 120.1546, 30.2741),
('ST005', '成都天府新区基站',        'CN_CD', 104.0535, 30.5728),
('ST006', '西安大唐不夜城基站',      'CN_XA', 108.9543, 34.2247),
('ST007', '上海陆家嘴金融中心基站',  'CN_SH', 121.5168, 31.2397),
('ST008', '大连星海广场基站',        'CN_DL', 121.5852, 38.9149);
