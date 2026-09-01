CREATE TABLE IF NOT EXISTS `m04_project` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_name` VARCHAR(200) NOT NULL COMMENT '项目名称',
    `project_code` VARCHAR(50) NOT NULL UNIQUE COMMENT '项目编号',
    `region_code` VARCHAR(20) COMMENT '区域编码',
    `current_phase` VARCHAR(50) COMMENT '当前阶段',
    `phase_progress` DECIMAL(5,2) DEFAULT 0 COMMENT '阶段进度',
    `total_progress` DECIMAL(5,2) DEFAULT 0 COMMENT '总进度',
    `start_date` DATE COMMENT '开工日期',
    `planned_end_date` DATE COMMENT '计划完工日期',
    `actual_end_date` DATE COMMENT '实际完工日期',
    `construction_unit` VARCHAR(200) COMMENT '施工单位',
    `design_unit` VARCHAR(200) COMMENT '设计单位',
    `supervision_unit` VARCHAR(200) COMMENT '监理单位',
    `owner_unit` VARCHAR(200) COMMENT '建设单位',
    `status` INT DEFAULT 0 COMMENT '状态 0-在建 1-竣工 2-验收',
    `creator_id` BIGINT COMMENT '创建人ID',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目信息表';

CREATE TABLE IF NOT EXISTS `m04_work_order` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `order_no` VARCHAR(50) NOT NULL UNIQUE COMMENT '工单编号',
    `title` VARCHAR(200) NOT NULL COMMENT '工单标题',
    `type` VARCHAR(50) COMMENT '工单类型',
    `priority` INT DEFAULT 1 COMMENT '优先级 1-低 2-中 3-高',
    `status` INT DEFAULT 0 COMMENT '状态 0-待处理 1-处理中 2-已完成 3-已关闭',
    `station_code` VARCHAR(50) COMMENT '站点编码',
    `device_code` VARCHAR(50) COMMENT '设备编码',
    `assignee_id` BIGINT COMMENT '处理人ID',
    `creator_id` BIGINT COMMENT '创建人ID',
    `description` TEXT COMMENT '工单描述',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单表';

CREATE TABLE IF NOT EXISTS `m04_safety_check` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_id` BIGINT NOT NULL COMMENT '项目ID',
    `check_date` DATE COMMENT '检查日期',
    `equipment_type` VARCHAR(100) COMMENT '设备类型',
    `brand_model` VARCHAR(100) COMMENT '品牌型号',
    `production_date` DATE COMMENT '生产日期',
    `valid_date` DATE COMMENT '有效期至',
    `last_test_date` DATE COMMENT '上次检测日期',
    `test_report_no` VARCHAR(50) COMMENT '检测报告编号',
    `quantity` INT DEFAULT 0 COMMENT '数量',
    `appearance_status` VARCHAR(200) COMMENT '外观状态',
    `photo_path` VARCHAR(500) COMMENT '照片路径',
    `check_result` INT DEFAULT 0 COMMENT '检查结果 0-合格 1-不合格',
    `check_by` BIGINT COMMENT '检查人ID',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='安全检查表';

CREATE TABLE IF NOT EXISTS `m04_cert_verification` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_id` BIGINT NOT NULL COMMENT '项目ID',
    `person_name` VARCHAR(100) COMMENT '人员姓名',
    `id_card` VARCHAR(20) COMMENT '身份证号',
    `cert_type` VARCHAR(50) COMMENT '证件类型',
    `cert_number` VARCHAR(50) COMMENT '证件编号',
    `issuing_authority` VARCHAR(200) COMMENT '发证机关',
    `valid_from` DATE COMMENT '有效期起',
    `valid_to` DATE COMMENT '有效期至',
    `photo_distance` VARCHAR(500) COMMENT '远景照片路径',
    `photo_close` VARCHAR(500) COMMENT '近景照片路径',
    `video_path` VARCHAR(500) COMMENT '视频路径',
    `verify_result` INT DEFAULT 0 COMMENT '验证结果 0-通过 1-不通过',
    `verify_comment` TEXT COMMENT '验证备注',
    `verify_by` BIGINT COMMENT '验证人ID',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资质验证表';

CREATE TABLE IF NOT EXISTS `m04_construction_record` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_id` BIGINT NOT NULL COMMENT '项目ID',
    `responsible_person` VARCHAR(100) COMMENT '负责人',
    `work_date` DATE COMMENT '施工日期',
    `work_content` TEXT COMMENT '施工内容',
    `construction_units` VARCHAR(500) COMMENT '施工班组',
    `environment_assessment` INT DEFAULT 0 COMMENT '环境评估 0-正常 1-异常',
    `hazard_description` TEXT COMMENT '危险源描述',
    `video_path` VARCHAR(500) COMMENT '视频路径',
    `photo_panorama` VARCHAR(500) COMMENT '全景照片路径',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='施工记录表';

CREATE TABLE IF NOT EXISTS `m04_barrier_check` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_id` BIGINT NOT NULL COMMENT '项目ID',
    `check_date` DATE COMMENT '检查日期',
    `barrier_integrity` INT DEFAULT 0 COMMENT '围挡完整性 0-完整 1-破损',
    `sign_list` TEXT COMMENT '标识清单',
    `night_light_status` INT DEFAULT 0 COMMENT '夜间照明状态 0-正常 1-异常',
    `road_photo` VARCHAR(500) COMMENT '道路照片路径',
    `environment_risk` VARCHAR(500) COMMENT '环境风险',
    `check_conclusion` INT DEFAULT 0 COMMENT '检查结论 0-合格 1-不合格',
    `check_by` BIGINT COMMENT '检查人ID',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='围挡检查表';

CREATE TABLE IF NOT EXISTS `m04_electricity_check` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_id` BIGINT NOT NULL COMMENT '项目ID',
    `check_date` DATE COMMENT '检查日期',
    `distribution_box_no` VARCHAR(50) COMMENT '配电箱编号',
    `circuit_count` INT DEFAULT 0 COMMENT '回路数量',
    `leakage_protector_model` VARCHAR(100) COMMENT '漏电保护器型号',
    `leakage_protector_count` INT DEFAULT 0 COMMENT '漏电保护器数量',
    `one_machine_one_switch` INT DEFAULT 0 COMMENT '一机一闸 0-是 1-否',
    `cable_status` VARCHAR(200) COMMENT '电缆状态',
    `ground_resistance` DECIMAL(10,2) COMMENT '接地电阻值',
    `box_surrounding` VARCHAR(200) COMMENT '箱体周边环境',
    `photo_path` VARCHAR(500) COMMENT '照片路径',
    `check_conclusion` INT DEFAULT 0 COMMENT '检查结论 0-合格 1-不合格',
    `check_by` BIGINT COMMENT '检查人ID',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用电检查表';

CREATE TABLE IF NOT EXISTS `m04_delivery_package` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_id` BIGINT NOT NULL COMMENT '项目ID',
    `package_name` VARCHAR(200) COMMENT '交付包名称',
    `package_type` VARCHAR(50) COMMENT '交付包类型',
    `status` INT DEFAULT 0 COMMENT '状态 0-待打包 1-已打包 2-已归档',
    `file_count` INT DEFAULT 0 COMMENT '文件数量',
    `total_size` BIGINT DEFAULT 0 COMMENT '总大小(字节)',
    `minio_path` VARCHAR(500) COMMENT 'MinIO存储路径',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交付包表';

CREATE TABLE IF NOT EXISTS `m04_delivery_file` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `package_id` BIGINT NOT NULL COMMENT '交付包ID',
    `file_name` VARCHAR(200) COMMENT '文件名',
    `file_path` VARCHAR(500) COMMENT '文件路径',
    `file_size` BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
    `file_type` VARCHAR(50) COMMENT '文件类型',
    `md5` VARCHAR(32) COMMENT '文件MD5',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交付文件明细表';

CREATE TABLE IF NOT EXISTS `m04_acceptance_task` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `project_id` BIGINT NOT NULL COMMENT '项目ID',
    `task_name` VARCHAR(200) COMMENT '验收任务名称',
    `task_type` VARCHAR(50) COMMENT '任务类型',
    `status` INT DEFAULT 0 COMMENT '状态 0-待验收 1-验收中 2-已通过 3-未通过',
    `acceptance_standard` TEXT COMMENT '验收标准',
    `result_description` TEXT COMMENT '验收结果描述',
    `problem_count` INT DEFAULT 0 COMMENT '问题数量',
    `acceptance_by` BIGINT COMMENT '验收人ID',
    `acceptance_time` DATETIME COMMENT '验收时间',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验收任务表';

CREATE TABLE IF NOT EXISTS `m04_acceptance_problem` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `task_id` BIGINT NOT NULL COMMENT '验收任务ID',
    `problem_title` VARCHAR(200) COMMENT '问题标题',
    `problem_level` INT DEFAULT 1 COMMENT '问题级别 1-一般 2-严重 3-重大',
    `problem_description` TEXT COMMENT '问题描述',
    `photo_path` VARCHAR(500) COMMENT '问题照片',
    `status` INT DEFAULT 0 COMMENT '状态 0-待整改 1-整改中 2-已整改 3-已复查',
    `rectify_deadline` DATE COMMENT '整改截止日期',
    `rectify_result` TEXT COMMENT '整改结果',
    `rectify_by` BIGINT COMMENT '整改人ID',
    `review_by` BIGINT COMMENT '复查人ID',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验收问题表';

CREATE INDEX idx_m04_project_code ON m04_project(project_code);
CREATE INDEX idx_m04_project_region ON m04_project(region_code);
CREATE INDEX idx_m04_work_order_status ON m04_work_order(status);
CREATE INDEX idx_m04_work_order_type ON m04_work_order(type);
CREATE INDEX idx_m04_safety_check_project ON m04_safety_check(project_id);
CREATE INDEX idx_m04_cert_project ON m04_cert_verification(project_id);
CREATE INDEX idx_m04_construction_project ON m04_construction_record(project_id);
CREATE INDEX idx_m04_barrier_project ON m04_barrier_check(project_id);
CREATE INDEX idx_m04_electricity_project ON m04_electricity_check(project_id);
CREATE INDEX idx_m04_delivery_package_project ON m04_delivery_package(project_id);
CREATE INDEX idx_m04_delivery_file_package ON m04_delivery_file(package_id);
CREATE INDEX idx_m04_acceptance_task_project ON m04_acceptance_task(project_id);
CREATE INDEX idx_m04_acceptance_problem_task ON m04_acceptance_problem(task_id);