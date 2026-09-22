# S4 产物目录说明

## pipeline/ — 全链路流水线产物（最新，2026-08-22 生成）

通过完整链路（S1 设计 → S3 分级审查闸门 → BOM 生成 → S5 反馈）经 API 实际运行生成，
每个 Excel 含三个 Sheet：**BOM 物料清单 / 关键工序工艺 / 纤芯分配表**。

| 文件 | 场景 | BOM 项 | 工序 | 纤芯 | 特征 |
|------|------|--------|------|------|------|
| `D001_宏站_全链路BOM.xlsx` | 5G 宏站 | 100 条（15 主/53 辅/32 缆） | 26 道 | 35 条 | 干净场景，闸门 allowed |
| `D002_室分_全链路BOM_含整改标记.xlsx` | 室分系统 | 85 条（14 主/42 辅/29 缆） | 31 道（含 3 道 RECT） | 26 条 | 闸门 allowed_with_warnings，14 项物料带「⚠ 需整改」标记 |
| `D003_微站_全链路BOM.xlsx` | 微站 | 44 条 | 19 道 | 8 条 | 轻量场景 |

D002 的 3 道 RECT 整改核验工序来源（S3 审查违规自动转化）：

| 工序 | 违规规则 | 国标依据 |
|------|---------|---------|
| RECT-01 | LP-203 光缆与电源线间距不足 | GB 50689-2011 |
| RECT-02 | EL-112 接地电阻临界 | GB/T 6451-2015 |
| RECT-03 | OS-301 吊顶内路由待复核 | YD 5120-2010 |

## 根目录 xlsx — 脚本直出产物（早期）

`物料清单_BOM_*.xlsx` 由 `generate_all_bom.py` 离线脚本直接生成（未走完整链路），
保留作对比基准。`benchmark_bom.py` / `verify_all_ac.py` 用于性能基准与验收指标验证。

## volume-report/ — 工程量报表导出产物（2026-09-22 新增）

[S4-S1-迁移] 从 QGIS 插件「导出工程量报表」迁入 S4 Web 端，由 `VolumeReportExporter`
（Apache POI 5.2.5）生成，4 sheet 工作簿：

| Sheet | 内容 | 标注 |
|-------|------|------|
| **BOM 物料清单** | 物料编码 / 名称 / 规格 / 数量 / 类别（main_device / auxiliary / cable） | — |
| **设备清单** | 设备名 / 型号 / 坐标 / 所属站点 / 安装方式 | — |
| **管线明细** | 管线编号 / 起点终点 / 长度（m）/ 敷设方式（直埋/管道/架空/桥架）/ 光纤类型（G.652D/G.657A2/G.655） | — |
| **造价估算汇总** | 总成本 / 每米成本 / 材料费 / 施工费 / 辅材 / 管理费 5% / 利润 7% / 税金 9% | ⚠️ **顶部黄底警告"概算/示意"，禁止伪称行业基准** |

**单价参数库**：`backend/src/main/resources/cost_configs.json`（复用 QGIS
`PipelineConfig.cost_configs / fiber_cost_configs` 口径），不修改代码即可覆盖底层参数。
未知类型自动回退默认（管道路由单价 → 80 元/m）。

**调用方式**：
```bash
# JSON（前端 /report 页面默认）
GET /api/s4/bom/{designTaskId}/volume-report

# Excel 下载（前端「导出工程量报表 →」按钮）
GET /api/s4/bom/{designTaskId}/volume-report/export
# 文件名：VolumeReport_<designTaskId>_<timestamp>.xlsx
```

**测试覆盖**：`CostEstimationServiceTest` 9 例（正常管线 / 未知类型回退 / 空 / 比例 /
每米成本 / 警告 / 零长度） + `VolumeReportExporterTest` 3 例（4 sheet 存在 / 空 / null）。

**FTTH 交付物**走上传式（见 S1-S4 交接说明 §5.2），下期再启。
