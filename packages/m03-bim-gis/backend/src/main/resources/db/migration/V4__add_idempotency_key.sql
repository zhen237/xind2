-- V4: 上传幂等键，防止 QGIS 插件网络抖动重试导致重复创建设计方案
-- 配合 DesignData.idempotencyKey / DesignScheme.idempotencyKey 使用。
-- 幂等键为 NULL 时不触发唯一约束（MySQL 唯一索引允许多个 NULL），旧数据不受影响。

ALTER TABLE m03_design_scheme
  ADD COLUMN idempotency_key VARCHAR(64) DEFAULT NULL
  COMMENT '上传幂等键(QGIS插件生成UUID)，重复上传返回已存在方案'
  AFTER route_type;

CREATE UNIQUE INDEX uk_scheme_idempotency ON m03_design_scheme(idempotency_key);
