-- 任务级本地数据源：任务加载本地 GeoJSON 后持久化，重进项目可恢复
ALTER TABLE m03_design_task
    ADD COLUMN local_data_json LONGTEXT NULL COMMENT '任务本地加载的 GeoJSON 数据源（原始 JSON）' AFTER result_json;
