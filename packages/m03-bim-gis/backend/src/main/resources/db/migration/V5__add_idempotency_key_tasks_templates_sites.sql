-- V5: 为创建类接口补充幂等键，防止网络重试/按钮连点导致重复数据
-- 配合 DesignTask.idempotencyKey / ParametricTemplate.idempotencyKey / Site.idempotencyKey 使用。
-- 幂等键为 NULL 时不触发唯一约束（MySQL 唯一索引允许多个 NULL），旧数据不受影响。

ALTER TABLE m03_design_task
  ADD COLUMN idempotency_key VARCHAR(64) DEFAULT NULL
  COMMENT '创建幂等键(客户端生成UUID)，重复创建返回已存在任务'
  AFTER updated_at;

CREATE UNIQUE INDEX uk_task_idempotency ON m03_design_task(idempotency_key);

ALTER TABLE m03_parametric_template
  ADD COLUMN idempotency_key VARCHAR(64) DEFAULT NULL
  COMMENT '创建幂等键(客户端生成UUID)，重复创建返回已存在模板'
  AFTER updated_at;

CREATE UNIQUE INDEX uk_template_idempotency ON m03_parametric_template(idempotency_key);

ALTER TABLE m03_site
  ADD COLUMN idempotency_key VARCHAR(64) DEFAULT NULL
  COMMENT '站点幂等键(客户端生成UUID)，重复提交同键站点跳过不翻倍'
  AFTER invalid_reason;

CREATE UNIQUE INDEX uk_site_idempotency ON m03_site(idempotency_key);
