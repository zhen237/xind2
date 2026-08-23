通信基建数智化全流程平台 全赛题需求设计文档
Challenge Cup XA-202610 Team
2026-07-14
通信基建数智化全流程平台
全赛题需求设计文档合集
赛题：挑战杯「揭榜挂帅」— XA-202610 通信基建工程数智化设计与交付关键技术
文档范围：子赛题总览分析 + S1~S5 五个子赛题的需求设计文档
编制日期：2026 年 7 月 14 日
说明：本合集由五个子赛题的需求设计文档汇编而成，涵盖项目背景目标、范围边界、现状基线、功能需求、架构交互、开发任务分解、验收标准与风险待决项。各子赛题负责人依据对应文档开展 AI 辅助开发。
子赛题总览分析 — 通信基建数智化全流程平台
版本: v1.0 统筹: 高（S1，GitHub: zhen237） 生成日期: 2026-07-14 配套文档: 2026-07-14-S1~S5-需求设计文档.md（5 份子赛题各自的开发生成基线） 状态: 草稿（待团队确认）
1. 项目定位
挑战杯”揭榜挂帅”赛题 XA-202610 通信基建工程数智化设计与交付关键技术。 目标：打通”设计 → 审查 → 施工指令 → 施工监管”全流程，形成一条从 GIS 设计到隐蔽工程验真的数字化交付链路。
5 个子赛题对应流水线的 5 个环节，由 5 人分别负责、模块独立、互不干扰。
2. 五个子赛题定位与关系
[S1 智能辅助设计]  ← S2 融合 CAD/GIS 数据喂入
       │ 设计成果(设备/拓扑/坐标)
       ▼
[S3 智能审查]       ← 基于行业标准校验安全规范
       │ 审查通过的设计
       ▼
[S4 施工指令转化]   ← 设计 → BOM 物料清单/工艺
       │ 施工指令/物料
       ▼
[S5 施工监管]       ← CV 影像验真 + 数字孪生大屏
       │ 监管结果
       └──→ 回喂 S3 复核（闭环）
3. 模块归属与负责人
共享模块（谁用谁调用，改动需团队确认）：m01-auth(8080) / m06-portal(5173) / shared / screen(8087) → 按 CODEOWNERS，共享模块由 高 + 王 双审。
4. 统一技术底座（全员约定）
5. 跨赛题接口契约（纸面定义，待联调验证）
所有跨模块数据交换只走 REST API，禁止直连他人数据库。
6. 全局待决架构问题 ⚠️
D-G1：M04 过渡模块 vs 独立子赛题模块（S3/S4/S5 共通）
原 S3/S4/S5 详细设计（topic3/4/5）把 Java API 全写在 M04 Controller（/api/m04/...，表前缀 m04_）。但 2026-07-13 分工方案已将它们重组为独立模块（s3/s4/s5），M04 仅作过渡（验收后迁移）。
建议统一口径（已写入各子赛题需求设计文档待决项）： - Java API 前缀：/api/m04/* → /api/s3|s4|s5/* - DB 表前缀：m04_* → s3_/s4_/s5_* - Python 引擎独立部署（s3 规则引擎 / s4 BOM 引擎 / m07-cv 引擎）
需统筹（高）与对应负责人确认后，各文档待决项方可关闭。
D-G2：拓扑引擎（m03-topology-engine）去留（S1 内部，见 S1 文档 D-1）
孤儿服务，与 QGIS/M03 算法三方重复，零调用。方案 A 保留并集成 / B 删除 / C 保留不集成，待高拍板。
D-G3：跨赛题联调
5 组契约（I1~I5）目前仅为纸面定义，需各模块有点东西后统一联调验证，可能需返工字段。
D-G4：运城样例数据
按约定由 AI 生成试运行数据，待各人开工后由各模块 AI 造。
7. 当前整体进度基线（实现度总览）
结论：基础设施、规范、文档、协作机制全部就绪；S1 领先，S2-S5 处于”从空骨架起步”阶段。无方向性风险，剩余均为工程量问题，且职责清晰、互不干扰。
8. 协作机制速览
分支：每人 feat/sX 分支，push 后开 PR 到 main，触发 CODEOWNERS 自动拉 owner 审核
互不干扰：只改自己模块目录；改共享模块走 PR + 双审
统一约定：见 §4，详见 docs/团队AI启动指令.md 与 docs/成员AI开发工作流.md
9. 变更记录
S1 需求设计文档 — 面向专业 GIS 平台的通信工程智能辅助设计
版本: v1.0 负责人: 高（S1，GitHub: zhen237） 开发分支: feat/s1-parametric-design 生成日期: 2026-07-14 基于: 2026-06-02-topic1-parametric-design.md（参数化设计详细设计 v1.1）、技术架构与开发规范.md、当前代码库探查结果 状态: 草稿（待负责人确认后转开发基线）
1. 背景与目标
1.1 赛题定位
子赛题 S1：面向专业 GIS 平台的通信工程智能辅助设计。 整条流水线（设计 → 审查 → 施工指令 → 施工监管）的源头：设计师在 GIS 环境中完成基站/机房/管线的参数化智能设计，产出可被 S3 审查、S4 转化的结构化设计成果。
1.2 量化指标（来自规格，交差硬约束）
1.3 目标用户
通信工程设计人员（非专业程序员），需要在 GIS 地图上快速完成合规的基站布局、覆盖分析、管线规划和图纸导出。
2. 范围
2.1 S1 负责模块（高可改，禁止他人改）
2.2 不在 S1 范围
S2（数据融合）、S3（智能审查）、S4（施工指令）、S5（施工监管）各模块
共享模块（m01-auth / m06-portal / shared / screen）：需团队确认才能改
跨赛题数据交换只走已定义的 REST API 契约，不直连他人数据库
3. 现状基线（开发起点）
以下为 2026-07-14 代码库实际探查结论，非文档宣称值。
已完成的清理（T1，本分支已提交）：删除 qgis-plugin/backend 孤儿 Java、删除 HexGridGeneratorTest 假绿测试、清理 topology-engine 死依赖。
4. 功能需求清单
4.1 参数化智能设计（核心）
FR-1 提供三套参数化模板（宏站 macro / 微站 micro / 室分 indoor），套用即生成预设设备清单与规则
FR-2 用户输入少量参数（区域、容量、场景）→ 一键生成站点布局 + 设备拓扑
FR-3 操作步骤压缩至 ≤ 5 步（选模板 → 填参数 → 一键生成 → 3D 预览 → 保存），支撑效率 ≥ 50%
4.2 覆盖分析
FR-4 基于站点参数计算 RSRP 覆盖，输出真实栅格热力图（非简化椭圆）
FR-5 覆盖缺口自动识别，驱动机房/站点补点建议
4.3 管线与拓扑
FR-6 管线敷设支持路网感知最短路径（Dijkstra/A*），接入道路矢量数据
FR-7 支持星型/树型/冗余拓扑自动设计
4.4 机房与图纸
FR-8 机房自动选址（覆盖缺口 + 供电可达 + 传输可达）+ 容量规划
FR-9 导出标准图纸：PDF / PNG / DWG / DXF（当前缺后两者）
4.5 前后端贯通
FR-10 QGIS 插件设计成果通过 REST API 推送 M03 存储并在网页三维展示
FR-11 M03 前端与 QGIS 设计场景数据同步与交互联动
5. 架构与交互设计
5.1 整体数据流
设计师在 QGIS 插件设计
   → 参数化生成（FR-1~3）
   → 覆盖/管线/拓扑计算（FR-4~7）
   → 通过 data_sync.py 推送 REST API 给 M03 存储
        ↘ M03 三维可视化（CesiumJS）
        ↘ [待决] M03 → 拓扑引擎 HTTP 调用
   → 图纸导出（FR-9）
设计成果 → S3 审查接口 / S4 转化接口（跨赛题，只走 API）
5.2 规格定义的理想链路（topic1 §二）
Java 参数校验 → Python 拓扑引擎 → 模板加载/坐标计算/设备布局/覆盖推演 → shapely/numpy → CesiumJS 3D
即 M03 后端接收参数 → 调 topology-engine 的 /generate → 结果存 DB → 前端渲染。
5.3 关键架构决策：m03-topology-engine 去留 ⚠️ 待负责人拍板
当前 topology-engine 是孤儿服务：与 QGIS 插件、M03 后端算法三方重复，且零调用。三种处理方案：
推荐 A 的理由：规格白纸黑字要求 Java→Python 链路；QGIS 插件虽最成熟但它是桌面端设计工具，不适合承担服务端高并发的生成请求；M03 作为服务端中枢，把生成逻辑下沉到 Python 引擎更贴合微服务架构，也消掉 M03 与 QGIS 的双份 hex/RSRP 重复实现。
待决项 D-1：负责人在 A/B/C 中选定后，T2 据此执行。
6. 开发任务分解
P0 — 架构债（先清，低风险可立即提交）
P1 — 核心增强
P2 — 补齐阶段 4/5（规格明确”待开始”）
建议起点：P0 → T2（决断 D-1 后）→ P1（T3/T4）→ P2。T1 已完成，下一动作取决于 D-1。
7. 验收标准
8. 风险与待决项
9. 变更记录
S2 需求设计文档 — 多源异构工程数据融合
版本: v1.0 负责人: 任（S2，GitHub: xinnnr） 开发分支: feat/s2-cad-fusion 生成日期: 2026-07-14 基于: 2026-06-02-topic2-cad-fusion.md（CAD 融合详细设计 v1.0）、技术架构与开发规范.md、当前代码库探查结果 状态: 草稿（待负责人确认后转开发基线）
1. 背景与目标
1.1 赛题定位
子赛题 S2：多源异构工程数据融合。整条流水线（设计 → 审查 → 施工指令 → 施工监管）的数据底座：将通信工程 CAD 图纸（DWG/DXF）解析为统一 GeoJSON，完成坐标系转换与 CAD+GIS 数据融合，向 S1 等上游赛题推送可用的工程底图数据。
1.2 量化指标（来自规格，交差硬约束）
1.3 目标用户
通信工程设计人员及数据工程师，需要将既有 CAD 工程图纸快速转换为可在 GIS 平台叠加分析的标准化地理数据。
2. 范围
2.1 S2 负责模块（任可改，禁止他人改）
2.2 不在 S2 范围
S1（参数化设计）、S3（智能审查）、S4（施工指令）、S5（施工监管）各模块
共享模块（m01-auth / m06-portal / shared / screen）：需团队确认才能改
跨赛题数据交换只走已定义的 REST API 契约，不直连他人数据库
MinIO/MySQL 等基础设施沿用项目既有；Python 版本统一 3.10；不使用 Docker，本地手动启动
3. 现状基线（开发起点）
以下为 2026-07-14 代码库实际探查结论，非文档宣称值。
结论：S2 是真正的绿地起点，所有业务逻辑均需从零搭建；相对 S1 已有 60%+ 实现，S2 工作量集中在”建骨架 + 建引擎”。
4. 功能需求清单
4.1 CAD 文件解析（DWG/DXF → GeoJSON）
FR-1 上传 .dwg / .dxf（AutoCAD 2010+）触发解析，输出标准 GeoJSON
FR-2 按图层命名规范识别并分离 6 类要素：建筑轮廓（Polygon）、道路中心线（LineString）、电力线路（LineString）、管井位置（Point）、地形等高线（LineString+高程）、红线范围（Polygon）
FR-3 基于 cad-layer-mapping.yml 配置做图层模式匹配与属性映射（如楼层/用途/电压等级）
4.2 坐标系转换
FR-4 支持 WGS84(EPSG:4326) / CGCS2000(EPSG:4490) / 地方坐标系三类互转
FR-5 支持七参数（平移+旋转+缩放）与四参数转换，输出统一归一到 WGS84
4.3 数据融合与冲突解决
FR-6 CAD 与已有 GIS 数据合并，统一坐标到 WGS84
FR-7 融合规则：GIS 既有数据优先；同名同位置(<5m)去重；属性冲突标记”待人工审核”；记录冲突数量
4.4 REST API（后端端口 8082）
FR-8 POST /api/s2/cad/upload 上传并触发解析
FR-9 GET /api/s2/cad/task/{id} 查询任务状态；GET /api/s2/cad/layers/{taskId} 获取图层列表
FR-10 GET /api/s2/cad/download/{taskId}/{layer} 下载图层 GeoJSON；POST /api/s2/cad/transform 自定义转换
FR-11 GET /api/s2/cad/fusion/{projectId} 预览融合结果
4.5 前后端贯通与跨赛题对接
FR-12 前端 4 页覆盖上传/任务状态/图层预览(OpenLayers)/融合管理，与后端 API 联动
FR-13 S2 → S1 推送融合后 GeoJSON：POST /api/s1/design/import-fusion-data（只走 API 契约）
5. 架构与交互设计
5.1 整体数据流
用户上传 DWG/DXF（前端 5182）
   → POST /api/s2/cad/upload（Java 8082 接收，落库 s2_cad_upload）
   → 调度 Python 解析引擎（ezdxf/libredwg）→ GeoJSON（按图层分文件）
   → pyproj 坐标系转换（CGCS2000↔WGS84↔地方系）→ s2_transform_log
   → 融合引擎：CAD+GIS 合并/去重/冲突标记 → s2_fusion_result
   → 前端 OpenLayers 预览；可下载 GeoJSON
   → S2 → S1 推送融合结果（POST /api/s1/design/import-fusion-data）
5.2 技术选型（照搬规格）
5.3 关键架构决策：解析引擎的 Java↔Python 调用方式 ⚠️ 待负责人拍板
规格推荐 Java + Python 混合：Java 管 API/文件/DB，Python 管解析与转换。落地方式有二：
推荐 A 的理由：规格明确写”Java 负责文件管理/API，Python 引擎负责解析”；ezdxf/libredwg/pyproj 在 Python 生态最成熟，避免 Java 侧重复造轮子。
待决项 D-1：负责人在 A/B 中选定后，P1 据此实现引擎调用层。
5.4 数据库设计（4 张 s2_ 表，照搬规格）
s2_cad_upload：上传记录（文件名/路径/大小/类型/状态/图层数/要素数/原坐标系/错误）
s2_cad_layer：解析后图层（图层名/要素类型/数量/GeoJSON 路径/属性元信息）
s2_transform_log：坐标转换记录（源/目标 CRS/参数/状态）
s2_fusion_result：融合结果（来源图层/结果路径/冲突数/状态）
6. 开发任务分解
P0 — 脚手架（先建，低风险可立即提交）
P1 — 核心引擎
P2 — 融合与贯通
建议起点：P0（T1→T3）→ P1（T4/T5 优先，T6/T7 紧随）→ P2（T8→T9→T10）。D-1 不阻塞 P0，但 P1 引擎实现前需先决。按项目约定，让 AI 生成样例 CAD/GeoJSON 试运行数据（运城样例缺失时）。
7. 验收标准
8. 风险与待决项
9. 变更记录
S3 需求设计文档 — 基于行业标准的设计智能审查
版本: v1.0 负责人: 王（S3，GitHub: w0722） 开发分支: feat/s3-review-engine 生成日期: 2026-07-14 基于: 2026-06-02-topic3-safety-review.md（S3 详细设计 v1.1）、技术架构与开发规范.md、当前代码库探查结果 状态: 草稿（代笔：高 / zhen237；待负责人王确认后转开发基线）
1. 背景与目标
1.1 赛题定位
子赛题 S3：基于行业标准的设计智能审查。 整条流水线（设计 → 审查 → 施工指令 → 施工监管）的第二环：接收 S1 产出的结构化设计成果，按电力/防雷/结构/电磁/通用五类行业标准做精确计算审查，输出违规清单、风险等级、3D 标注与修复建议，供 S4 转化与 S5 监管消费。
1.2 量化指标（来自规格，交差硬约束）
1.3 目标用户
通信工程设计审查人员（非专业程序员），需要一键对设计方案做全维度合规审查，并在 GIS 三维地图上直观看到违规点与整改建议。
2. 范围
2.1 S3 负责模块（王可改，禁止他人改）
2.2 不在 S3 范围
S1（设计源头）、S2（数据融合）、S4（施工指令）、S5（施工监管）各模块
共享模块（m01-auth / m06-portal / shared / screen）：需团队确认才能改
跨赛题数据交换只走已定义的 REST API 契约，不直连他人数据库
设计数据来自 S1：S3 通过 API 拉取设计成果，不反向修改 S1
3. 现状基线（开发起点）
以下为 2026-07-14 代码库实际探查结论，非文档宣称值。
环境约定：Python 版本统一 3.10；不使用 Docker，本地手动启动后端(8089)+Python(自定义端口)+前端(5189)。
4. 功能需求清单
4.1 审查规则体系（核心，5 类 25+ 条）
FR-1 电力安全 electric：ELEC-001~008（10/35/110/220kV 交越垂直距离、平行接近水平距离、变压器安全距离），含阈值与严重级
FR-2 防雷接地 lightning：LIGHT-001~005（接地电阻、接闪器保护、等电位、天馈线接地）
FR-3 结构安全 structure：STRU-001~004（风荷载、基础承载、天线高度、抱杆承重）
FR-4 电磁安全 emc：EMC-001~003（辐射限值、隔离距离、同频干扰保护比）
FR-5 通用安全 general：GEN-001~003（消防通道、防爆隔离、登高空间）
FR-6 规则库可配置（阈值/严重级存 s3_safety_rule），引擎按规则逐条执行计算
4.2 规则引擎计算
FR-7 Python 引擎输入 {designData, rules, environmentData} → 输出 {summary, violations[{rule,isPass,actual,expected,deviation,coord,suggestion}]}
FR-8 3D 坐标级违规定位（如 ELEC-001 交越点），供前端 Cesium 标注
FR-9 风险等级聚合（critical/error/warning 统计 + 审查覆盖率 + 准确率指标）
4.3 审查任务与接口
FR-10 开始审查：接收 designTaskId + scope.categories，调 Python 引擎并落库
FR-11 审查历史列表、结果详情查询（含重新审查）
FR-12 Java→Python 引擎 HTTP 调用，含超时 fallback（引擎不可用时返回降级结果）
4.4 前端审查报告
FR-13 统计卡片（规则数/通过/警告/错误）+ 违规明细表（按严重性排序）
FR-14 Cesium 3D 场景标注违规点（红/橙/黄对应 critical/error/warning）
FR-15 导出审查报告 PDF
5. 架构与交互设计
5.1 整体数据流
用户在前端选设计方案 → 点"安全审查"
   → S3 后端(8089) 通过 API 拉取 S1 设计成果 + 查 s3_safety_rule
   → S3 后端 HTTP 调 Python 引擎 /api/v1/review/check
        ↘ {designData, rules, environmentData}
   ← Python 引擎返回 {summary, violations[]}（精确计算，无人工干预）
   → S3 后端写 s3_review_task + s3_review_result（批量）
   → 前端(5189) 渲染报告：统计卡片 + 明细表 + 3D 标注 + 导出 PDF
审查结果 → S4 转化接口 / S5 监管接口（跨赛题，只走 API）
5.2 规格定义的理想链路（topic3 §四）
Vue 前端 → Java Controller → 查设计数据+规则 → Python 规则引擎 → 逐条执行 → 落库 → 报告
即后端组装输入调 Python 引擎，结果落库并返回，前端渲染。
5.3 关键架构决策：API 前缀与表前缀冲突 ⚠️ 待负责人/统筹拍板
原 topic3 规格里的 Java API 全部写在 M04 Controller 下（路径 /api/m04/review/...，DB 表 m04_safety_rule/m04_review_task/m04_review_result），但 2026-07-13 分工方案已把 S3 重组成独立模块 s3-review-engine，M04 只是过渡（验收后迁 S3）。
实际开发以独立 s3-review-engine 为准，建议调整如下：
待决项 D-1：请负责人王 / 统筹高确认「以 s3 前缀独立模块为准」是否定稿，定后 P0 直接按 s3_ 建表与接口。Python 引擎路径 /api/v1/review/check 与输入/输出契约保持不变。
6. 开发任务分解
P0 — 脚手架（先建，低风险可立即提交）
P1 — 核心增强
P2 — 补齐阶段（界面与联调）
建议起点：P0（T1→T2→T3，依赖 D-1）→ P1（T4/T5）→ P2（T6/T7/T8）。
7. 验收标准
8. 风险与待决项
9. 变更记录
S4 需求设计文档 — 设计成果向施工指令自动转化（BOM）
版本: v1.0 负责人: 庞（S4，GitHub: nosh1816） 开发分支: feat/s4-bom-transform 生成日期: 2026-07-14 基于: 2026-06-02-topic4-bom-generation.md（BOM 详细设计 v1.1）、技术架构与开发规范.md、当前代码库探查结果 状态: 草稿（待负责人确认后转开发基线）
1. 背景与目标
1.1 赛题定位
子赛题 S4：设计成果向施工指令自动转化（BOM）。 整条流水线（设计 → 审查 → 施工指令 → 施工监管）的施工指令转化环节：把 S1 产出的结构化设计成果（设备布局清单）自动映射为可施工的物料清单（主设备 + 辅材 + 线缆），并通过 Excel 导出交付施工方，将 2-4 小时的施工准备压缩到 1 分钟内。
1.2 量化指标（来自规格，交差硬约束）
1.3 目标用户
通信工程施工准备人员 / 物料采购员，需要由设计成果秒级生成准确、完整、无漏项的 BOM 清单与 Excel。
2. 范围
2.1 S4 负责模块（庞可改，禁止他人改）
2.2 不在 S4 范围
S1（参数化设计）、S2（数据融合）、S3（智能审查）、S5（施工监管）各模块
共享模块（m01-auth / m06-portal / shared / screen）：需团队确认才能改
设计数据来源（S1/S3 设备布局清单）只走已定义的 REST API 契约，不直连他人数据库
3. 现状基线（开发起点）
以下为 2026-07-14 代码库实际探查结论，非文档宣称值。
无已完成清理（P0 起步）：本节所有缺口即为 T1~T3 的实际开发内容。
4. 功能需求清单
4.1 设备-物料映射（核心）
FR-1 加载物料编码库 material_catalog.json（天线/RRU/BBU/电源/传输/铁塔等物料编码），按设备 type/model 映射到标准物料编码（如 M-ANT-001）
FR-2 输入设备清单 {name, type, model, qty, parent} → 输出主设备 BOM 明细，分类为 main_device
4.2 辅材自动计算
FR-3 每副天线配 1 套安装套件；每台 RRU 配 1 套防水套件；每站点配 1 批接地材料 + max(1, int(antenna/2)) 包标识标签
FR-4 辅材分类归为 auxiliary，自动推算消除人工漏项（漏项率 < 2%）
4.3 线缆长度估算
FR-5 射频跳线（天线→RRU）固定 3m/根；野战光纤（RRU→BBU）按水平距离 ×1.2 布线余量系数（主备双路由 qty=2）
FR-6 线缆分类归为 cable，输出单根长 / 总长，估算误差目标 < 15%
4.4 汇总与导出
FR-7 分类汇总统计（总类目/总数量、主设备/辅材/线缆分项），落库 s4_bom_task + s4_bom_item
FR-8 通过 openpyxl 导出 Excel（.xlsx，中文编码正确），支持前端下载
4.5 前后端贯通
FR-9 前端选择设计方案 → 点”生成 BOM” → 展示三类清单 + 统计概览 → 导出 Excel
FR-10 与 S1/S3 联调：通过 REST API 拉取设计设备清单作为 BOM 输入源
5. 架构与交互设计
5.1 整体数据流
用户在前端选设计方案 → 点"生成BOM"
   → Java 后端接收(designTaskId/projectId) → 查 S1/S3 设计设备清单(REST API)
   → Java HTTP 调 Python BOM 引擎 /api/v1/bom/generate
        ↘ 设备-物料映射(FR-1/2)
        ↘ 辅材自动计算(FR-3/4)
        ↘ 线缆长度估算(FR-5/6)
        ↘ 分类汇总(FR-7)
   → Python 返回 BOM JSON → Java 落库(s4_bom_task + s4_bom_item)
   → 前端展示 + 导出 Excel(openpyxl)
BOM 成果 → S5 施工监管接口（跨赛题，只走 API）
5.2 规格定义的理想链路（topic4 §三）
Vue 前端 → Java BOM Controller → Python BOM Engine → 物料编码库/辅材规则/线缆规则
→ BOM明细 + 汇总统计 → Excel 导出 → (MinIO 存储)
即 Java 负责编排与存储，Python 引擎承担生成算法，结果回写 MySQL。
5.3 关键架构决策：API 前缀与表前缀冲突 ⚠️ 待统筹确认
原 topic4 规格里 Java API 全部写在 M04 Controller 下（路径 /api/m04/bom/...，DB 表 m04_bom_task / m04_bom_item），但 2026-07-13 分工方案已把 S4 重组成独立模块 s4-bom-transform，M04 只是过渡（交付后迁 S4）。需求文档须明确：实际开发以独立 s4-bom-transform 为准，Java API 前缀建议改为 /api/s4/bom/...，DB 表前缀改为 s4_。
待决项 D-1：API 前缀与表前缀由统筹（高/庞）确认后固化为 S4 基线；M04 过渡代码不并入最终交付。
6. 开发任务分解
P0 — 脚手架与数据底座（先建）
P1 — 核心引擎与集成
P2 — 前端与联调
建议起点：P0（T1/T2）→ P1（T3/T4）→ P2（T5~T7）。T3 是最大工作量。
7. 验收标准
8. 风险与待决项
9. 变更记录
S5 需求设计文档 — 隐蔽工程影像分析与数字化验真
版本: v1.0 负责人: 李（S5，GitHub: lixiaojie-ui） 开发分支: feat/s5-construction-monitor 生成日期: 2026-07-14 基于: 2026-06-02-topic5-underground-verification.md（隐蔽工程验真详细设计 v1.1）、技术架构与开发规范.md、当前代码库探查结果 状态: 草稿（待负责人确认后转开发基线）
1. 背景与目标
1.1 赛题定位
子赛题 S5：隐蔽工程影像分析与数字化验真。 整条流水线（设计 → 审查 → 施工指令 → 施工监管）的末端：在施工监管环节，对地下管道、接地网、塔基基础、电缆沟等隐蔽工程影像做 AI 分析，输出设计-施工对比验真结果与不可篡改的数字化交付档案，并联动数字孪生大屏可视化。
1.2 量化指标（来自规格，交差硬约束）
1.3 目标用户
施工监管人员、质量验真人员，需要基于现场影像快速判定隐蔽工程是否合规，并生成可供审计存档的防篡改档案。
2. 范围
2.1 S5 负责模块（李可改，禁止他人改）
2.2 不在 S5 范围
S1（设计）、S2（数据融合）、S3（审查）、S4（施工指令）各模块
共享模块（m01-auth / m06-portal / shared）需团队确认才能改
跨赛题数据交换只走已定义的 REST API 契约：S4 提供施工指令/影像来源，S5 消费；不直连他人数据库
不使用 Docker，本地手动启动；Python 统一 3.10
3. 现状基线（开发起点）
以下为 2026-07-14 代码库实际探查结论，非文档宣称值。
起点策略：m05 作现有基础复用，s5 脚手架与 m07 引擎并行从 0 搭建，优先打通 s5→m07 的 HTTP 调用链路。
4. 功能需求清单
4.1 隐蔽工程检测场景
FR-1 支持四类检测：地下通信管道（管径/埋深/间距/材质/数量）、接地网（接地极数量/间距/焊接/防腐）、塔基/设备基础（尺寸/钢筋密度/外观）、电缆沟（线缆数量/间距/保护管/回填分层）
FR-2 影像须含参照物（标尺/卷尺/已知尺寸物体），多角度 3-5 张
4.2 影像分析管道
FR-3 预处理：高斯去噪 + 透视畸变校正 + 参照物尺度标定
FR-4 YOLOv8 目标检测：管线/标尺/接地极/焊点，输出 bbox+class+confidence
FR-5 SAM 语义分割：精确分割管线/区域，提取轮廓
FR-6 几何测量：基于参照物像素-实际比例推算管径/埋深/间距
FR-7 生成标注影像：在原始图绘制检测框 + 测量值 + 偏差标注
4.3 设计-施工对比验真
FR-8 实测值 vs 设计值偏差判定，容忍度：管径 ±5% / 埋深 ±10% / 间距 ±15%；输出 通过/偏差/不合格
4.4 防篡改数字化交付档案
FR-9 SHA256 哈希链（taskHash → resultHash → archiveHash）+ 时间戳，支持独立验证脚本
4.5 前后端贯通
FR-10 前端验真报告：概览 + 明细 + 原图/标注图对比 + 防篡改信息
FR-11 与 m05-twin-ops 大屏联动展示验真结果
5. 架构与交互设计
5.1 整体数据流
施工人员上传含参照物影像
   → S5 后端(8091) 提交验真任务(异步)
        ↘ 调 m07-cv-engine(8088) /api/v1/verify/analyze
             → 预处理 → YOLOv8 → SAM → 几何测量 → 设计对比 → 标注影像
        ↘ 结果落库(verification_task/result 含哈希)
   → S5 前端(5191) 轮询/查询 验真报告
   → 生成防篡改档案(SHA256 哈希链)
   → 推送 m05-twin-ops(8085) 大屏联动
设计参数来源：S4 施工指令(跨赛题，只走 API)
5.2 关键架构决策：模块重组与 API/DB 前缀冲突 ⚠️ 待决项
原 topic5 规格里的 Java API 全部写在 M04 Controller 下（路径 /api/m04/verification/...，DB 表 m04_verification_task/m04_verification_result），但 2026-07-13 分工方案已把 S5 重组成独立模块，M04 只是过渡；CV 引擎独立为 m07-cv-engine(8088)。
实际开发须明确以独立 s5-construction-monitor + m07-cv-engine 为准： - Java API 前缀建议改为 /api/s5/verification/...（替换原 /api/m04/...） - DB 表前缀改为 s5_（即 s5_verification_task / s5_verification_result，替换原 m04_） - Python CV 引擎 API 保持不变：/api/v1/verify/analyze、/api/v1/verify/task/{id}
待决项 D-1：上述 API/DB 前缀由统筹方确认（S5 负责人+统筹）。文档正文均按 s5_ 前缀表述，若最终维持 m04_ 需全局替换。
6. 开发任务分解
P0 — 脚手架与数据（先搭，低风险）
P1 — 核心 CV 与集成
P2 — 验真闭环与联动
建议起点：P0(T1→T2→T3) → P1(T4/T5) → P2(T6~T9)。T10 数据可并行准备。
7. 验收标准
8. 风险与待决项
9. 变更记录

[TABLE 1]
子赛题	环节	核心产出	量化硬指标
S1 智能辅助设计	源头	参数化基站/管线/机房设计	效率↑≥50%、手绘↓≥75%
S2 多源数据融合	喂入	CAD/DWG → GeoJSON 统一	坐标系转换亚米级
S3 智能审查	把关	安全规范审查报告	覆盖率≥85%、准确率≥98%
S4 施工指令转化	转化	BOM 物料清单	准备时间↓≥95%
S5 施工监管	落地	隐蔽工程验真 + 数字孪生	影像分析准确率≥90%、防篡改

[TABLE 2]
子赛题	负责人	GitHub	负责模块	后端端口	前端端口
S1	高	zhen237	qgis-plugin / m03-bim-gis / m03-topology-engine	8083	5183
S2	任	xinnnr	s2-cad-fusion	8082	5182
S3	王	w0722	s3-review-engine	8089	5189
S4	庞	nosh1816	s4-bom-transform	8090	5190
S5	李	lixiaojie-ui	s5-construction-monitor / m07-cv-engine / m05-twin-ops	8091 / 8088 / 8085	5191

[TABLE 3]
约定	内容
语言/框架	后端 Spring Boot 3.1.10 + MyBatis-Plus；前端 Vue3 + Element Plus + CesiumJS
Python 版本	统一 3.10（统筹指定）；QGIS 插件用 QGIS 自带 Python（独立）
部署	不使用 Docker，依赖本地启动或集成进自身模块
数据库	MySQL（各模块独立表前缀 s1_/s2_/s3_/s4_/s5_）；MinIO 共享文件
认证	统一走 m01-auth JWT
UI 风格	沿用 m06-portal 视觉规范（Element Plus + 设计 Token）
试运行数据	能生成的由 AI 写脚本造，不手工构造
进度同步	不强制周报/站会

[TABLE 4]
序号	源 → 目标	契约	状态
I1	S2 → S1	POST /api/s1/design/import-fusion-data 推送融合 GeoJSON	未实战
I2	S1 → S3	设计任务数据（designTaskId）触发审查	未实战
I3	S1/S3 → S4	设备布局清单 → BOM 生成	未实战
I4	S4 → S5	施工指令/物料 → 施工监管	未实战
I5	S5 → S3	监管结果回喂复核	未实战

[TABLE 5]
模块	实现度	说明
qgis-plugin (S1)	≈85%	最成熟，主链路已落地
m03-bim-gis (S1)	≈60%	有算法但模板未联动、无管线
m03-topology-engine (S1)	70%代码/0%集成	孤儿，待 D-G2 决断
s2-cad-fusion (S2)	≈5%	仅 1 个空骨架 Java，Python 引擎待建
s3-review-engine (S3)	≈5%	仅 1 个空骨架 Java，Python 规则引擎待建
s4-bom-transform (S4)	≈5%	仅 1 个空骨架 Java，Python BOM 引擎待建
s5-construction-monitor (S5)	≈5%	仅 1 个空骨架 Java
m07-cv-engine (S5)	0%	CV 引擎完全待建
m05-twin-ops (S5)	≈40%	12 个 Java，数字孪生相对成熟
m01-auth / m06-portal	可用	认证 + 门户基础就绪

[TABLE 6]
版本	日期	内容	维护人
v1.0	2026-07-14	初始子赛题总览分析，串起 5 赛题定位/关系/归属/契约/全局待决	高

[TABLE 7]
指标	官方要求	我们的目标
设计效率提升	≥ 30%	≥ 50%（操作步骤 20+ 步 → 5 步）
手动绘图减少	≥ 50%	≥ 75%（参数化替代手绘）
平台基础	开源 GIS	CesiumJS + Tianditu（M03 内已运行）

[TABLE 8]
模块	类型	角色	当前实现度（探查）
qgis-plugin/	QGIS 桌面插件（PyQGIS）	设计源头：地图上一站式设计、导出对接后端	≈ 85%，最成熟
packages/m03-bim-gis/	Spring Boot 后端 + Vue 前端	设计数据存储、三维可视化、参数化生成服务端	≈ 60%
packages/m03-topology-engine/	Python（FastAPI）	拓扑/覆盖算法引擎（规格要求被 M03 调用）	≈ 70% 代码，0% 被集成

[TABLE 9]
模块	真实情况	主要缺口
qgis-plugin	基站/覆盖/管线/BOM/导出主链路已落地；design_engine/pipeline.py 用 direct/manhattan 启发式（非路网感知）	① 管线为直线/曼哈顿，非 Dijkstra 路网感知（规格点名短板）；② 缺拓扑设计 topology.py、机房自动选址、DWG/DXF 导出
m03-bim-gis	DesignService 有真实算法但模板未联动 /generate（用硬编码默认值）；前端 3D 真实但覆盖热力图为简化椭圆	① /generate 不消费模板；② 覆盖热力图为简化；③ 与拓扑引擎算法三方重复
m03-topology-engine	/api/v1/design/generate 返回站点+完整设备拓扑，算法与 QGIS、M03 后端三方重复	零调用：规格 §3.1 要求 M03 HTTP 调用它，但从未接通；requirements.txt 含死依赖 numpy（未 import）且 pydantic 版本在 PyPI 不存在

[TABLE 10]
方案	做法	优点	缺点	工作量
A. 保留并集成（推荐）	M03 DesignService 改为 HTTP 调拓扑引擎 /generate，删除 M03 内部重复算法，加超时/fallback	落地规格 §3.1；消除 M03 侧重复；算法集中可维护	需扩展 Java 实体存设备拓扑；联调成本	中
B. 删除孤儿服务	直接删 m03-topology-engine，QGIS 作唯一设计引擎，推送结果给 M03	最快消除重复；算法增强只在 QGIS 侧	偏离规格 §3.1 写的 Java→Python 链路；评委可能质疑	小
C. 保留暂不集成	先留着不调，转做 T4 模板联动	最快出可见成果	重复债延后；最终仍要决断	—

[TABLE 11]
任务	内容	状态
T1 清理孤儿/重复代码	删 qgis-plugin/backend 孤儿 Java、假绿测试、topology-engine 死依赖	✅ 已完成
T2 打通 M03→Python 拓扑引擎调用	重构 DesignService 为 HTTP 调 /generate，删 M03 重复算法，加超时 fallback（依赖 D-1）	⏸ 待 D-1

[TABLE 12]
任务	内容
T3 管线 Dijkstra/A* 路网感知	升级 pipeline.py，接入道路矢量，消除规格点名短板（效率量化关键）
T4 参数化模板联动 generate 端点	M03 /generate 真正消费 m03_parametric_template（macro/micro/indoor），非硬编码默认值

[TABLE 13]
任务	内容
T5 拓扑设计 topology.py	星型/树型/冗余自动设计
T6 机房自动选址 + 容量规划	覆盖缺口/供电/传输可达驱动
T7 DWG/DXF 图纸导出	补齐 metadata 宣称但未实现的能力
T8 M03 前端真实覆盖热力图 + 3D 联动	替换简化椭圆；强化 QGIS↔3D 同步

[TABLE 14]
编号	功能	Given	When	Then
AC-1	参数化生成	用户选 macro 模板填区域参数	点一键生成	≤5 步产出站点+设备拓扑，效率较基线 ≥50%
AC-2	模板联动	存在 m03_parametric_template 预设	调 /generate	返回结果含模板定义设备清单，非硬编码默认
AC-3	管线路网感知	加载道路矢量	生成管线	路径为路网最短路径（Dijkstra/A*），非直线
AC-4	覆盖热力图	站点参数确定	前端渲染	显示真实 RSRP 栅格，识别覆盖缺口
AC-5	图纸导出	设计完成	导出 DWG/DXF	生成标准格式文件可被 CAD 打开
AC-6	引擎集成（若选 A）	M03 收到生成请求	调拓扑引擎	返回设备拓扑并落库，引擎超时时有 fallback

[TABLE 15]
编号	项	影响	处置
D-1	topology-engine 去留（§5.3）	决定 T2 方向	需负责人拍板
R-1	S2-S5 后端为空壳，跨赛题联调未实战	接口契约可能需返工	各赛题有点东西后统一联调
R-2	运城样例数据缺失	无法演示真实场景	按约定由 AI 生成试运行数据
R-3	本地启动（不用 Docker），各人环境独立	联调需约定端口/地址	端口速查表已固化

[TABLE 16]
版本	日期	内容	维护人
v1.0	2026-07-14	初始需求设计文档，固化 S1 范围/现状/需求/架构决策/任务分解	高

[TABLE 17]
指标	官方要求	我们的目标
CAD 解析覆盖	DWG/DXF 格式	支持 AutoCAD 2010+ 各版本
坐标系转换精度	米级	亚米级（CGCS2000↔WGS84↔地方坐标系）
数据统一格式	GeoJSON	标准 GeoJSON，含属性映射
多源融合类型	CAD+GIS	建筑轮廓/道路/电力线/管井/等高线/红线

[TABLE 18]
模块	类型	角色	当前实现度（探查）
packages/s2-cad-fusion/	Spring Boot 后端（端口 8082）	文件管理/解析调度/REST API/融合	仅 1 个 Application.java 空骨架
packages/s2-cad-fusion/frontend/	Vue 3 前端（端口 5182）	上传/状态/图层预览/融合管理 4 页	空壳目录，无页面
Python 解析引擎	ezdxf + libredwg + pyproj	CAD 解析/坐标系转换（规格要求）	代码为零，待建，无 requirements.txt

[TABLE 19]
模块	真实情况	主要缺口
后端 s2-cad-fusion	仅 Application.java 空骨架，无任何 Controller/Service/Mapper	① 无上传 API；② 无建表；③ 无解析调度逻辑
前端 frontend	目录存在但为空壳，无 Vue 页面与路由	4 个页面（上传/状态/预览/融合）全部待建
Python 解析引擎	目录/代码均不存在，requirements.txt 缺失	① DXF 解析（ezdxf）；② DWG 解析（libredwg/ODA）；③ 坐标系转换（pyproj）全部为零
DB	无 s2_ 前缀任何表	需新建 s2_cad_upload / s2_cad_layer / s2_transform_log / s2_fusion_result

[TABLE 20]
层级	技术	说明
后端框架	Spring Boot 3.1.10	与 M0x 模块统一，端口 8082
CAD 解析引擎	Python 3.10（ezdxf + libredwg）	解析，需补 requirements.txt
坐标系转换	pyproj（Python）/ proj4j（Java 备选）	全部 EPSG 定义
文件存储	MinIO	沿用既有基础设施
数据库	MySQL（comm_platform）	s2_ 表前缀
前端	Vue 3 + Element Plus	端口 5182，与 M06 统一

[TABLE 21]
方案	做法	优点	缺点
A. 进程间调用（推荐）	Java 通过 HTTP（FastAPI/Flask）或 CLI 调 Python 引擎	解析与算法下沉 Python，职责清晰；贴合规格”混合”写法	需约定进程启动/超时/错误回传
B. Java 原生解析	Java 用 aspose-cad / LibreDWG JNI 直解	单进程部署简单	偏离规格”Python 引擎”约定；DWG 原生库授权/成熟度风险

[TABLE 22]
任务	内容	状态
T1 Spring Boot 脚手架	建 s2-cad-fusion 模块，端口 8082，打通启动	⏸ 待开始
T2 文件上传 API	POST /api/s2/cad/upload + 落库 s2_cad_upload	⏸ 待开始
T3 建表	4 张 s2_ 表 DDL（upload/layer/transform_log/fusion_result）	⏸ 待开始

[TABLE 23]
任务	内容
T4 DXF 解析引擎	Python 3.10 + ezdxf，按 FR-2/FR-3 提取 6 类要素并做属性映射（依赖 D-1 调用方式）
T5 坐标系转换	Python pyproj 实现 CGCS2000↔WGS84↔地方系七/四参数（FR-4/FR-5）
T6 DWG 解析	libredwg/ODA 解析 DWG + 图层识别/属性映射（FR-1/FR-2 补全）
T7 其余 REST API	task/layers/download/transform/fusion 端点（FR-9~FR-11）

[TABLE 24]
任务	内容
T8 数据融合引擎	CAD+GIS 合并/去重/冲突标记，落 s2_fusion_result（FR-6/FR-7）
T9 前端 4 页	上传/任务状态/图层预览(OpenLayers)/融合管理，联调后端
T10 S2→S1 联调	推送融合 GeoJSON 给 S1（FR-13），统一接口契约

[TABLE 25]
编号	功能	Given	When	Then
AC-1	文件上传	用户持 DWG/DXF	POST /upload	落库 s2_cad_upload 且状态流转至完成/失败
AC-2	DXF 解析	上传 .dxf	解析引擎执行	输出 6 类要素 GeoJSON，图层与属性按映射配置提取
AC-3	DWG 解析	上传 .dwg（2010+）	解析引擎执行	同样产出标准 GeoJSON 图层
AC-4	坐标系转换	输入 CGCS2000 坐标	调 transform	输出 WGS84 亚米级一致；地方系互转可用
AC-5	图层查询/下载	解析完成	GET layers/download	返回图层列表并可下载对应 GeoJSON
AC-6	数据融合	有 CAD 与 GIS 同名同位置要素	触发融合	去重/冲突标记，s2_fusion_result 记录冲突数
AC-7	前端预览	解析完成	打开预览页	OpenLayers 正确渲染图层几何与属性
AC-8	S2→S1 推送	融合完成	POST /api/s1/design/import-fusion-data	S1 收到标准 GeoJSON 并落库可展示

[TABLE 26]
编号	项	影响	处置
D-1	解析引擎 Java↔Python 调用方式（§5.3）	决定 P1 引擎落地	需负责人拍板
R-1	S2 后端/前端/Python 引擎全为空壳	工作量集中且联调无实战对象	P0 先出骨架，各赛题有点东西后统一联调
R-2	DWG 原生解析依赖 libredwg/ODA 授权与本地环境	可能阻塞 T6	优先 DXF(ezdxf) 跑通，DWG 作后续；评估 ODA 免费 converter
R-3	Python 3.10 环境未在本机固化、无 requirements.txt	引擎无法本地运行	建 requirements.txt 并约定 3.10
R-4	运城样例 CAD 数据缺失	无法演示真实场景	按约定由 AI 生成试运行样例数据

[TABLE 27]
版本	日期	内容	维护人
v1.0	2026-07-14	初始需求设计文档，固化 S2 范围/空骨架现状/需求/架构决策/任务分解	高（代笔，zhen237）

[TABLE 28]
指标	官方要求	我们的目标
审查维度	覆盖安全规范等	≥5 类（电力/防雷/结构/电磁/通用）
审查覆盖率	≥ 80%	≥ 85%
关键风险识别准确率	≥ 95%	≥ 98%（规则引擎精确计算）
审查方式	可计算逻辑	Python 规则引擎，无需人工干预

[TABLE 29]
模块	类型	角色	端口	当前实现度（探查）
packages/s3-review-engine/	Spring Boot 后端	审查任务 API、规则库、调 Python 引擎、持久化	8089	空骨架：仅 1 个 Application.java
packages/s3-review-engine/（Python）	FastAPI 规则引擎	5 类规则精确计算，输出违规/风险/3D 标注	—	代码为零（无 requirements.txt、无 .py）
packages/s3-review-engine/frontend/	Vue 前端	审查报告（统计卡片+明细表+3D 标注+导出 PDF）	5189	空壳目录

[TABLE 30]
模块	真实情况	主要缺口
s3-review-engine 后端	仅 Application.java 空骨架，无任何 Controller/Service/Entity/表	脚手架、规则库表（s3_ 前缀）、审查任务 API 全待建
Python 规则引擎	代码为零，无 requirements.txt、无 .py	25+ 条规则、计算内核、FastAPI 服务全待建（Python 统一 3.10）
s3-review-engine 前端	目录存在但空壳	审查报告界面、3D 标注、PDF 导出全待建

[TABLE 31]
项	原规格（M04，待废弃）	S3 实际建议
Java API 前缀	/api/m04/review/...	/api/s3/review/...
DB 表前缀	m04_safety_rule 等	s3_safety_rule / s3_review_task / s3_review_result

[TABLE 32]
任务	内容	状态
T1 Spring Boot 脚手架	s3-review-engine 后端可启动(8089)，引入 Web/JPA/MySQL	⏸ 待建
T2 规则库表 + 任务/结果表	按 s3_ 前缀建 s3_safety_rule/s3_review_task/s3_review_result，预置 25+ 条规则	⏸ 待 D-1
T3 审查任务 API 骨架	开始审查 / 历史 / 结果详情（契约见 §5.3）	⏸ 待建

[TABLE 33]
任务	内容
T4 Python 规则引擎（FastAPI, 3.10）	先落地 ELEC/LIGHT 高频规则，再补 STRU/EMC/GEN；实现 /api/v1/review/check
T5 Java→Python HTTP 调用 + 超时 fallback	后端组输入调引擎，引擎不可用时降级返回

[TABLE 34]
任务	内容
T6 前端审查报告	统计卡片 + 违规明细表 + 导出 PDF(5189)
T7 3D 标注	Cesium 渲染违规点（红/橙/黄）
T8 与 S1 联调	拉取设计数据跑通端到端审查；AI 生成测试用例（正常/故意违规/边界值）

[TABLE 35]
编号	功能	Given	When	Then
AC-1	开始审查	存在 S1 设计成果 + s3_safety_rule 预置规则	调 /api/s3/review/check	返回 taskId+summary(覆盖率≥85%)，结果落 s3_review_task/result
AC-2	规则执行	输入含 ELEC-001 交越 1.2m < 2.0m	Python 引擎计算	检出 critical 违规，actual=1.2/expected=2.0/deviation=-0.8+coord
AC-3	覆盖率	五类规则全预置(≥25条)	跑测试集	审查覆盖率 ≥ 85%
AC-4	准确率	100 个已知违规 Ground Truth	引擎审查对比	关键风险识别准确率 ≥ 98%
AC-5	引擎降级	Python 引擎不可达	后端调引擎超时	返回 fallback 结果，不阻塞任务落库
AC-6	结果查询	已完成审查任务	调历史/详情 API	返回该任务全部违规明细与统计
AC-7	报告界面	审查完成	前端渲染	显示统计卡片+明细表+3D 标注，可导出 PDF

[TABLE 36]
编号	项	影响	处置
D-1	API/表前缀冲突（§5.3）：M04 过渡 vs s3 独立模块	决定 T2/T3 建表与接口命名	需负责人王 / 统筹高拍板
R-1	后端/Python/前端均为空壳，跨赛题联调未实战	接口契约可能需返工	S1 出成果后统一联调
R-2	Python 引擎精确计算依赖设计数据几何质量	几何缺失导致漏检	测试集覆盖边界值，落 coverageRate 指标
R-3	本地手动启动（不用 Docker），三方端口独立	联调需约定地址/端口	端口速查表：后端 8089 / 前端 5189 / Python 待定

[TABLE 37]
版本	日期	内容	维护人
v1.0	2026-07-14	初始需求设计文档，固化 S3 范围/现状/需求/架构冲突待决项/任务分解（代笔：高）	王

[TABLE 38]
指标	官方要求	我们的目标
施工准备时间缩短	≥ 50%	≥ 95%（2-4 小时 → 1 分钟内）
产出物	BOM 等施工指令	BOM 物料清单（主设备 + 辅材 + 线缆）
设计-施工链路	打通	设计模型 → 物料映射 → BOM 导出 全自动
线缆估算误差	—	估算值 vs 实际布线 < 15%

[TABLE 39]
模块	类型	角色	当前实现度（探查）
packages/s4-bom-transform/	Spring Boot 后端（端口 8090）	BOM 任务编排、存储、对外 API	空骨架：仅 1 个 Application.java，无业务代码
packages/s4-bom-transform/（Python 引擎）	FastAPI（Python 3.10）	BOM 生成核心：映射 / 辅材 / 线缆估算 / Excel	代码为零：无 requirements.txt、无 .py，待建
packages/s4-bom-transform/frontend/	Vue 前端（端口 5190）	BOM 清单展示、统计、导出	目录存在但空壳

[TABLE 40]
模块	真实情况	主要缺口
s4-bom-transform 后端	仅 Application.java 空骨架，Spring Boot 启动类无业务 Controller/Service	① 无 BOM 任务 API；② 无物料编码库表（应为 s4_ 前缀）；③ 无 Java→Python 引擎调用层
Python BOM 引擎	零代码：无 requirements.txt、无 .py 文件	① 设备-物料映射；② 辅材自动计算；③ 线缆长度估算；④ openpyxl Excel 导出；⑤ /api/v1/bom/generate 全未建
前端	目录存在但空壳	① BOM 三类清单表格；② 统计概览；③ 导出按钮；④ 与后端联调

[TABLE 41]
项	原规格(topic4)	建议(本需求)	处置
Java API 前缀	/api/m04/bom/...	/api/s4/bom/...	按本需求落地，M04 仅过渡
DB 表前缀	m04_bom_task / m04_bom_item	s4_bom_task / s4_bom_item	按本需求落地
模块归属	M04 Controller（过渡）	s4-bom-transform（独立）	交付后迁 S4

[TABLE 42]
任务	内容	状态
T1 Spring Boot 脚手架	packages/s4-bom-transform/ 后端骨架 + BOM 任务 API 框架（端口 8090）	⏸ 待开始
T2 物料编码库表	建 s4_bom_task + s4_bom_item，初始化 material_catalog.json（天线/RRU/BBU/电源/传输/铁塔）	⏸ 待开始

[TABLE 43]
任务	内容
T3 Python BOM 引擎	FastAPI(Py3.10)：设备-物料映射 + 辅材推算 + 线缆估算 + openpyxl 导出，/api/v1/bom/generate
T4 Java→Python 引擎调用	后端 HTTP 调引擎，加超时 fallback（引擎不可达时返回降级 BOM 或明确错误）

[TABLE 44]
任务	内容
T5 前端 BOM 界面	Vue(端口 5190)：三类清单 + 统计概览 + 导出按钮
T6 与 S1/S3 联调	通过 REST API 拉取设计设备清单作为 BOM 输入源
T7 AI 生成样例设备清单	按运城场景生成试运行设备清单数据驱动演示

[TABLE 45]
编号	功能	Given	When	Then
AC-1	生成BOM	输入含天线的设备清单 + projectId	调 /api/s4/bom/generate	1 分钟内返回 BOM（主设备+辅材+线缆），施工准备时间较人工 ≥95% 缩短
AC-2	设备-物料映射	material_catalog 含 M-ANT-001 等	调引擎生成	每台设备映射到正确物料编码，category 标记 main_device
AC-3	辅材自动计算	已知天线/RRU/站点数量	调引擎生成	安装套件/防水套件/接地材料/标签按 FR-3 规则推算，无漏项
AC-4	线缆估算	设备含天线与 RRU，含坐标	调引擎生成	射频跳线=3m/根，光纤=水平距×1.2，输出单根/总长
AC-5	Excel导出	BOM 已生成	点”导出”	openpyxl 生成 .xlsx，中文编码正确，可下载
AC-6	引擎集成	Java 收到生成请求	调 Python 引擎	返回 BOM 并落库 s4_bom_task/s4_bom_item；引擎超时有 fallback
AC-7	前端展示	BOM 已生成	前端打开	三类清单 + 统计概览正确渲染，导出按钮可用
AC-8	跨赛题联调	S1/S3 提供设计设备清单 API	S4 拉取并生成	端到端 BOM 自动生成成功，链路贯通

[TABLE 46]
编号	项	影响	处置
D-1	API/表前缀冲突（§5.3）：M04 还是 s4_	决定 T1/T2 命名基线	需统筹(高/庞)确认
R-1	Python 引擎完全从零，工作量最大	进度风险	P1 优先 T3，AI 样例数据先行
R-2	S1/S3 设计数据接口契约未实战	BOM 输入源不稳定	各赛题有点东西后统一联调（T6）
R-3	本地启动（不用 Docker），环境独立	端口/地址需约定	后端 8090 / 前端 5190 已固化
R-4	线缆估算依赖坐标，误差 <15% 验证难	验收挑战	多组样例对比（topic4 §8.2）

[TABLE 47]
版本	日期	内容	维护人
v1.0	2026-07-14	初始需求设计文档，固化 S4 范围/现状/需求/架构冲突/任务分解	高（代笔）

[TABLE 48]
指标	官方要求	我们的目标
影像结构化分析准确率	≥ 90%	≥ 90%（管径/埋深/计数/材质/回填）
数字化交付档案	不可篡改	SHA256 哈希链 + 时间戳
竣工与实景一致性	可追溯	设计-施工-检测 三方数据对齐

[TABLE 49]
模块	类型	端口	角色	当前实现度（探查）
packages/s5-construction-monitor/	Spring Boot 后端 + Vue 前端	后端 8091 / 前端 5191	施工监管主模块：任务提交、查询、档案、前端报告	≈ 5%，仅 1 个 Application.java 空骨架
packages/m07-cv-engine/	Python（FastAPI，3.10）	后端 8088	CV 影像分析引擎：YOLOv8/SAM 检测分割、几何测量、设计对比	0 个 Java 且无 Python，CV 引擎待建
packages/m05-twin-ops/	Spring Boot（Java）	后端 8085	数字孪生大屏：已 12 个 Java 文件，相对成熟，S5 现有基础	≈ 70%，较成熟

[TABLE 50]
模块	真实情况	主要缺口
s5-construction-monitor	后端只有 1 个 Application.java 空骨架；前端 frontend/ 目录存在但空壳	① 验真任务表、异步任务 API、前端报告界面全缺；② 需从 0 搭脚手架
m07-cv-engine	find 未发现任何 .java 或 .py，CV 引擎完全待建	① YOLOv8/SAM 环境；② 管径测量/几何测量算法；③ 设计对比验真；④ Python API
m05-twin-ops	12 个 Java 文件，数字孪生大屏相对成熟	① 需与 S5 验真结果联动（数据口径对接）

[TABLE 51]
任务	内容	状态
T1 s5-construction-monitor 脚手架	建 8091 后端 + 5191 前端工程，Application 接好配置	⏸ 待开始
T2 验真任务表(s5_ 前缀)	建 s5_verification_task + s5_verification_result（含哈希字段）	⏸ 待 D-1
T3 异步任务 API	提交验真任务(异步)、查询结果、生成档案，三个 Java 端点	⏸ 待 T1/T2

[TABLE 52]
任务	内容
T4 m07-cv-engine 搭建	Python3.10 + FastAPI；YOLOv8/SAM 环境；管径测量算法；设计对比验真
T5 Java→Python HTTP 调用	s5 后端调 m07 /api/v1/verify/analyze，加超时与 fallback

[TABLE 53]
任务	内容
T6 防篡改哈希链	taskHash→resultHash→archiveHash + 独立验证脚本
T7 前端验真报告界面	概览+明细+原图/标注图对比+防篡改信息(5191)
T8 大屏联动	验真结果推送 m05-twin-ops(8085)
T9 跨赛题联调	与 S4(施工指令来源)对接设计参数与影像来源
T10 AI 样例数据	生成含参照物的模拟影像（不可用真实涉密数据）

[TABLE 54]
编号	功能	Given	When	Then
AC-1	任务提交	含参照物影像+设计参数	POST 验真任务	返回 taskId/status=analyzing（异步）
AC-2	CV 分析	m07 收到 analyze 请求	执行管道	输出 bbox+测量值+偏差+标注影像，综合准确率 ≥90%
AC-3	结果查询	任务完成	GET 结果	返回逐项实测/设计/偏差/isPass/置信度
AC-4	偏差判定	实测 vs 设计	比对	按容忍度判定 通过/偏差/不合格(管径±5%/埋深±10%/间距±15%)
AC-5	防篡改档案	验真完成	生成档案	含 SHA256 哈希链+时间戳，独立脚本验证完整
AC-6	引擎调用	s5 调 m07	HTTP 请求	正常返回；m07 超时/异常时 s5 有 fallback
AC-7	前端报告	结果就绪	打开报告页	显示概览+明细+原图/标注图对比+防篡改信息
AC-8	大屏联动	验真完成	推送 m05	大屏(8085)展示该验真结果

[TABLE 55]
编号	项	影响	处置
D-1	API/DB 前缀冲突（§5.2）：s5_ vs m04_	决定 T2/T3 命名与全局替换	需统筹确认
R-1	m07-cv-engine 从 0 建，依赖 YOLOv8/SAM 模型与算力	进度与准确率风险	先用公开预训练+模拟数据验证管道
R-2	S4 后端为空壳，设计参数来源未实战	联调契约可能返工	各赛题有点东西后 T9 统一联调
R-3	真实隐蔽工程影像涉密，不可用	缺 Ground Truth	T10 用 AI 生成含参照物模拟图
R-4	本地手动启动(不用 Docker)、各人环境独立	联调需约定端口	端口速查表：s5=8091/5191, m07=8088, m05=8085

[TABLE 56]
版本	日期	内容	维护人
v1.0	2026-07-14	初始需求设计文档，固化 S5 三模块职责/现状/需求/架构冲突(D-1)/任务分解	高（代笔）