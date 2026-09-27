# S4 — 设计成果向施工指令的自动转化（BOM）

**类型**: Java Spring Boot 3.1.10 + Python FastAPI BOM 引擎 + Vue3 前端
**端口**: dev-proxy/后端 8090 / BOM 引擎 8100 / 前端 5190
**负责人**: 庞

## 模块职责

打通「S1 设计成果 → S3 审查闸门 → BOM 施工指令 → S5 施工监管」链路：

- **Python BOM 生成引擎**：设备-物料编码映射、辅材自动计算、线缆长度估算
- **S3 分级审查闸门**：四档分级（critical/error 拦截，warning/pending 放行并打标）
- **整改核验工序**：S3 违规自动转化为 RECT-xx 工序（含国标依据、设备关联、整改建议）
- **BOM→S3 反馈回路**：BOM 完成后回灌施工可行性评估
- **Excel 导出**：三 Sheet（BOM 物料清单 / 关键工序工艺 / 纤芯分配表），支持整改标记列；技术规范已内嵌在「关键工序工艺」Sheet，不再单独导出
- **[S4-S1-迁移 2026-09-22] 工程量报表**：从 QGIS 插件迁入（接口式）
  - 复用 S1→M03→S4 已落库的 `result.pipelines`（管线编号 / 起点终点 / 长度 / 敷设方式 / 光纤类型）
  - 套 QGIS `cost_configs` 概算单价算「材料费 + 施工费 + 辅材 + 管理费 + 利润 + 税金 → 总成本 / 每米成本」
  - **单价口径明确标注「概算 / 示意」**，不得伪称行业基准（详见 §工程量报表）
  - 输出：4 sheet Excel（BOM物料 / 设备清单 / 管线明细 / 造价估算汇总）+ 前端 `/report` 页面 + 一键导出
  - 单价参数化：`backend/src/main/resources/cost_configs.json`（不修改代码即可覆盖）
  - **设备清单口径**（§九·补 2026-09-22）：改逐设备明细（不再按型号聚合），补 parentDevice / azimuth / downtilt 3 列；VolumeReportExporter 表头 5 列均填实数据
- **[S4-S1-迁移 2026-09-22] FTTH 交付物（光路由表 + 光交箱汇总 + 机柜熔接盘图 + 系统图）**：从 QGIS 插件迁入（上传式）
  - 前端 `/ftth` 路由：8 个 .dbf 多文件选择（IMB/SITE/BOITE/CABLE/PTECH/INFRASTRUCTURE/ZNRO/ZPM，字段名已截断到 10 字符）
  - Spring Boot 代理：`POST /api/s4/ftth/upload`（multipart 透传到 Python 引擎）
  - Python 引擎（8100）：复用 `qgis-plugin/ftth.export_runner.export_from_dbf_single_workbook`（不依赖 PyQGIS，load_dbf 用 dbfread）
  - 输出：合并 Excel 工作簿（1 个光路由表 + 1 个光交箱汇总 + 每个 PM 各 1 个机柜熔接盘图 + 系统图，sheet 总数随 PM 数膨胀）+ ftth-data.json + 自检报告 ftth-validation.json（验收 AC-2 要求的五件套齐全）
  - 入口统一在 S4 前端 5190，按钮文案对齐 QGIS 原版「导出 FTTH 交付物（光路由表 + 光交箱汇总）」；QGIS 插件第 7 步原按钮保留至 S4 验收通过后删除（交接说明 §八）
- **安全加固**：taskId 白名单校验（防路径穿越）、127.0.0.1 监听、CORS 白名单

## 目录结构

```
packages/s4-bom-transform/
├── backend/      # Java Spring Boot 后端（MyBatis-Plus，表前缀 s4_）
├── dev-proxy/    # 开发代理（模拟 S1/S3/S5 接口 + 统一入口，端口 8090）
├── engine/       # Python FastAPI BOM 引擎（端口 8100）
│   ├── data/material_catalog.json   # 物料编码库
│   └── data/process_templates.json  # 工序工艺 / 验收标准参数库（底层参数导入）
├── frontend/     # Vue3 + Element Plus 前端（端口 5190）
├── outputs/      # BOM 产物（详见 outputs/README.md）
└── docs/         # 模块方案 / 任务分析 / 答辩方案 / 联调清单
```

## 启动

```bash
# Python BOM 引擎（端口 8100）
cd packages/s4-bom-transform/engine
venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8100

# dev-proxy 开发代理（端口 8090，mock S1/S3/S5）
cd packages/s4-bom-transform/dev-proxy
python -m uvicorn main:app --host 127.0.0.1 --port 8090

# 前端（端口 5190）
cd packages/s4-bom-transform/frontend
npm run dev
```

### 前端本地虚拟数据模式（免后端演示，仿 S1 做法）

前端 mock 模式**缺省即启用**（无需 `.env`；`.env` 被 `.gitignore` 排除，克隆后 `npm run dev` 开箱即演示）：
**只启动 `npm run dev` 即可完整演示**
（生成 → 轮询 → 三类清单 → 工序/纤芯 → `/report` 工程量报表四 sheet），不依赖 8090/8100。
数据来自真实引擎管线预生成的快照（`frontend/src/mock/data/`），导出按钮下载
`frontend/public/mock/BOM_demo.xlsx`。联调真实后端时在 `frontend/.env` 设 `VITE_USE_MOCK=false` 并重启。

```bash
# 重新生成前端虚拟数据快照（改了引擎逻辑/物料库后执行）
cd packages/s4-bom-transform/engine
venv/Scripts/python dump_mock_frontend.py

# mock 自测（用真实 axios 驱动 adapter，验证全链路）
cd packages/s4-bom-transform/frontend
node test-mock.mjs
```

### 单元测试与一键验证

```bash
# Python 引擎单元测试（33 例：映射/辅材/线缆公式/闸门/整改传导）
cd packages/s4-bom-transform/engine
venv/Scripts/python -m pytest tests/ -v

# 样例设计数据一键验证（D001/D002/D003 → BOM + Excel + 8 项规则核对，失败退出码 1）
venv/Scripts/python verify_bom.py          # 全部场景
venv/Scripts/python verify_bom.py D001     # 仅云川宏站
```

Java 后端测试：`cd backend && mvn test`（BomServiceTest 覆盖入参校验/闸门/导出/查询）。

## API 约定

```
POST /api/s4/bom/generate            # 从设计成果生成 BOM（designTaskId 必填）
GET  /api/s4/bom/{taskId}/status     # 查询任务状态
GET  /api/s4/bom/{taskId}/full       # 查询完整 BOM 结果
GET  /api/s4/bom/{taskId}/export     # 导出 Excel（三 Sheet）
GET  /api/s4/bom/history             # 历史任务列表

# [S4-S1-迁移] 工程量报表（S1 设计成果 → S4 在线导出）
GET  /api/s4/bom/{designTaskId}/volume-report         # 工程量报表 JSON（设备+管线+造价）
GET  /api/s4/bom/{designTaskId}/volume-report/export  # 工程量报表 Excel（4 sheet，标注「概算/示意」）

# [S4-S1-迁移 §5.2 2026-09-22] FTTH 交付物（上传式 — 8 个 .dbf）
POST /api/s4/ftth/upload                               # 8 个 .dbf multipart 上传 → 元数据 JSON（taskId + sheetCount + sheetNames + 下载链接）
GET  /api/s4/ftth/{taskId}                             # 查询导出任务元数据
GET  /api/s4/ftth/{taskId}/download                    # 下载合并工作簿 .xlsx
GET  /api/s4/ftth/{taskId}/validation                  # 下载自检报告 .json
GET  /api/s4/ftth/{taskId}/json                        # 下载 ftth-data .json
```

## 核心验收指标

### 业务指标（赛题口径）

| 指标 | 要求 | 实测 |
|------|------|------|
| 施工准备时间 | 缩短 ≥ 95% | 全链路约 7 秒（人工 2-4 小时） |
| 线缆估算误差 | < 15% | 满足 |
| 辅材漏项率 | < 2% | 满足 |

### S1 迁移验收（S1-S4 交接说明 §七，2026-09-22 对照）

| 验收项 | 要求（§七原文） | 状态 |
|--------|----------------|------|
| AC-1 工程量报表 | S4 能独立导出工程量报表（BOM + 设备清单 + 管线明细 + 造价估算汇总），字段口径与 §5.1 一致，且造价明确标注「概算」 | ✅ 4 sheet Excel（`/report` 页面 + 一键导出）；设备清单逐设备明细（parentDevice / azimuth / downtilt 已与 QGIS 原导出口径对账）；造价 sheet 顶部黄底「概算 / 示意」警告 |
| AC-2 FTTH 交付物 | S4 能上传 FTTH 交付物目录并生成光路由表 + 光交箱汇总 + 机柜熔接盘图 + 系统图 + 自检报告 | ✅ `/ftth` 路由上传 8 个 .dbf → 合并工作簿（1 光路由表 + 1 光交箱汇总 + 每 PM 熔接盘图/系统图）+ 自检报告 `ftth-validation.json`（JAD 真实数据 124 sheet 实测） |
| AC-3 全流程在线闭环 | 演示：S1 设计 → S3 审查 → S4 出清单/交付物 全流程在线闭环，无需切回 QGIS 导出 | ✅ S4 Web 端统一入口：流水线概览页「导出工程量报表 →」「导出 FTTH 交付物（光路由表 + 光交箱汇总）」两按钮；前端 mock 模式可免后端完整演示 |
| QGIS 按钮去留 | QGIS 插件第 7 步的这两个按钮在 S4 验收通过后才删除（见 §八） | ⏸ **保留中**——S4 侧 AC-1/AC-2/AC-3 已实现，待联调验收通过后由 S1 侧按 §八 删除，S4 不动 QGIS 插件代码 |

## 工程量报表（S1 迁移）

> 2026-09-22 接收 S1 模块（QGIS 插件第 7 步）「导出工程量报表」+「导出 FTTH 交付物」迁移任务（交接说明 §5.1 / §5.2 / §七）。
> 两项均已交付：**工程量报表**（接口式，本节）+ **FTTH 交付物**（上传式，见 §API 约定与 `outputs/README.md`）。
> QGIS 插件第 7 步原按钮保留至 S4 验收通过后删除（交接说明 §八），删除前 QGIS 与 S4 Web 端双入口并存。

**数据通路**：S1 设计生成管线 → 上传 M03 落 `DesignData.pipelines` → `/api/m03/design/tasks/{id}/result` 回吐 → S4 `BomService.normalizeDesignData` 消费 → 工程量报表。

**字段口径（与交接说明 §5.1 一致，验收 AC-1）**：BOM 物料（编码/名称/规格/数量/类别）+ 设备清单（逐设备明细，含所属站点/方位角/下倾角）+ 管线明细（编号/起终点/长度/敷设方式/光纤类型）+ 造价估算汇总（材料费/施工费/辅材/管理费 5%/利润 7%/税金 9%/总成本/每米成本）——四 sheet 字段与 QGIS 原导出逐项对账；**所有造价字段明确标注「概算」**（顶部黄底警告 + 单元格高亮），禁止伪称行业基准。

**消费端实现**（仅 S4 侧）：

| 端点 | 用途 |
|---|---|
| `GET /api/s4/bom/{designTaskId}/volume-report` | JSON：设备 + 管线 + 造价估算（标注「概算/示意」） |
| `GET /api/s4/bom/{designTaskId}/volume-report/export` | Excel：4 sheet（BOM物料 / 设备清单 / 管线明细 / 造价估算汇总） |

**前端入口**：`/report` 路由（`VolumeReport.vue`），流水线概览页 S4 卡片新增「导出工程量报表 →」按钮。

**单价参数**：`backend/src/main/resources/cost_configs.json`（复用 QGIS `PipelineConfig.cost_configs / fiber_cost_configs`），不修改代码即可导入/覆盖底层参数。所有造价字段对外标注 **「概算 / 示意」**，禁止伪称行业基准。

**测试**：
- `backend/src/test/.../CostEstimationServiceTest` — 9 例：正常管线 / 未知类型回退 / 空 / 比例 / 每米成本 / 警告
- `backend/src/test/.../VolumeReportExporterTest` — 3 例：4 sheet 存在 / 空 / null
- 前端 `mock/index.js` — 工程量报表 + 设计-审查聚合 + S1 任务列表均已 mock 化
