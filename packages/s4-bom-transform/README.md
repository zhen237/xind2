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
- **Excel 导出**：三 Sheet（BOM 物料清单 / 关键工序工艺 / 纤芯分配表），支持整改标记列
- **安全加固**：taskId 白名单校验（防路径穿越）、127.0.0.1 监听、CORS 白名单

## 目录结构

```
packages/s4-bom-transform/
├── backend/      # Java Spring Boot 后端（MyBatis-Plus，表前缀 s4_）
├── dev-proxy/    # 开发代理（模拟 S1/S3/S5 接口 + 统一入口，端口 8090）
├── engine/       # Python FastAPI BOM 引擎（端口 8100）
│   └── data/material_catalog.json   # 物料编码库
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

## API 约定

```
POST /api/s4/bom/generate            # 从设计成果生成 BOM（designTaskId 必填）
GET  /api/s4/bom/{taskId}/status     # 查询任务状态
GET  /api/s4/bom/{taskId}/full       # 查询完整 BOM 结果
GET  /api/s4/bom/{taskId}/export     # 导出 Excel（三 Sheet）
GET  /api/s4/bom/history             # 历史任务列表
```

## 核心验收指标

| 指标 | 要求 | 实测 |
|------|------|------|
| 施工准备时间 | 缩短 ≥ 95% | 全链路约 7 秒（人工 2-4 小时） |
| 线缆估算误差 | < 15% | 满足 |
| 辅材漏项率 | < 2% | 满足 |
