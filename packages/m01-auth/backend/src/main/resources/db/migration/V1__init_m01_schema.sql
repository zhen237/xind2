-- =============================================================================
-- V1：M01 认证/权限模块建表 + 初始化
--
-- 背景（2026-09-15 生产读接口扫荡发现）：
--   m01-auth 此前 spring.flyway.enabled=false，且仓库里没有任何 m01 迁移文件，
--   m01_* 六张表只写在遗留脚本 scripts/init-mysql.sql 里、**从未进过迁移链**。
--   结果：任何环境（含生产/本地）都没有这些表 → 登录、取用户、取菜单全部必炸。
--   本迁移把它们正式纳入 Flyway，从此空库启动即有表。
--
-- 幂等性说明：
--   建表用 CREATE TABLE IF NOT EXISTS；索引并入建表 KEY 子句（MySQL 8 不支持
--   CREATE INDEX IF NOT EXISTS，独立的 CREATE INDEX 在重复执行时会报错）。
--   种子用 INSERT IGNORE —— m01_user.username / m01_role.role_code /
--   m01_menu.menu_code 均有 UNIQUE 约束，IGNORE 才是真幂等（对比 m03_device
--   无唯一键时 INSERT IGNORE 是伪幂等，会被重复插入）。
--   关联表（user_role / role_menu）的 INSERT 全部通过 **查 code/id 的子查询** 定位，
--   不写死自增 id，因此无论表里已有多少行都能正确落位。
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- 用户
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m01_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL COMMENT '登录名',
    password VARCHAR(255) NOT NULL COMMENT 'BCrypt 密文',
    real_name VARCHAR(100) COMMENT '姓名',
    email VARCHAR(100) COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    status TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_m01_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- -----------------------------------------------------------------------------
-- 角色
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m01_role (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_code VARCHAR(50) NOT NULL COMMENT '角色编码',
    role_name VARCHAR(100) NOT NULL COMMENT '角色名称',
    description VARCHAR(255) COMMENT '说明',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_m01_role_code (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- -----------------------------------------------------------------------------
-- 用户-角色
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m01_user_role (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    KEY idx_m01_user_role_role (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- -----------------------------------------------------------------------------
-- 菜单
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m01_menu (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    parent_id BIGINT DEFAULT 0 COMMENT '父菜单ID，0 为顶级',
    menu_code VARCHAR(50) NOT NULL COMMENT '菜单编码',
    menu_name VARCHAR(100) NOT NULL COMMENT '菜单名称',
    menu_type TINYINT DEFAULT 1 COMMENT '1:目录 2:菜单 3:按钮',
    iframe_url VARCHAR(255) COMMENT '内嵌地址',
    permission_code VARCHAR(100) COMMENT '权限标识',
    sort_order INT DEFAULT 0 COMMENT '排序',
    status TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_m01_menu_code (menu_code),
    KEY idx_m01_menu_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜单表';

-- -----------------------------------------------------------------------------
-- 角色-菜单
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m01_role_menu (
    role_id BIGINT NOT NULL,
    menu_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, menu_id),
    KEY idx_m01_role_menu_menu (menu_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色菜单关联表';

-- -----------------------------------------------------------------------------
-- 操作日志
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS m01_operation_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT COMMENT '操作人ID',
    username VARCHAR(50) COMMENT '操作人登录名',
    operation_type VARCHAR(50) COMMENT '操作类型',
    operation_desc VARCHAR(500) COMMENT '操作描述',
    module_code VARCHAR(50) COMMENT '模块编码',
    ip_address VARCHAR(50) COMMENT '客户端IP',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_m01_oplog_user (user_id),
    KEY idx_m01_oplog_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';


-- =============================================================================
-- 初始化数据（种子密码均为 admin123，与 README.md「默认账号」一节一致）
--
-- 【2026-09-15 修正】此处原先照抄了遗留脚本 scripts/init-mysql.sql 里的密文
--   $2a$10$N9qo8uLOickgx2ZMRZoMye.IjzqAKL9xL5jvMFVdNJHvGCgTq/VEq
--   经 BCryptPasswordEncoder 实测：它 **不是** 任何候选口令的有效 BCrypt（是对
--   网上流传的 "password" 密文 $2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
--   的误抄，第 30 字符起被改写），导致 POST /api/m01/auth/login 恒返回 401。
--   下面的密文由 BCryptPasswordEncoder.encode("admin123") 生成并已实测通过
--   （见 drills 的「真登录」断言），cost=10，与旧值同格式。
-- =============================================================================

INSERT IGNORE INTO m01_user (username, password, real_name, email, status) VALUES
('admin',    '$2a$10$Wpc6XfBZzJj5IYBPzn16yeyaZ5Ud93ccPYmCwxATXyViyDMHwcs2a', '超级管理员', 'admin@example.com',    1),
('operator', '$2a$10$Wpc6XfBZzJj5IYBPzn16yeyaZ5Ud93ccPYmCwxATXyViyDMHwcs2a', '运维人员',   'operator@example.com', 1),
('designer', '$2a$10$Wpc6XfBZzJj5IYBPzn16yeyaZ5Ud93ccPYmCwxATXyViyDMHwcs2a', '设计人员',   'designer@example.com', 1),
('planner',  '$2a$10$Wpc6XfBZzJj5IYBPzn16yeyaZ5Ud93ccPYmCwxATXyViyDMHwcs2a', '规划人员',   'planner@example.com',  1);

INSERT IGNORE INTO m01_role (role_code, role_name, description) VALUES
('admin',    '超级管理员', '系统超级管理员'),
('operator', '运维人员',   '日常运维操作人员'),
('designer', '设计人员',   'BIM设计人员'),
('planner',  '规划人员',   '网络规划人员');

-- 顶级菜单（parent_id = 0）
INSERT IGNORE INTO m01_menu (parent_id, menu_code, menu_name, menu_type, iframe_url, permission_code, sort_order) VALUES
(0, 'system',     '系统管理',   1, NULL, 'system:view',     1),
(0, 'simulation', '网络规划',   1, NULL, 'simulation:view', 2),
(0, 'design',     '三维设计',   1, NULL, 'design:view',     3),
(0, 'delivery',   '数智交付',   1, NULL, 'delivery:view',   4),
(0, 'twin',       '数字孪生',   1, NULL, 'twin:view',       5);

-- 二级菜单：父级用 menu_code 子查询定位，不写死自增 id（遗留脚本写死 1/5/8/11/14，
-- 仅在"表恰好为空、且插入顺序不变"时成立，这里改成结构性定位）
INSERT IGNORE INTO m01_menu (parent_id, menu_code, menu_name, menu_type, iframe_url, permission_code, sort_order)
SELECT p.id, x.menu_code, x.menu_name, 2, x.iframe_url, x.permission_code, x.sort_order
FROM (SELECT 'system' AS pcode, 'system_user' AS menu_code, '用户管理' AS menu_name, '/modules/m01/user.html' AS iframe_url, 'system:user:view' AS permission_code, 1 AS sort_order
      UNION ALL SELECT 'system',     'system_role',        '角色管理', '/modules/m01/role.html',           'system:role:view',        2
      UNION ALL SELECT 'system',     'system_menu',        '菜单管理', '/modules/m01/menu.html',           'system:menu:view',        3
      UNION ALL SELECT 'system',     'system_progress',    '进度看板', NULL,                               'system:progress:view',    4
      UNION ALL SELECT 'simulation', 'sim_plan',           '规划方案', '/modules/m02/plan.html',           'simulation:plan:view',    1
      UNION ALL SELECT 'simulation', 'sim_simulation',     '覆盖仿真', '/modules/m02/simulation.html',     'simulation:sim:view',     2
      UNION ALL SELECT 'design',     'design_project',     '项目管理', '/modules/m03/project.html',        'design:project:view',     1
      UNION ALL SELECT 'design',     'design_model',       '模型管理', '/modules/m03/model.html',          'design:model:view',       2
      UNION ALL SELECT 'design',     'design_collision',   '碰撞检测', '/modules/m03/collision.html',      'design:collision:view',   3
      UNION ALL SELECT 'delivery',   'delivery_order',     '工单管理', '/modules/m04/order.html',          'delivery:order:view',     1
      UNION ALL SELECT 'delivery',   'delivery_inspection','验收管理', '/modules/m04/inspection.html',     'delivery:inspection:view', 2
      UNION ALL SELECT 'delivery',   'delivery_package',   '交付包管理','/modules/m04/package.html',       'delivery:package:view',   3
      UNION ALL SELECT 'twin',       'twin_monitor',       '实时监控', '/modules/m05/monitor.html',        'twin:monitor:view',       1
      UNION ALL SELECT 'twin',       'twin_alert',         '告警管理', '/modules/m05/alert.html',          'twin:alert:view',         2
      UNION ALL SELECT 'twin',       'twin_device',        '设备管理', '/modules/m05/device.html',         'twin:device:view',        3
      UNION ALL SELECT 'twin',       'twin_screen',        '大屏中心', '/modules/screen/index.html',       'twin:screen:view',        4
     ) x
JOIN m01_menu p ON p.menu_code = x.pcode;

-- 角色-菜单：admin 拥有全部菜单
INSERT IGNORE INTO m01_role_menu (role_id, menu_id)
SELECT r.id, m.id FROM m01_role r CROSS JOIN m01_menu m WHERE r.role_code = 'admin';

-- 用户-角色：按用户名与角色编码对应
INSERT IGNORE INTO m01_user_role (user_id, role_id)
SELECT u.id, r.id FROM m01_user u JOIN m01_role r ON r.role_code = u.username
WHERE u.username IN ('admin', 'operator', 'designer', 'planner');
