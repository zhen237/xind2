# 文档索引

**版本**: 1.0  
**最后更新**: 2026-07-02  
**文档用途**: 快速定位项目文档，平均查找时间 ≤ 30秒

---

## 变更记录

| 版本 | 日期 | 更新内容 | 维护人 |
|------|------|----------|--------|
| v1.0 | 2026-07-02 | 初始版本，创建双维度索引 | 人A |

---

## 一、按角色查找

### 1.1 新加入成员
| 阅读顺序 | 文档 | 目的 |
|----------|------|------|
| 1 | [PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md) | 快速了解项目全貌 |
| 2 | [烽火通信-子赛题1345开发方案.md](烽火通信-子赛题1345开发方案.md) | 决策汇总、架构设计 |
| 3 | [开发规范.md](开发规范.md) | 代码规范、命名约定 |
| 4 | [本地部署指南.md](本地部署指南.md) | 环境搭建、启动步骤 |

### 1.2 后端开发人员（人C/人D）
| 主题 | 文档 | 重点内容 |
|------|------|----------|
| API定义 | [API接口文档.md](API接口文档.md) | M01-M05所有接口 |
| 数据库设计 | [数据库设计.md](数据库设计.md) | 表结构、字段定义 |
| 开发规范 | [开发规范.md](开发规范.md) | Java命名、Controller结构 |
| 环境版本 | [环境依赖版本.md](环境依赖版本.md) | JDK17、Spring Boot版本 |

### 1.3 前端开发人员（人E）
| 主题 | 文档 | 重点内容 |
|------|------|----------|
| 前端设计 | [前端设计.md](前端设计.md) | Vue3组件、页面结构 |
| API定义 | [API接口文档.md](API接口文档.md) | 接口路径、请求响应格式 |
| 开发规范 | [开发规范.md](开发规范.md) | Vue命名、组件结构 |
| 部署指南 | [本地部署指南.md](本地部署指南.md) | npm安装、启动命令 |

### 1.4 AI/CV开发人员（人D）
| 主题 | 文档 | 重点内容 |
|------|------|----------|
| 子赛题规格 | [子赛题规格设计/2026-06-02-topic5-underground-verification.md](子赛题规格设计/2026-06-02-topic5-underground-verification.md) | CV引擎设计 |
| API定义 | [API接口文档.md](API接口文档.md) | M07接口定义 |
| 环境版本 | [环境依赖版本.md](环境依赖版本.md) | Python版本、YOLOv8 |

### 1.5 QGIS插件开发人员（人A/人B）
| 主题 | 文档 | 重点内容 |
|------|------|----------|
| 使用指南 | [qgis-plugin/docs/usage-guide.md](../qgis-plugin/docs/usage-guide.md) | 插件功能、操作流程 |
| 子赛题规格 | [子赛题规格设计/2026-06-02-topic1-parametric-design.md](子赛题规格设计/2026-06-02-topic1-parametric-design.md) | 参数化设计详细规格 |
| 子赛题规格 | [子赛题规格设计/2026-06-02-topic4-bom-generation.md](子赛题规格设计/2026-06-02-topic4-bom-generation.md) | BOM生成详细规格 |
| API定义 | [API接口文档.md](API接口文档.md) | M03/M04接口 |

### 1.6 评委/导师
| 阅读顺序 | 文档 | 目的 |
|----------|------|------|
| 1 | [PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md) | 项目总览 |
| 2 | [烽火通信-子赛题1345开发方案.md](烽火通信-子赛题1345开发方案.md) | 决策汇总、评分标准 |
| 3 | [实施计划.md](实施计划.md) | 开发进度、里程碑 |

---

## 二、按主题查找

### 2.1 项目概览
| 文档 | 说明 |
|------|------|
| [PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md) | 项目总概括（AI理解入口） |
| [AI-TOOL-CONTEXT.md](AI-TOOL-CONTEXT.md) | AI工具问题识别辅助文档 |
| [烽火通信-子赛题1345开发方案.md](烽火通信-子赛题1345开发方案.md) | 权威主文档 |

### 2.2 架构设计
| 文档 | 说明 |
|------|------|
| [架构设计规范.md](架构设计规范.md) | 系统架构图、技术选型、集成方案 |
| [子赛题规格设计/2026-06-02-architecture-design.md](子赛题规格设计/2026-06-02-architecture-design.md) | 详细架构设计 |

### 2.3 API接口
| 文档 | 说明 |
|------|------|
| [API接口文档.md](API接口文档.md) | M01-M05完整API定义 |

### 2.4 数据库设计
| 文档 | 说明 |
|------|------|
| [数据库设计.md](数据库设计.md) | 全模块表结构设计 |
| [scripts/init-mysql.sql](../scripts/init-mysql.sql) | MySQL建表脚本（含测试数据） |
| [scripts/init-postgis.sql](../scripts/init-postgis.sql) | PostGIS建表脚本 |

### 2.5 开发规范
| 文档 | 说明 |
|------|------|
| [开发规范.md](开发规范.md) | Java/Vue/Python代码规范（含文档命名规范） |

### 2.6 部署与环境
| 文档 | 说明 |
|------|------|
| [本地部署指南.md](本地部署指南.md) | 环境要求、启动步骤 |
| [环境依赖版本.md](环境依赖版本.md) | 各组件版本范围 |

### 2.7 子赛题规格
| 文档 | 子赛题 | 内容 |
|------|--------|------|
| [子赛题规格设计/2026-06-02-topic1-parametric-design.md](子赛题规格设计/2026-06-02-topic1-parametric-design.md) | 子赛题1 | 参数化智能辅助设计 |
| [子赛题规格设计/2026-06-02-topic3-safety-review.md](子赛题规格设计/2026-06-02-topic3-safety-review.md) | 子赛题3 | 安全规范审查 |
| [子赛题规格设计/2026-06-02-topic4-bom-generation.md](子赛题规格设计/2026-06-02-topic4-bom-generation.md) | 子赛题4 | BOM物料提取 |
| [子赛题规格设计/2026-06-02-topic5-underground-verification.md](子赛题规格设计/2026-06-02-topic5-underground-verification.md) | 子赛题5 | 隐蔽工程影像分析 |

### 2.8 实施计划
| 文档 | 说明 |
|------|------|
| [实施计划.md](实施计划.md) | 41个Task的逐步执行手册 |

### 2.9 QGIS插件
| 文档 | 说明 |
|------|------|
| [qgis-plugin/docs/usage-guide.md](../qgis-plugin/docs/usage-guide.md) | 使用指南（含答辩演示） |

---

## 三、关键词快速定位

| 关键词 | 相关文档 |
|--------|----------|
| 基站设计、QGIS | [usage-guide.md](../qgis-plugin/docs/usage-guide.md), [topic1-parametric-design.md](子赛题规格设计/2026-06-02-topic1-parametric-design.md) |
| 覆盖分析、Okumura-Hata | [topic1-parametric-design.md](子赛题规格设计/2026-06-02-topic1-parametric-design.md) |
| 智能审查、安全规范 | [topic3-safety-review.md](子赛题规格设计/2026-06-02-topic3-safety-review.md) |
| BOM、物料清单 | [topic4-bom-generation.md](子赛题规格设计/2026-06-02-topic4-bom-generation.md) |
| CV、视觉检测、YOLOv8 | [topic5-underground-verification.md](子赛题规格设计/2026-06-02-topic5-underground-verification.md) |
| 3D可视化、Cesium | [前端设计.md](前端设计.md), [架构设计规范.md](架构设计规范.md) |
| 告警、运维、巡检 | [API接口文档.md](API接口文档.md), [数据库设计.md](数据库设计.md) |
| 验收、工单、流程 | [API接口文档.md](API接口文档.md), [数据库设计.md](数据库设计.md) |
| 认证、JWT、权限 | [API接口文档.md](API接口文档.md), [开发规范.md](开发规范.md) |

---

## 四、文档目录结构

```
docs/
├── INDEX.md                    ← 本文件（索引）
├── PROJECT-OVERVIEW.md         ← 项目总概括
├── AI-TOOL-CONTEXT.md          ← AI工具问题识别辅助文档
├── TASK-PRIORITY.md            ← 任务优先级管理规范
├── DOC-REVIEW-MECHANISM.md     ← 文档定期复查机制
├── 烽火通信-子赛题1345开发方案.md    ← 权威主文档
├── API接口文档.md               ← API定义
├── 数据库设计.md                 ← 表结构
├── 开发规范.md                   ← 代码规范（含文档命名规范）
├── 前端设计.md                   ← Vue设计
├── 架构设计规范.md                ← 系统架构
├── 本地部署指南.md                ← 部署步骤
├── 环境依赖版本.md                ← 版本范围
├── 实施计划.md                   ← 开发计划
├── 子赛题规格设计/               ← 各子赛题详细规格
│   ├── 2026-06-02-architecture-design.md
│   ├── 2026-06-02-topic1-parametric-design.md
│   ├── 2026-06-02-topic3-safety-review.md
│   ├── 2026-06-02-topic4-bom-generation.md
│   └── 2026-06-02-topic5-underground-verification.md
└── diagrams/                   ← 架构图资源
    └── 示例架构图.drawio
```

---

**文档结束** — 快速查找：先看「按角色查找」定位你需要的文档类型，再看「关键词快速定位」找到具体文档。
