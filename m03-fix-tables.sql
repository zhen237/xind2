-- M03 缺失表修复脚本（手动执行版）
-- 在服务器上执行： mysql -u root -p comm_platform < m03-fix-tables.sql

CREATE TABLE IF NOT EXISTS m03_parametric_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    devices_json JSON NOT NULL,
    topology_rule VARCHAR(50),
    coverage_type VARCHAR(30),
    default_params JSON,
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='参数化基站设计模板';

CREATE TABLE IF NOT EXISTS m03_design_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_no VARCHAR(50) NOT NULL UNIQUE,
    template_id BIGINT,
    project_id BIGINT,
    params_json JSON NOT NULL,
    result_json JSON,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_by VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='参数化设计任务';

CREATE TABLE IF NOT EXISTS m03_generated_layout (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    model_spec VARCHAR(100),
    longitude DOUBLE NOT NULL,
    latitude DOUBLE NOT NULL,
    altitude DOUBLE DEFAULT 0,
    azimuth DOUBLE DEFAULT 0,
    downtilt DOUBLE DEFAULT 0,
    mount_height DOUBLE,
    coverage_radius DOUBLE,
    parent_device VARCHAR(100),
    extra_params JSON,
    sort_order INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES m03_design_task(id)
) COMMENT='自动生成的设备布局明细';

CREATE INDEX idx_m03_template_category ON m03_parametric_template(category);
CREATE INDEX idx_m03_task_status ON m03_design_task(status);
CREATE INDEX idx_m03_task_project ON m03_design_task(project_id);
CREATE INDEX idx_m03_layout_task ON m03_generated_layout(task_id);

-- 初始化模板数据（先清后插，避免重复执行报错）
DELETE FROM m03_parametric_template;
INSERT INTO m03_parametric_template (name, category, description, devices_json, topology_rule, coverage_type, default_params) VALUES
('标准宏基站(三扇区)', 'macro', '适用于室外广域覆盖的宏蜂窝基站，标准三扇区配置', '{"devices":[{"type":"tower","name":"通信铁塔","model":"TOWER-35M","quantity":1,"position_rule":"center","height":35,"parent":null},{"type":"antenna","name":"扇区天线","model":"ANT-1710-2170-65-18i","quantity":3,"position_rule":"sector_top","offset_radius":1.5,"height":30,"downtilt":6,"beamwidth_h":65,"beamwidth_v":7,"gain":18,"parent":"tower"},{"type":"rru","name":"射频拉远单元","model":"RRU-3942","quantity":3,"position_rule":"below_antenna","offset_z":-2,"parent":"antenna"},{"type":"bbu","name":"基带处理单元","model":"BBU-5900","quantity":1,"position_rule":"cabinet_center","parent":null},{"type":"power","name":"电源柜","model":"PWR-48V-200A","quantity":1,"position_rule":"cabinet_west","offset_x":-3,"parent":null},{"type":"transmission","name":"传输柜","model":"TRANS-ODF-48","quantity":1,"position_rule":"cabinet_east","offset_x":5,"parent":null}]}', 'sector_120', 'outdoor', '{"antenna_height":30,"coverage_radius":500,"frequency":2100,"sector_count":3}'),
('微基站(单扇区)', 'micro', '适用于城区热点补盲或街道覆盖', '{"devices":[{"type":"antenna","name":"一体化天线","model":"ANT-3300-3800-65-15i","quantity":1,"position_rule":"center","height":6,"downtilt":4,"beamwidth_h":65,"gain":15},{"type":"rru","name":"RRU","model":"RRU-MICRO-5G","quantity":1,"position_rule":"below_antenna","offset_z":-1,"parent":"antenna"},{"type":"bbu","name":"BBU","model":"BBU-MICRO","quantity":1,"position_rule":"cabinet_center","parent":null}]}', 'single_point', 'outdoor', '{"antenna_height":6,"coverage_radius":200,"frequency":3500,"sector_count":1}'),
('室内分布系统(单层)', 'indoor', '适用于楼宇室内覆盖，单楼层', '{"devices":[{"type":"rru","name":"信源RRU","model":"RRU-INDOOR","quantity":1,"position_rule":"equipment_room","parent":null},{"type":"splitter","name":"功分器","model":"SPL-2WAY","quantity":2,"position_rule":"distributed_calc","calc_basis":"floor_area","parent":"rru"},{"type":"antenna","name":"室分天线","model":"ANT-CEILING-OMNI","quantity":8,"position_rule":"grid","spacing":15,"height":3.0,"gain":3,"parent":"splitter"}]}', 'grid', 'indoor', '{"floor_area":1000,"ceiling_height":3.5,"antenna_spacing":15,"frequency":2100}');

SELECT 'M03 表修复完成' AS result;
