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
（Apache POI 5.2.5）生成，4 sheet 工作簿。字段口径与交接说明 §5.1 一致（验收 AC-1），
造价明确标注「概算」：

| Sheet | 内容 | 标注 |
|-------|------|------|
| **BOM 物料清单** | 物料编码 / 名称 / 规格 / 数量 / 类别（main_device / auxiliary / cable） | — |
| **设备清单** | **逐设备明细**（每台一行，与 QGIS `_device_layout` 原导出口径一致）：所属站点 / 设备名称 / 设备类型 / 方位角(°) / 下倾角(°) | §九·补 2026-09-22 设备清单字段对账：原聚合口径会丢 3 列（parentDevice/azimuth/downtilt）已修复 |
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

**FTTH 交付物**（上传式，交接说明 §5.2 / 验收 AC-2）已于 2026-09-22 同步交付，见下节 `ftth-deliverables/`。

## ftth-deliverables/ — FTTH 交付物上传式产物（2026-09-22 新增）

[S4-S1-迁移 §5.2] 从 QGIS 插件「导出 FTTH 交付物（光路由表 + 光交箱汇总）」迁入 S4 Web 端。
前端 `/ftth` 路由 `FtthUpload.vue` 上传 8 个 .dbf（`IMB / SITE / BOITE / CABLE / PTECH / INFRASTRUCTURE / ZNRO / ZPM`），
复用 `qgis-plugin/ftth.export_runner.export_from_dbf_single_workbook` 生成合并工作簿。

### 合并工作簿 sheet 结构

| Sheet 类型 | 数量 | 说明 |
|---|---|---|
| **光路由表** | 1 | 每户的「最近 BPE → IMB」光路连接清单 |
| **光交箱汇总** | 1 | BPE/PBO 容量 / 已用 / 熔接盘使用情况 |
| **机柜熔接盘图** | N × 每个 PM | 每个 PM 一个：`Plan_Baie_<PM编码>` |
| **系统图** | N × 每个 PM | 每个 PM 一个：`Syno_<MRJ编号>_<PM编码>` |

示例：`docs/真实数据/Plan_de_récolement/Shape/` 跑出 **124 个 sheet**：
- 1 × 光路由表 + 1 × 光交箱汇总
- 121 × 机柜熔接盘图（BPE / PBO 各站点）
- 4 × 系统图（每 PM 一对：Plan_Baie + Synoptique）

### 8 层记录数（与 `qgis-plugin/ftth/field_map.py:125 EXPECTED_COUNTS_JAD` 对齐）

| Layer | 含义 | JAD-MARJANE 期望 | 实测 |
|---|---|---|---|
| IMB | 楼栋/住户 | 51 | ✅ 51 |
| SITE | 技术站点 NRO/PM | 3 | ✅ 3 |
| BOITE | 光箱 BPE/PBO | 118 | ✅ 118 |
| CABLE | 光缆 | 120 | ✅ 120 |
| PTECH | 杆/井技术点 | 141 | ✅ 141 |
| INFRASTRUCTURE | 管道/杆路 | 193 | ✅ 193 |
| ZNRO | OLT 覆盖范围 | 1 | ✅ 1 |
| ZPM | PM/SRO 范围 | 2 | ✅ 2 |

### 调用方式

```bash
# 8 个 .dbf multipart 上传
curl -X POST http://localhost:8090/api/s4/ftth/upload \
  -F "files=@IMB.dbf" -F "files=@SITE.dbf" -F "files=@BOITE.dbf" \
  -F "files=@CABLE.dbf" -F "files=@PTECH.dbf" -F "files=@INFRASTRUCTURE.dbf" \
  -F "files=@ZNRO.dbf" -F "files=@ZPM.dbf"

# 响应：{ taskId, sheetCount, sheetNames, layerCounts, downloadUrl, validationUrl, jsonUrl, ... }

# 下载合并 xlsx
GET /api/s4/ftth/{taskId}/download
```

### 单独输出（与合并 xlsx 并行）

- `ftth-data.json` — 前端 S1 同步用（点位 + 光缆 + 汇总）
- `ftth-validation.json` — 自检报告（S3 校验规则复用）
- `ftth-plan.json` — 正向智能规划设计产物（反推重建 + 对比真实）

### 配置

- `S4_QGIS_PLUGIN_PATH` 环境变量可覆盖默认 `qgis-plugin/` 路径（默认自动推导：上溯 5 层到仓库根）
- `engine/requirements.txt` 已加 `dbfread>=3.0.0` + `python-multipart>=0.0.9`

### 测试覆盖

`engine/tests/test_ftth_export.py` — 7 例：
1. 8 层清单契约
2. 缺失 .dbf 抛 FileNotFoundError
3. QGIS plugin 路径解析
4. 端到端导出（JAD 真实数据集，124 sheet）
5. 缺 1 层仍抛错
6. 两次导出 task_id 互不干扰
7. 不存在 task_id 查询返回 None
