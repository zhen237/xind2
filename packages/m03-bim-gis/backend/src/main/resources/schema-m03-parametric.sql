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