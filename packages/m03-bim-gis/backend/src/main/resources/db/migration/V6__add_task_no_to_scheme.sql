-- 任务主线追溯：设计方案表增加来源任务编号，任务执行产出的方案可回溯到所属任务
ALTER TABLE m03_design_scheme
    ADD COLUMN task_no VARCHAR(64) NULL COMMENT '来源设计任务编号(S1 taskNo)' AFTER project_id;

CREATE INDEX idx_m03_design_scheme_taskno ON m03_design_scheme(task_no);
