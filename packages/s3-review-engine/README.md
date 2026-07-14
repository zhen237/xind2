# S3 — 基于行业标准的设计智能审查

**类型**: Java Spring Boot + Python 规则引擎（新建）
**端口**: 后端 8089 / 前端 5189
**归属**: S3 — 基于行业标准的设计智能审查
**负责人**: 王

## 职责

- Python 规则引擎（可配置的行业安全规范）
- 电力安全审查（接地电阻/安全距离）
- 防雷接地审查（避雷针覆盖/接地网）
- 结构安全审查（承重/抗风）
- 审查报告自动生成（PDF）
- 从 M04 迁移验收代码（Acceptance*/SafetyCheck 等）

## 启动

```bash
# 后端
cd packages/s3-review-engine/backend
mvn spring-boot:run

# Python 规则引擎（待实现）
cd packages/s3-review-engine/rules
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn rule_engine:app --port 8092 --reload

# 前端（待创建）
cd packages/s3-review-engine/frontend
npm install && npm run dev
```

## 依赖

- **M01 Auth**: JWT 鉴权
- **S1 REST API**: 接收设计数据（接口契约见技术架构与开发规范 §5.5）
- **MySQL**: 表前缀 `s3_`，Flyway 表 `flyway_schema_history_s3`

## API 约定

```
POST /api/v1/s3/review/submit      # 提交审查
GET  /api/v1/s3/review/task/{id}   # 查询审查任务
GET  /api/v1/s3/review/rules       # 获取规则列表
GET  /api/v1/s3/review/report/{id} # 获取审查报告
```

## M04 迁移清单

从 M04 迁移以下代码到 S3：
- AcceptanceController/Problem/Task
- SafetyCheck/BarrierCheck/CertVerification/ElectricityCheck
- 对应 Service/Mapper
- 前端 views/AcceptanceList.vue
