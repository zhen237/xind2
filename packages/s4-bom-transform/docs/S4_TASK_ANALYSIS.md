# S4 施工指令转化（BOM）— 任务分析

> 负责人：庞（GitHub: nosh1816）｜ 开发分支：feat/s4-bom-transform ｜ 分析日期：2026-08-09
> 来源：《全赛题需求设计文档》v1.0 §S4 + 2026-07-13 分工方案

---

## 0. 一句话定位

你是流水线**第 4 环**：把 S1 设计产出的设备布局清单，自动转化为可施工的 BOM 物料清单（主设备 + 辅材 + 线缆），用 Excel 导出交付施工方。把 **2-4 小时**的人工施工准备压缩到 **1 分钟**内。

---

## 1. 流水线位置

```
S1 设计 ─→ S3 审查 ─→ [S4 BOM 转化] ─→ S5 施工监管
设备清单    审查通过      │              ▲
            设计成果       ▼              │
                         BOM Excel ─── 验真对比（I4 契约）
```

- **你的输入**：S1/S3 的设备布局清单（`DesignTaskDTO`，**只走 REST API**，禁止直连他人数据库）
- **你的输出**：BOM 物料清单（`BomItemDTO`）+ Excel 文件 → 推送给 S5

---

## 2. 量化硬指标（交差硬约束）

| 指标 | 官方要求 | 我们的目标 | 怎么验证 |
|---|---|---|---|
| 施工准备时间缩短 | ≥ 50% | **≥ 95%**（2-4h → 1min）| 端到端调 `/api/s4/bom/generate` 计时 |
| 产出物 | BOM 等施工指令 | 主设备 + 辅材 + 线缆 | 输出三类 `BomItemDTO` |
| 设计-施工链路 | 打通 | 设计 → 物料映射 → BOM 全自动 | 端到端跑通 AC-8 |
| 线缆估算误差 | — | **< 15%** | 估算值 vs 实际布线对比 |
| 辅材漏项率 | — | **< 2%** | 人工对照清单核漏项 |

---

## 3. 负责的 3 个工程

| 工程 | 类型 | 端口 | 现状 | 工作量估算 |
|---|---|---|---|---|
| s4-bom-transform **后端** | Spring Boot 3.1.10 + MyBatis-Plus | **8090** | 空骨架（仅 Application.java）| 2 天 |
| s4-bom-transform **Python 引擎** | FastAPI (Python 3.10) | （内部）| **0 代码** | 3-5 天（最大） |
| s4-bom-transform **前端** | Vue3 + Element Plus | **5190** | 空目录 | 1-2 天 |

---

## 4. 13 个小模块拆解（按 P0/P1/P2 分阶段，每个 = 一个 PR）

### 🔵 P0 — 脚手架（先做，1 天，4 个 PR 可并行）

| 模块ID | 名称 | 类型 | 关键产出 |
|---|---|---|---|
| **S4-B-01** | Spring Boot 后端脚手架 | B | pom.xml + Application.java + application.yml + 健康检查 |
| **S4-B-04** | MyBatis-Plus + 建表 | B | DDL（s4_bom_task / s4_bom_item）+ Entity + Mapper |
| **S4-E-01** | FastAPI 引擎脚手架 | E | main.py + requirements.txt + /health |
| **S4-F-01** | Vue 前端脚手架 | F | vite + element-plus + 路由 + App.vue |

### 🟠 P1 — 核心引擎（最大工作量，3-5 天，9 个 PR）

| 模块ID | 名称 | 类型 | FR覆盖 | 关键产出 |
|---|---|---|---|---|
| **S4-E-02** | material_catalog.json 物料编码库 | E | FR-1 | 天线/RRU/BBU/电源/传输/铁塔 → 物料编码映射 |
| **S4-E-03** | 设备-物料映射 | E | FR-1/2 | 输入设备清单 → main_device BOM 明细 |
| **S4-E-04** | 辅材自动计算 | E | FR-3/4 | 天线→安装套件、RRU→防水套件、站点→接地+标签 |
| **S4-E-05** | 线缆长度估算 | E | FR-5/6 | 射频跳线 3m/根、光纤=水平距×1.2、主备双路由 |
| **S4-E-06** | openpyxl Excel 导出 | E | FR-8 | .xlsx 文件，中文编码正确 |
| **S4-E-07** | /api/v1/bom/generate 主入口 | E | FR-7 | 串联 5 个子模块，对外暴露 |
| **S4-B-03** | Java→Python HTTP 调用 + fallback | B | - | RestTemplate/WebClient + 超时降级 |
| **S4-B-02** | BOM 任务 API | B | FR-9 | /api/s4/bom/generate + 历史/详情 |
| **T7** | AI 生成样例设备清单 | - | - | 运城场景模拟数据（可与 P1 并行）|

### 🟢 P2 — 前端 + 联调（2 天，3 个 PR）

| 模块ID | 名称 | 类型 | FR覆盖 | 关键产出 |
|---|---|---|---|---|
| **S4-F-02** | BOM 三类清单展示 | F | FR-9 | 主设备/辅材/线缆三张表 |
| **S4-F-03** | 统计概览 + 导出按钮 | F | FR-9 | 调 /api/s4/bom/{id}/export |
| **T6** | 与 S1/S3 联调 | - | FR-10 | 拉取 DesignTaskDTO（I3 契约）|

---

## 5. 关键架构决策 D-1（**你拍板**）

### 问题：API 前缀与表前缀用 `m04_` 还是 `s4_`？

原 topic4 规格把 Java API 写在 M04 Controller 下（`/api/m04/bom/...`，表 `m04_bom_*`）。但 2026-07-13 分工方案已重组成独立 `s4-bom-transform` 模块，M04 仅作过渡。

### ✅ 建议：`s4_` 前缀

| 项 | 原 M04 规格 | 建议（按本需求落地）|
|---|---|---|
| Java API 前缀 | `/api/m04/bom/...` | **`/api/s4/bom/...`** |
| DB 表前缀 | `m04_bom_task` / `m04_bom_item` | **`s4_bom_task` / `s4_bom_item`** |
| 模块归属 | M04 Controller（过渡）| `s4-bom-transform`（独立）|

**理由**：
1. 分工方案已明确独立模块，与 S2/S3/S5 前缀一致
2. M04 共享前缀会让你的代码与王（S3）/李（S5）耦合，难独立交付
3. M04 过渡代码最终不并入交付

**拍板后**：T1/T2 直接按 `s4_` 落地，文档待决项关闭。

---

## 6. 数据库表设计（2 张 s4_ 表，照搬规格）

### `s4_bom_task` — BOM 任务

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| task_id | VARCHAR(64) UK | 任务 ID（UUID）|
| design_task_id | VARCHAR(64) | 关联 S1 设计任务 |
| project_id | VARCHAR(64) | 项目 ID |
| status | VARCHAR(20) | pending / running / done / failed |
| total_categories | INT | 总类目数 |
| total_qty | INT | 总数量 |
| main_device_qty | INT | 主设备数量 |
| auxiliary_qty | INT | 辅材数量 |
| cable_qty | INT | 线缆数量 |
| created_at | DATETIME | 创建时间 |
| finished_at | DATETIME | 完成时间 |

### `s4_bom_item` — BOM 物料明细

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| task_id | VARCHAR(64) | 关联 BOM 任务 |
| material_code | VARCHAR(32) | 物料编码（M-ANT-001）|
| material_name | VARCHAR(128) | 物料名称 |
| spec | VARCHAR(128) | 规格型号 |
| unit | VARCHAR(16) | 单位（套/根/包/件）|
| qty | INT | 数量 |
| single_length | DECIMAL(10,2) | 单根长度（米，线缆专用）|
| total_length | DECIMAL(10,2) | 总长度（米，线缆专用）|
| category | VARCHAR(20) | main_device / auxiliary / cable |

---

## 7. API 端点清单

| 端点 | 方法 | 用途 | FR |
|---|---|---|---|
| `/api/s4/bom/generate` | POST | 生成 BOM（接 designTaskId + projectId）| FR-9 |
| `/api/s4/bom/{taskId}` | GET | 查 BOM 详情（含三类清单）| FR-9 |
| `/api/s4/bom/history` | GET | 历史列表（分页）| FR-9 |
| `/api/s4/bom/{taskId}/export` | GET | 导出 Excel（.xlsx）| FR-8 |
| `/api/v1/bom/generate` | POST | Python 引擎主入口（**内部调用**，不对外）| FR-7 |

---

## 8. 8 个验收用例（AC，验收对照）

| AC | 功能 | Given | When | Then |
|---|---|---|---|---|
| AC-1 | 生成 BOM | 含天线的设备清单 + projectId | 调 /api/s4/bom/generate | 1 分钟内返回 BOM，时间缩短 ≥95% |
| AC-2 | 设备-物料映射 | material_catalog 含 M-ANT-001 等 | 调引擎生成 | 每台设备映射到正确物料编码，category=main_device |
| AC-3 | 辅材自动计算 | 已知天线/RRU/站点数 | 调引擎生成 | 安装套件/防水套件/接地材料/标签按 FR-3 推算，无漏项 |
| AC-4 | 线缆估算 | 设备含天线与 RRU，含坐标 | 调引擎生成 | 跳线=3m/根，光纤=水平距×1.2，输出单根/总长 |
| AC-5 | Excel 导出 | BOM 已生成 | 点"导出" | openpyxl 生成 .xlsx，中文编码正确，可下载 |
| AC-6 | 引擎集成 | Java 收到生成请求 | 调 Python 引擎 | 返回 BOM 并落库；引擎超时有 fallback |
| AC-7 | 前端展示 | BOM 已生成 | 前端打开 | 三类清单 + 统计概览正确渲染，导出按钮可用 |
| AC-8 | 跨赛题联调 | S1/S3 提供设计设备清单 API | S4 拉取并生成 | 端到端 BOM 自动生成成功，链路贯通 |

---

## 9. 风险与缓解

| 编号 | 风险 | 影响 | 缓解 |
|---|---|---|---|
| R-1 | **Python 引擎完全从零**，T3 是最大工作量 | 进度风险 | P1 优先 T3，T7 AI 样例数据先行驱动 |
| R-2 | S1/S3 设计数据接口契约未实战 | BOM 输入源不稳 | 先 mock `DesignTaskDTO`，T6 等其他赛题就绪后统一联调 |
| R-3 | 不用 Docker，本地启动 | 环境独立 | 后端 8090 / 前端 5190 端口已固化 |
| R-4 | 线缆估算依赖坐标，误差 <15% 难验证 | 验收挑战 | 多组样例对比（运城场景），用 Haversine 距离做基线 |

---

## 10. 推荐开发顺序（依赖图）

```
Step 1：拍板 D-1（建议 s4_）                ← 立刻决
   │
Step 2：P0 脚手架（4 个并行，1 天）          ← 立刻开工
   ├── S4-B-01 后端脚手架
   ├── S4-B-04 建表 + MyBatis-Plus
   ├── S4-E-01 Python 引擎脚手架
   └── S4-F-01 前端脚手架
   │
Step 3：T7 样例设备清单（与 P1 并行）         ← AI 造运城数据
   │
Step 4：P1 核心引擎（3-5 天，最大工作量）     ← 主战场
   ├── S4-E-02 material_catalog.json        ← 数据底座
   ├── S4-E-03 设备-物料映射                 ← main_device
   ├── S4-E-04 辅材自动计算                  ← auxiliary
   ├── S4-E-05 线缆长度估算                  ← cable
   ├── S4-E-06 openpyxl Excel 导出
   ├── S4-E-07 /api/v1/bom/generate 主入口   ← 串联上面 5 个
   ├── S4-B-03 Java→Python HTTP + fallback
   └── S4-B-02 BOM 任务 API
   │
Step 5：P2 前端 + 联调（2 天）
   ├── S4-F-02 三类清单展示
   ├── S4-F-03 统计 + 导出按钮
   └── T6 与 S1/S3 联调（I3 契约）
```

---

## 11. 关键技术选型

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Spring Boot 3.1.10 + MyBatis-Plus | 与 M0x 模块统一 |
| Python 引擎 | FastAPI (Python 3.10) | 与 S2/S3/m07 统一 |
| HTTP 调用 | RestTemplate 或 WebClient | Java→Python，含超时 fallback |
| Excel 导出 | openpyxl | Python 侧生成 .xlsx |
| 数据库 | MySQL (comm_platform) | s4_ 表前缀 |
| 文件存储 | MinIO | Excel 文件存这里 |
| 前端 | Vue3 + Element Plus | 与 M06 视觉规范一致 |
| 认证 | m01-auth JWT | 复用共享鉴权 |

---

## 12. 下一步建议

我可以立刻开始，三个选项任你选：

- **选项 A**：把 **P0 脚手架 4 个工程一次性建出来**（后端 + Python + 前端 + 建表 DDL）— 1 个 PR 批次
- **选项 B**：直接进 P1，先做 **S4-E-02 物料编码库**（最大依赖项，所有映射都靠它）
- **选项 C**：先 mock 一份**运城样例设备清单**（T7），驱动后续开发与验收

**我的推荐：A → C → B**。先把脚手架立起来，再造样例数据驱动开发，最后进引擎核心逻辑。
