# S4 — 设计成果向施工指令的自动转化

**类型**: Java Spring Boot + Python BOM 引擎（新建）
**端口**: 后端 8090 / 前端 5190
**归属**: S4 — 设计成果向施工指令的自动转化
**负责人**: 庞

## 职责

- Python BOM 生成引擎
- 设备-物料编码映射
- 辅材自动计算
- 线缆长度估算
- 施工图自动标注
- BOM 导出（Excel/PDF）
- 从 M04 迁移交付代码（DeliveryPackage*/WorkOrder）

## 启动

```bash
# 后端
cd packages/s4-bom-transform/backend
mvn spring-boot:run

# Python BOM 引擎（待实现）
cd packages/s4-bom-transform/engine
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn bom_engine:app --port 8093 --reload

# 前端（待创建）
cd packages/s4-bom-transform/frontend
npm install && npm run dev
```

## 依赖

- **M01 Auth**: JWT 鉴权
- **S1 REST API**: 接收设计成果（接口契约见技术架构与开发规范 §5.5）
- **MySQL**: 表前缀 `s4_`，Flyway 表 `flyway_schema_history_s4`

## API 约定

```
POST /api/v1/s4/bom/from-design   # 从设计生成 BOM
GET  /api/v1/s4/bom/task/{id}     # 查询 BOM 任务
GET  /api/v1/s4/bom/catalog       # 获取物料编码库
GET  /api/v1/s4/bom/export/{id}   # 导出 BOM 文件
```

## M04 迁移清单

从 M04 迁移以下代码到 S4：
- DeliveryPackageController/DeliveryPackage/DeliveryFile
- WorkOrderController/WorkOrder
- 对应 Service/Mapper
- 前端 views/DeliveryPackage.vue, WorkOrderList.vue
