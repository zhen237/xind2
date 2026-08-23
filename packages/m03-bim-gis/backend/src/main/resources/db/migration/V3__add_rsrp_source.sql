-- V3: 添加 RSRP 数据来源字段
-- 用于区分仿真值(simulated, 模型 Okumura-Hata 估算)与实测值(measured, 现场勘测/路测)
-- 前端覆盖分析据此判断使用真值(rsrp 实测)还是估算值；实测站点导入后自动切换。
-- 默认 simulated，保证历史已生成站点在升级后仍为仿真标注。

ALTER TABLE m03_site
  ADD COLUMN rsrp_source VARCHAR(20) DEFAULT 'simulated' COMMENT 'RSRP数据来源: simulated=模型仿真, measured=实测/现场勘测' AFTER rsrp;
