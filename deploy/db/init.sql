-- =============================================================================
-- xind2 初始化数据库脚本
-- 目标：创建共享库 comm_platform（UTF-8MB4），字符集与仓库约定一致。
-- 表结构由 Flyway 在应用首次启动时自动创建/迁移，本脚本只负责建库与字符集。
-- 执行（服务器上，MySQL 已随 docker-compose 或系统安装）：
--   密码从服务器 /opt/xind2/.env 读取（2026-09-15 已轮换为随机强密码）：
--     PW=$(sudo grep '^MYSQL_PASSWORD=' /opt/xind2/.env | cut -d= -f2-)
--     mysql -uroot -p"$PW" < init.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS comm_platform
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 使用新库（可选，方便后续手动操作）
USE comm_platform;

-- -----------------------------------------------------------------------------
-- （可选）生产建议：为平台创建独立账号，而非共用 root。
-- 当前部署使用 root（密码存于服务器 /opt/xind2/.env，不在仓库内），
-- 下面语句按需启用并替换强密码。
-- -----------------------------------------------------------------------------
-- CREATE USER IF NOT EXISTS 'comm'@'localhost' IDENTIFIED BY 'ChangeMe!Strong';
-- GRANT ALL PRIVILEGES ON comm_platform.* TO 'comm'@'localhost';
-- FLUSH PRIVILEGES;
