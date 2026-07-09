-- M05 数字孪生运维模块 — 初始 schema
-- 创建日期: 2026-07-07

CREATE TABLE IF NOT EXISTS m05_device (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_code VARCHAR(100) COMMENT '设备编码',
    device_name VARCHAR(200) COMMENT '设备名称',
    device_type VARCHAR(50) COMMENT '设备类型',
    station_code VARCHAR(100) COMMENT '所属基站编码',
    install_time DATETIME COMMENT '安装时间',
    status INT DEFAULT 1 COMMENT '状态: 1-正常, 0-离线',
    manufacturer VARCHAR(100) COMMENT '厂商',
    model VARCHAR(100) COMMENT '型号',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运维设备表';

CREATE TABLE IF NOT EXISTS m05_alert (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT COMMENT '设备ID',
    device_code VARCHAR(100) COMMENT '设备编码',
    alert_content VARCHAR(500) COMMENT '告警内容',
    level INT DEFAULT 1 COMMENT '告警级别: 1-一般, 2-重要, 3-紧急',
    status INT DEFAULT 0 COMMENT '状态: 0-未处理, 1-已处理',
    source VARCHAR(50) COMMENT '告警来源: mqtt/manual/system',
    order_no VARCHAR(100) COMMENT '关联工单号',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_m05_alert_device (device_id),
    INDEX idx_m05_alert_status (status),
    INDEX idx_m05_alert_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警表';
