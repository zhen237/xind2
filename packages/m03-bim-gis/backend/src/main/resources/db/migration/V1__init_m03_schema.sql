-- M03 BIM-GIS 模块 — 初始 schema
-- 创建日期: 2026-07-07
-- 最后修改: 2026-09-15（原因见文末「V1 修复记录」）
-- Flyway 命名规范: V{version}__{description}.sql
--
-- ============================================================================
-- ⚠️ 本文件必须保持【整份脚本完全幂等】——重复执行不得报错。三条硬约束：
--   ① 建表一律 CREATE TABLE IF NOT EXISTS；
--   ② 索引一律写进建表的 KEY 子句，禁止使用独立的 CREATE INDEX
--      —— 因为 MySQL 8 既不支持 `CREATE INDEX IF NOT EXISTS`（那是 MariaDB
--         语法，写上去直接语法报错），也不支持 `ALTER TABLE ... ADD COLUMN
--         IF NOT EXISTS`。历史上本文件在这两种写法之间反复横跳：
--         MariaDB 写法 → MySQL 语法报错；去掉 IF NOT EXISTS → 语法通了但
--         重跑必报 `Duplicate key name`。写进建表 KEY 子句是唯一同时满足
--         "MySQL 合法" + "可重复执行"的写法。
--   ③ 种子数据用 INSERT ... SELECT ... WHERE NOT EXISTS 逐条保护
--      （这些表上没有唯一键，不能靠 INSERT IGNORE 去重）。
--
-- 为什么必须幂等：Flyway 只在迁移**成功后**才写入历史表。若本脚本执行到一半
-- 失败（历史上就发生在建索引那一步），下次启动会从头重跑 V1；脚本幂等则重跑
-- 自愈，否则永久卡在 `Duplicate key name`。详见
-- docs/数据库迁移遗留问题-修复方案.md。
-- ============================================================================

-- 显式声明连接字符集。本脚本含中文字面量，且下面用 `WHERE NOT EXISTS (... = '中文')`
-- 做幂等保护；若通过默认字符集为 gbk 的 Windows 客户端手工执行，中文字面量会被
-- 当作 gbk，与 utf8mb4 列比较时直接失败：
--   ERROR 1267 (HY000): Illegal mix of collations
--   (utf8mb4_0900_ai_ci,IMPLICIT) and (gbk_chinese_ci,COERCIBLE) for operation '='
-- Flyway 走 JDBC 时连接本就是 utf8mb4，此行是幂等兜底，对人肉执行同样必要。
SET NAMES utf8mb4;

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
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_m03_device_project_id (project_id),
  KEY idx_m03_device_station_code (station_code),
  KEY idx_m03_device_type (device_type)
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
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_m03_model_type (model_type)
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
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_m03_region_parent (parent_code)
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
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_m03_design_scheme_project (project_id)
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
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_m03_site_scheme (scheme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点表';

-- 参数化基站设计模板
-- V5 会对本表执行 `ADD COLUMN idempotency_key ... AFTER updated_at`，
-- 因此 updated_at 必须始终是本表最后一个列，列名不可改。
CREATE TABLE IF NOT EXISTS m03_parametric_template (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL COMMENT '模板名称',
  category VARCHAR(50) NOT NULL COMMENT '模板分类: macro/micro/indoor',
  description TEXT COMMENT '模板说明',
  devices_json JSON NOT NULL COMMENT '设备清单(JSON)',
  topology_rule VARCHAR(50) COMMENT '组网规则: sector_120/single_point/grid',
  coverage_type VARCHAR(30) COMMENT '覆盖类型: outdoor/indoor',
  default_params JSON COMMENT '默认参数(JSON)',
  is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_m03_template_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='参数化基站设计模板';

-- 参数化设计任务
-- V5 会 `ADD COLUMN idempotency_key ... AFTER updated_at`、V7 会
-- `ADD COLUMN local_data_json ... AFTER result_json`，故 updated_at 必须在列尾、
-- result_json 必须存在，列名均不可改。
CREATE TABLE IF NOT EXISTS m03_design_task (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  task_no VARCHAR(50) NOT NULL UNIQUE COMMENT '任务编号',
  template_id BIGINT COMMENT '所用模板ID',
  project_id BIGINT COMMENT '所属项目ID',
  params_json JSON NOT NULL COMMENT '任务参数(JSON)',
  result_json JSON COMMENT '设计成果(JSON)',
  status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT '状态: draft/running/completed/failed',
  created_by VARCHAR(50) COMMENT '创建人',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_m03_task_status (status),
  KEY idx_m03_task_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='参数化设计任务';

-- 自动生成的设备布局明细
-- 必须在 m03_design_task 之后建：本表有指向它的外键。
CREATE TABLE IF NOT EXISTS m03_generated_layout (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  task_id BIGINT NOT NULL COMMENT '所属任务ID',
  device_name VARCHAR(100) NOT NULL COMMENT '设备名称',
  device_type VARCHAR(50) NOT NULL COMMENT '设备类型',
  model_spec VARCHAR(100) COMMENT '型号规格',
  longitude DOUBLE NOT NULL COMMENT '经度',
  latitude DOUBLE NOT NULL COMMENT '纬度',
  altitude DOUBLE DEFAULT 0 COMMENT '海拔(米)',
  azimuth DOUBLE DEFAULT 0 COMMENT '方位角(度)',
  downtilt DOUBLE DEFAULT 0 COMMENT '下倾角(度)',
  mount_height DOUBLE COMMENT '挂高(米)',
  coverage_radius DOUBLE COMMENT '覆盖半径(米)',
  parent_device VARCHAR(100) COMMENT '上级设备名称',
  extra_params JSON COMMENT '附加参数(JSON)',
  sort_order INT DEFAULT 0 COMMENT '排序',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_m03_layout_task (task_id),
  CONSTRAINT fk_m03_layout_task FOREIGN KEY (task_id) REFERENCES m03_design_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自动生成的设备布局明细';

-- ---------------------------------------------------------------------------
-- 种子数据（幂等）
-- 模板数据原先只存在于仓库根目录的手工脚本 m03-fix-tables.sql，且用
-- `DELETE FROM m03_parametric_template` + `INSERT` 实现（破坏性：重跑会连用户
-- 自建模板一起删掉）。现改为 WHERE NOT EXISTS 逐条保护，可安全重复执行。
-- ---------------------------------------------------------------------------
-- 示例设备数据：仅当表为空时灌入。
-- ⚠️ 不能用 `INSERT IGNORE`：m03_device 上没有唯一键（只有主键 + 3 个普通 KEY），
--    所以 IGNORE 不会去重，重跑一次就会再插 8 行。改为"表空才插"的守卫。
INSERT INTO m03_device (device_code, device_name, device_type, station_code, longitude, latitude, height, status, manufacturer, model)
SELECT * FROM (
  SELECT 'DEV-001' AS a, '基站A-天线1' AS b, 'antenna' AS c, 'STA-001' AS d, 116.397 AS e, 39.908 AS f, 30 AS g, 'active' AS h, '华为' AS i, 'AAU5639' AS j
  UNION ALL SELECT 'DEV-002', '基站A-天线2', 'antenna', 'STA-001', 116.397, 39.908, 30, 'active', '华为', 'AAU5639'
  UNION ALL SELECT 'DEV-003', '基站A-RRU', 'rru', 'STA-001', 116.397, 39.908, 25, 'active', '华为', 'RRU5301'
  UNION ALL SELECT 'DEV-004', '基站B-天线1', 'antenna', 'STA-002', 116.405, 39.915, 35, 'active', '中兴', 'AAU5313'
  UNION ALL SELECT 'DEV-005', '基站B-RRU', 'rru', 'STA-002', 116.405, 39.915, 30, 'active', '中兴', 'RRU5301'
  UNION ALL SELECT 'DEV-006', '基站C-天线1', 'antenna', 'STA-003', 116.412, 39.920, 40, 'active', '华为', 'AAU5313'
  UNION ALL SELECT 'DEV-007', '基站C-天线2', 'antenna', 'STA-003', 116.412, 39.920, 40, 'maintenance', '华为', 'AAU5313'
  UNION ALL SELECT 'DEV-008', '基站D-天线1', 'antenna', 'STA-004', 116.385, 39.900, 25, 'active', '大唐', 'RRU5301'
) AS t
WHERE NOT EXISTS (SELECT 1 FROM m03_device LIMIT 1);

INSERT INTO m03_parametric_template (name, category, description, devices_json, topology_rule, coverage_type, default_params)
SELECT * FROM (SELECT
  '标准宏基站(三扇区)' AS name,
  'macro' AS category,
  '适用于室外广域覆盖的宏蜂窝基站，标准三扇区配置' AS description,
  CAST('{"devices":[{"type":"tower","name":"通信铁塔","model":"TOWER-35M","quantity":1,"position_rule":"center","height":35,"parent":null},{"type":"antenna","name":"扇区天线","model":"ANT-1710-2170-65-18i","quantity":3,"position_rule":"sector_top","offset_radius":1.5,"height":30,"downtilt":6,"beamwidth_h":65,"beamwidth_v":7,"gain":18,"parent":"tower"},{"type":"rru","name":"射频拉远单元","model":"RRU-3942","quantity":3,"position_rule":"below_antenna","offset_z":-2,"parent":"antenna"},{"type":"bbu","name":"基带处理单元","model":"BBU-5900","quantity":1,"position_rule":"cabinet_center","parent":null},{"type":"power","name":"电源柜","model":"PWR-48V-200A","quantity":1,"position_rule":"cabinet_west","offset_x":-3,"parent":null},{"type":"transmission","name":"传输柜","model":"TRANS-ODF-48","quantity":1,"position_rule":"cabinet_east","offset_x":5,"parent":null}]}' AS JSON) AS devices_json,
  'sector_120' AS topology_rule,
  'outdoor' AS coverage_type,
  CAST('{"antenna_height":30,"coverage_radius":500,"frequency":2100,"sector_count":3}' AS JSON) AS default_params
) AS t WHERE NOT EXISTS (SELECT 1 FROM m03_parametric_template WHERE name = '标准宏基站(三扇区)');

INSERT INTO m03_parametric_template (name, category, description, devices_json, topology_rule, coverage_type, default_params)
SELECT * FROM (SELECT
  '微基站(单扇区)' AS name,
  'micro' AS category,
  '适用于城区热点补盲或街道覆盖' AS description,
  CAST('{"devices":[{"type":"antenna","name":"一体化天线","model":"ANT-3300-3800-65-15i","quantity":1,"position_rule":"center","height":6,"downtilt":4,"beamwidth_h":65,"gain":15},{"type":"rru","name":"RRU","model":"RRU-MICRO-5G","quantity":1,"position_rule":"below_antenna","offset_z":-1,"parent":"antenna"},{"type":"bbu","name":"BBU","model":"BBU-MICRO","quantity":1,"position_rule":"cabinet_center","parent":null}]}' AS JSON) AS devices_json,
  'single_point' AS topology_rule,
  'outdoor' AS coverage_type,
  CAST('{"antenna_height":6,"coverage_radius":200,"frequency":3500,"sector_count":1}' AS JSON) AS default_params
) AS t WHERE NOT EXISTS (SELECT 1 FROM m03_parametric_template WHERE name = '微基站(单扇区)');

INSERT INTO m03_parametric_template (name, category, description, devices_json, topology_rule, coverage_type, default_params)
SELECT * FROM (SELECT
  '室内分布系统(单层)' AS name,
  'indoor' AS category,
  '适用于楼宇室内覆盖，单楼层' AS description,
  CAST('{"devices":[{"type":"rru","name":"信源RRU","model":"RRU-INDOOR","quantity":1,"position_rule":"equipment_room","parent":null},{"type":"splitter","name":"功分器","model":"SPL-2WAY","quantity":2,"position_rule":"distributed_calc","calc_basis":"floor_area","parent":"rru"},{"type":"antenna","name":"室分天线","model":"ANT-CEILING-OMNI","quantity":8,"position_rule":"grid","spacing":15,"height":3.0,"gain":3,"parent":"splitter"}]}' AS JSON) AS devices_json,
  'grid' AS topology_rule,
  'indoor' AS coverage_type,
  CAST('{"floor_area":1000,"ceiling_height":3.5,"antenna_spacing":15,"frequency":2100}' AS JSON) AS default_params
) AS t WHERE NOT EXISTS (SELECT 1 FROM m03_parametric_template WHERE name = '室内分布系统(单层)');

-- ============================================================================
-- V1 修复记录（2026-09-15）
--
-- 【问题 1】三张表不在迁移链里
--   m03_design_task / m03_parametric_template / m03_generated_layout 原本只
--   存在于仓库根目录的手工脚本 m03-fix-tables.sql，从未进入 Flyway 迁移链；
--   但 V5 与 V7 却对 m03_design_task、m03_parametric_template 做 ALTER。
--   后果：全新库跑到 V5 必然报
--     Table 'comm_platform.m03_design_task' doesn't exist
--   修法：把三张表的建表语句补进 V1。版本号必须 < 5，否则来不及
--   （Flyway 严格按版本升序执行，补在 V8 也救不了 V5）。
--   注意：m03_design_task 建表时【不包含】idempotency_key（交由 V5 追加）
--   与 local_data_json（交由 V7 追加），以保持 "V1 建基表 → V5/V7 加列"
--   的既有语义不被破坏。
--
-- 【问题 2】V1 非幂等
--   原文末尾有 7 条独立的 `CREATE INDEX`（更早的版本写作
--   `CREATE INDEX IF NOT EXISTS`，那是 MariaDB 语法，在 MySQL 8 上直接
--   语法报错）。去掉 IF NOT EXISTS 后语法通了，但重跑必报
--     Duplicate key name 'idx_m03_device_project_id'
--   修法：7 条索引全部并入各自建表的 KEY 子句，并把 m03-fix-tables.sql 里
--   的 4 条索引一并并入，使整份脚本可重复执行且 MySQL 8 语法合法。
--
-- 【问题 3】种子数据破坏性
--   原 m03-fix-tables.sql 的模板种子用 `DELETE FROM` + `INSERT`，重跑会把
--   用户自建模板一起删掉。已改为 WHERE NOT EXISTS 幂等写法。
--
-- 验收方式见 docs/数据库迁移遗留问题-修复方案.md §4.2：
--   空库 DROP/CREATE → 启动 m03 → V1..V7 全绿 → 再执行一次 V1 不得报错。
-- ============================================================================
