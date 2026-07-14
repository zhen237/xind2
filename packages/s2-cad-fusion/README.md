# S2 — 多源异构工程数据融合

**类型**: Java Spring Boot + Vue 3（新建）
**端口**: 后端 8082 / 前端 5182
**归属**: S2 — 多源异构工程数据融合
**负责人**: 任

## 职责

- DWG/DXF 解析引擎
- 坐标系转换（WGS84/CGCS2000/地方坐标系）
- 多源数据模型统一
- 图层管理与冲突检测
- 融合结果预览与编辑

## 启动

```bash
# 后端
cd packages/s2-cad-fusion/backend
mvn spring-boot:run

# 前端（待创建）
cd packages/s2-cad-fusion/frontend
npm install && npm run dev
```

## 依赖

- **M01 Auth**: JWT 鉴权
- **MySQL**: 表前缀 `s2_`，Flyway 表 `flyway_schema_history_s2`
- **Python CAD 引擎**: DWG/DXF 解析（路径待定）

## API 约定

```
POST /api/v1/s2/cad/parse      # DWG/DXF 解析
POST /api/v1/s2/cad/transform  # 坐标系转换
POST /api/v1/s2/cad/fusion     # 多源数据融合
GET  /api/v1/s2/cad/layers     # 图层列表
```

## 对赛题输出

S2 融合结果通过 REST API 供 S1/S3/S4 调用。
