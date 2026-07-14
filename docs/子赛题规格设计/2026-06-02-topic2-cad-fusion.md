# 子赛题2 — 多源异构工程数据融合 详细设计

**版本**: v1.0  
**最后更新**: 2026-07-14  
**适用对象**: S2-任  
**关联文档**: [五人分工方案-按子赛题重组.md](../五人分工方案-按子赛题重组.md)

---

## 变更记录

| 版本 | 日期 | 更新内容 | 维护人 |
|------|------|----------|--------|
| v1.0 | 2026-07-14 | 初始版本，定义CAD数据融合规格 | 高（zhen237） |

---

## 一、赛题目标与指标

| 指标 | 要求 | 我们的目标 |
|------|------|-----------|
| CAD数据解析覆盖 | DWG/DXF格式 | 支持AutoCAD 2010+各版本 |
| 坐标系转换精度 | 米级 | 亚米级（CGCS2000↔WGS84↔地方坐标系） |
| 数据统一格式 | GeoJSON | 输出标准GeoJSON，含属性映射 |
| 多源融合类型 | CAD+GIS | 建筑轮廓、道路、电力线、地形高程 |

---

## 二、功能架构

```
┌─────────────────────────────────────────────────────────────┐
│                    S2 多源异构数据融合模块                     │
├───────────────┬───────────────┬───────────────┬─────────────┤
│  CAD解析引擎   │  坐标系转换    │  数据融合层    │  API服务层   │
│               │               │               │             │
│ DWG → GeoJSON │ CGCS2000↔WGS84│ 图层提取/过滤  │ REST API    │
│ DXF → GeoJSON │ 地方系↔标准系  │ 属性映射配置   │ 文件上传接口 │
│ 图层识别/分离  │ 批量转换工具   │ 冲突检测/合并  │ 数据查询接口 │
│ 属性提取/映射  │ 七参数/四参数   │ 数据校验       │ 下载/导出    │
└───────────────┴───────────────┴───────────────┴─────────────┘
```

---

## 三、核心功能

### 3.1 CAD文件解析（DWG/DXF）

**目标**: 解析通信工程CAD图纸，提取矢量图层数据

**输入格式**:
- `.dwg` — AutoCAD 图形文件（2010-2024版本）
- `.dxf` — 图形交换格式（ASCII/Binary）

**解析内容**:

| 图层类型 | CAD图层命名规范 | 提取要素 | 输出格式 |
|----------|----------------|----------|----------|
| 建筑轮廓 | BUILDING-*, 建筑-* | Polygon/封闭PLine | GeoJSON Polygon |
| 道路中心线 | ROAD-*, 道路-* | Line/PLine | GeoJSON LineString |
| 电力线路 | POWER-*, 电力-* | Line/PLine | GeoJSON LineString |
| 管井位置 | MANHOLE-*, 井-* | Point/BlockRef | GeoJSON Point |
| 地形等高线 | CONTOUR-*, 等高线-* | PLine(3D) | GeoJSON LineString + 高程属性 |
| 红线范围 | REDLINE-*, 红线-* | Polygon | GeoJSON Polygon |

**技术方案**:
- Python后端：使用 `ezdxf` 库解析DXF，`libredwg` / `ODA File Converter` 处理DWG
- Java后端：使用 `aspose-cad` 或 `LibreDWG` 的JNI封装
- 推荐：**Java + Python混合** — Java负责文件管理/API，Python引擎负责解析

**属性映射配置**:

```yaml
# cad-layer-mapping.yml
layers:
  building:
    patterns: ["BUILDING-*", "建筑-*", "BLDG-*"]
    feature_type: "Polygon"
    properties:
      building_name: "{LAYER_NAME}"
      floor_count: "extract_from_block_attribute('楼层')"
      building_type: "extract_from_block_attribute('用途')"
  
  power_line:
    patterns: ["POWER-*", "电力-*", "PL-*"]
    feature_type: "LineString"
    properties:
      voltage_level: "extract_from_layer_name(r'(\d+)kV')"
      line_name: "{LAYER_NAME}"
```

### 3.2 坐标系转换

**目标**: 统一不同来源数据的坐标系为WGS84

**支持坐标系**:
| 坐标系 | 说明 | 常见于 |
|--------|------|--------|
| WGS84 (EPSG:4326) | 全球经纬度 | GPS、天地图 |
| CGCS2000 (EPSG:4490) | 国家大地坐标系 | 工程CAD图纸 |
| 地方坐标系 | 各地独立坐标系 | 地方规划CAD |

**转换参数**:
- 七参数转换：平移(dX,dY,dZ) + 旋转(rX,rY,rZ) + 缩放
- 四参数转换：平移(dX,dY) + 旋转 + 缩放（适用于小范围）
- 工具库：`proj4j` (Java) / `pyproj` (Python)

```python
# 示例：CGCS2000 → WGS84 批量转换
from pyproj import Transformer

transformer = Transformer.from_crs("EPSG:4490", "EPSG:4326")
lon, lat = transformer.transform(cgcs_x, cgcs_y)
```

### 3.3 数据融合与冲突解决

**目标**: 将CAD数据与已有GIS数据合并，解决冲突

**融合规则**:
1. **优先级**: GIS现有数据 > CAD新解析数据（除非明确标记"覆盖"）
2. **去重**: 同名+同位置(<5m)的要素去重，保留数据较完整的版本
3. **冲突标记**: 同位置不同属性时标记为"待人工审核"
4. **坐标统一**: 所有输出统一为WGS84 (EPSG:4326)

### 3.4 REST API设计

**新增模块**: `s2-cad-fusion`，后端端口 **8082**

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 上传CAD | POST | `/api/s2/cad/upload` | 上传DWG/DXF文件，触发解析 |
| 查询任务 | GET | `/api/s2/cad/task/{id}` | 查询解析任务状态 |
| 获取图层 | GET | `/api/s2/cad/layers/{taskId}` | 获取已解析的图层列表 |
| 下载GeoJSON | GET | `/api/s2/cad/download/{taskId}/{layer}` | 下载指定图层的GeoJSON |
| 坐标系转换 | POST | `/api/s2/cad/transform` | 自定义坐标系转换 |
| 融合预览 | GET | `/api/s2/cad/fusion/{projectId}` | 预览融合后的数据 |

**数据交互协议**（与S1对接）:

```json
// S2 → S1: 融合后的数据
POST /api/s1/design/import-fusion-data
{
  "projectId": "PRJ-001",
  "source": "cad-fusion",
  "layers": [
    {
      "type": "buildings",
      "features": [...]  // GeoJSON FeatureCollection
    },
    {
      "type": "roads",
      "features": [...]
    }
  ],
  "metadata": {
    "coordinateSystem": "EPSG:4326",
    "fusionTime": "2026-07-14T10:00:00Z"
  }
}
```

---

## 四、技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Spring Boot 3.1.10 | 与现有M0x模块统一 |
| CAD解析引擎 | Python (ezdxf + libreDWG) | 社区成熟度最高 |
| 坐标系转换 | pyproj / proj4j | 支持全部EPSG定义 |
| 文件存储 | MinIO | 与现有基础设施共享 |
| 数据库 | MySQL (comm_platform) | s2_ 表前缀 |
| 前端 | Vue 3 + Element Plus | 与M06门户统一 |

---

## 五、数据库设计

```sql
-- CAD文件上传记录
CREATE TABLE IF NOT EXISTS s2_cad_upload (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    file_name VARCHAR(255) COMMENT '原始文件名',
    file_path VARCHAR(500) COMMENT 'MinIO存储路径',
    file_size BIGINT COMMENT '文件大小(字节)',
    file_type VARCHAR(10) COMMENT 'dwg/dxf',
    status TINYINT DEFAULT 0 COMMENT '0待解析 1解析中 2完成 3失败',
    layer_count INT DEFAULT 0 COMMENT '识别图层数',
    feature_count INT DEFAULT 0 COMMENT '提取要素数',
    coordinate_system VARCHAR(50) COMMENT '原始坐标系',
    error_msg TEXT COMMENT '错误信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 解析后的图层数据
CREATE TABLE IF NOT EXISTS s2_cad_layer (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    upload_id BIGINT NOT NULL,
    layer_name VARCHAR(100) COMMENT '图层名称',
    feature_type VARCHAR(20) COMMENT 'Point/LineString/Polygon',
    feature_count INT COMMENT '要素数量',
    geojson_path VARCHAR(500) COMMENT 'GeoJSON文件路径',
    properties_meta JSON COMMENT '属性元信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 坐标系转换记录
CREATE TABLE IF NOT EXISTS s2_transform_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    layer_id BIGINT NOT NULL,
    source_crs VARCHAR(20) COMMENT 'EPSG:4490',
    target_crs VARCHAR(20) COMMENT 'EPSG:4326',
    params_json TEXT COMMENT '转换参数',
    status TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 数据融合记录
CREATE TABLE IF NOT EXISTS s2_fusion_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    source_layers TEXT COMMENT '来源图层ID列表(JSON)',
    result_path VARCHAR(500) COMMENT '融合结果GeoJSON路径',
    conflict_count INT DEFAULT 0 COMMENT '冲突数量',
    status TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 六、前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| CAD上传页 | `/cad/upload` | 拖拽上传DWG/DXF文件 |
| 解析状态页 | `/cad/tasks` | 查看所有解析任务状态 |
| 图层预览页 | `/cad/preview/:taskId` | OpenLayers地图预览解析结果 |
| 融合管理页 | `/cad/fusion/:projectId` | 查看融合结果、冲突处理 |

**前端端口**: 5182（dev模式）

---

## 七、开发路线

| 阶段 | 内容 | 预计工作量 |
|------|------|-----------|
| 第1周 | Java Spring Boot脚手架 + 文件上传API + 数据库建表 | 3天 |
| 第2周 | DXF解析引擎（Python）+ 坐标系转换 | 4天 |
| 第3周 | DWG解析 + 图层识别/属性映射 | 5天 |
| 第4周 | 数据融合引擎 + 前端页面 | 5天 |
| 第5周 | 与S1联调 + 优化 | 3天 |

---

## 八、与各赛题的数据接口

```
S2(CAD融合) ──→ S1(设计)     融合后的GeoJSON数据
S2(CAD融合) ──→ Screen(大屏)  数据来源统计
S2(CAD融合) ←── 共享认证(M01)  JWT鉴权
```

---

**文档结束** — 更多实施细节参考 [五人分工方案-按子赛题重组.md](../五人分工方案-按子赛题重组.md)
