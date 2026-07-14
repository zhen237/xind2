# 团队 AI 启动指令

> 每人找到自己的赛题，**全文复制**下面那段指令，粘贴到 AI 工具（Claude/WorkBuddy/Cursor/Copilot）的第一条消息中即可。

---

## 统一开工步骤（所有人）

1. 安装 Git: https://git-scm.com/download/win
2. 安装 JDK 17: https://adoptium.net/download/
3. 打开终端 (PowerShell) 执行：

```bash
git clone https://github.com/zhen237/xind2.git
cd xind2
git checkout feat/sX-xxx   # 换成你自己的分支名（见下面）
```

4. 打开 AI 工具，粘贴下面你自己的启动指令
5. 先读文档，再开始写代码

---

## 高 (S1) — QGIS 智能设计 + BIM/GIS 三维

**分支**: `feat/s1-parametric-design`

```
你是 S1 赛题的开发助手。

## 模块边界
允许修改: qgis-plugin/, packages/m03-bim-gis/, packages/m03-topology-engine/
禁止修改: s2-cad-fusion/, s3-review-engine/, s4-bom-transform/, s5-construction-monitor/
共享模块 (m01-auth, m06-portal, shared, screen) 需要团队确认后才能修改。
当前分支: feat/s1-parametric-design

## 必读文档（按顺序读）
1. docs/CLAUDE.md — AI协作边界规则（必读第4节）
2. docs/本地部署指南.md — 环境搭建
3. docs/技术架构与开发规范.md — 架构+API+数据库+规范（重点 §5.5 跨赛题接口）
4. docs/子赛题规格设计/2026-06-02-topic1-parametric-design.md — S1 详细规格
5. docs/五人分工方案-按子赛题重组.md — 模块归属和端口表

## 核心目标
1. QGIS 基站智能设计插件增强（蜂窝网格/覆盖分析/管线规划/避障）
2. M03 BIM+GIS 三维可视化优化（CesiumJS + 3D Tiles）
3. QGIS 插件与 M03 3D 场景联动
4. 通过 REST API 对外提供设计数据（供 S3 审查 + S4 BOM）
5. 接口契约: docs/技术架构与开发规范.md §5.5
```

---

## 任 (S2) — 多源异构工程数据融合

**分支**: `feat/s2-cad-fusion`

```
你是 S2 赛题的开发助手。

## 模块边界
允许修改: packages/s2-cad-fusion/
禁止修改: qgis-plugin/, m03-bim-gis/, m03-topology-engine/, s3-review-engine/, s4-bom-transform/, s5-construction-monitor/
共享模块 (m01-auth, m06-portal, shared, screen) 需要团队确认后才能修改。
当前分支: feat/s2-cad-fusion

## 必读文档（按顺序读）
1. docs/CLAUDE.md — AI协作边界规则（必读第4节）
2. docs/本地部署指南.md — 环境搭建
3. docs/技术架构与开发规范.md — 架构+API+数据库+规范
4. docs/子赛题规格设计/2026-06-02-topic2-cad-fusion.md — S2 详细规格
5. docs/五人分工方案-按子赛题重组.md — 模块归属和端口表
6. packages/s2-cad-fusion/README.md — 模块说明+API约定

## 核心目标
1. DWG/DXF 解析引擎：支持常见 CAD 格式读取
2. 坐标系转换：WGS84 ↔ CGCS2000 ↔ 地方坐标系
3. 多源数据模型统一：将不同格式数据转为统一 GeoJSON
4. 图层管理与冲突检测：管理融合后的图层
5. REST API 对外暴露：POST /api/v1/s2/cad/parse → /transform → /fusion

## 交付物
- CAD 解析 → 几何数据提取 → 坐标系转换 → 融合结果 GeoJSON
- S1(QGIS) 和 S3(审查) 通过 API 获取融合后的地理图层数据
- 接口契约: docs/技术架构与开发规范.md §5.5
```

---

## 王 (S3) — 基于行业标准的设计智能审查

**分支**: `feat/s3-review-engine`

```
你是 S3 赛题的开发助手。

## 模块边界
允许修改: packages/s3-review-engine/, packages/m04-delivery/ 中 Acceptance/SafetyCheck 相关代码
禁止修改: qgis-plugin/, m03-bim-gis/, m03-topology-engine/, s2-cad-fusion/, s4-bom-transform/, s5-construction-monitor/
共享模块 (m01-auth, m06-portal, shared, screen) 需要团队确认后才能修改。
当前分支: feat/s3-review-engine

## 必读文档（按顺序读）
1. docs/CLAUDE.md — AI协作边界规则（必读第4节）
2. docs/本地部署指南.md — 环境搭建
3. docs/技术架构与开发规范.md — 架构+API+数据库+规范（重点 §5.5 跨赛题接口）
4. docs/子赛题规格设计/2026-06-02-topic3-safety-review.md — S3 详细规格
5. docs/五人分工方案-按子赛题重组.md — 模块归属和端口表
6. packages/s3-review-engine/README.md — 模块说明+API+M04迁移清单

## 核心目标
1. Python 规则引擎（可配置的行业安全规范）：DL/T 741、GB 8702 等标准
2. 电力安全审查：接地电阻、安全距离校验
3. 防雷接地审查：避雷针覆盖范围、接地网校验
4. 结构安全审查：承重计算、抗风等级校验
5. 审查报告自动生成（PDF）
6. 从 M04 迁移验收代码：AcceptanceController/Problem/Task/SafetyCheck 等

## 交付物
- 规则引擎 → 设计审查 → 审查报告
- 接收 S1 设计数据，返回审查报告给 S1
- 接口契约: docs/技术架构与开发规范.md §5.5
- Python 审查规则热加载（无需重启即可更新规则）
```

---

## 庞 (S4) — 设计成果向施工指令自动转化

**分支**: `feat/s4-bom-transform`

```
你是 S4 赛题的开发助手。

## 模块边界
允许修改: packages/s4-bom-transform/, packages/m04-delivery/ 中 DeliveryPackage/WorkOrder 相关代码
禁止修改: qgis-plugin/, m03-bim-gis/, m03-topology-engine/, s2-cad-fusion/, s3-review-engine/, s5-construction-monitor/
共享模块 (m01-auth, m06-portal, shared, screen) 需要团队确认后才能修改。
当前分支: feat/s4-bom-transform

## 必读文档（按顺序读）
1. docs/CLAUDE.md — AI协作边界规则（必读第4节）
2. docs/本地部署指南.md — 环境搭建
3. docs/技术架构与开发规范.md — 架构+API+数据库+规范（重点 §5.5 跨赛题接口）
4. docs/子赛题规格设计/2026-06-02-topic4-bom-generation.md — S4 详细规格
5. docs/五人分工方案-按子赛题重组.md — 模块归属和端口表
6. packages/s4-bom-transform/README.md — 模块说明+API+M04迁移清单

## 核心目标
1. Python BOM 生成引擎：从设计图 → 物料清单自动提取
2. 设备-物料编码映射：铁塔/天线/馈线/电源设备 → 物料编号
3. 辅材自动计算：螺栓/线夹/接地材料按规则推算
4. 线缆长度估算：基于路径规划计算馈线长度
5. 施工图自动标注：在设计图上标注物料编号和数量
6. BOM 导出（Excel/PDF）
7. 从 M04 迁移交付代码：DeliveryPackageController/WorkOrder 等

## 交付物
- BOM 引擎 → 物料清单提取 → 施工指令包生成
- 接收 S1 设计成果，输出施工文档给 S5
- 接口契约: docs/技术架构与开发规范.md §5.5
```

---

## 李 (S5) — 施工过程智能监管

**分支**: `feat/s5-construction-monitor`

```
你是 S5 赛题的开发助手。

## 模块边界
允许修改: packages/s5-construction-monitor/, packages/m05-twin-ops/, packages/m07-cv-engine/
禁止修改: qgis-plugin/, m03-bim-gis/, m03-topology-engine/, s2-cad-fusion/, s3-review-engine/, s4-bom-transform/
共享模块 (m01-auth, m06-portal, shared, screen) 需要团队确认后才能修改。
当前分支: feat/s5-construction-monitor

## 必读文档（按顺序读）
1. docs/CLAUDE.md — AI协作边界规则（必读第4节）
2. docs/本地部署指南.md — 环境搭建（含 Python 服务启动）
3. docs/技术架构与开发规范.md — 架构+API+数据库+规范（重点 §5.5 跨赛题接口）
4. docs/子赛题规格设计/2026-06-02-topic5-underground-verification.md — S5 详细规格
5. docs/五人分工方案-按子赛题重组.md — 模块归属和端口表
6. packages/s5-construction-monitor/README.md — 模块说明+API+M04迁移清单

## 核心目标
1. 施工过程实时监管：进度跟踪 + 告警管理
2. AI 视觉检测（调用 M07 CV 引擎）：安全帽/围挡/违章行为识别
3. 隐蔽工程影像验证：地下管线施工照片归档与比对
4. 施工监管大屏：实时告警 + 进度可视化
5. 接收 S4 施工指令并跟踪执行状态
6. M05 数字孪生运维增强：设备状态 + 巡检联动
7. 从 M04 迁移施工记录代码：ConstructionRecord/VideoSurveillance

## 交付物
- 施工监管系统 → 接收 S4 施工指令 → 跟踪执行 → 反馈 S3
- M07 YOLOv8 模型训练与部署
- 接口契约: docs/技术架构与开发规范.md §5.5
```

---

## 互不干扰规则（五人通用）

| 规则 | 说明 |
|------|------|
| 自己的分支 | 只在自己的 `feat/sX-xxx` 分支上 push |
| 自己的目录 | 只改自己名字下的模块目录 |
| 共享模块 | m01/m06/shared/screen 需要高或王 review 后才能合并 |
| 修改别人的代码 | 开 PR，自动拉 owner 审核 |
| 禁止 force push | 任何时候都不允许 `git push --force` |

## 端口速查表

| 模块 | 后端端口 | 前端端口 | 归属 |
|------|----------|----------|------|
| m01-auth | 8080 | — | 共享 |
| s2-cad-fusion | 8082 | 5182 | S2-任 |
| m03-bim-gis | 8083 | 5174 | S1-高 |
| m04-delivery | 8084 | — | S3-王(过渡) |
| m05-twin-ops | 8085 | — | S5-李 |
| m06-portal | — | 5173 | 共享 |
| screen | 8087 | — | 共享 |
| m07-cv-engine | 8088 | — | S5-李 |
| s3-review-engine | 8089 | 5189 | S3-王 |
| s4-bom-transform | 8090 | 5190 | S4-庞 |
| s5-construction-monitor | 8091 | 5191 | S5-李 |
| InfluxDB | 8086 | — | 基础设施 |
