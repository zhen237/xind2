# M02-CAD-Fusion 多源异构数据融合服务

S2 子赛题模块：DWG/DXF 解析、坐标系转换、CAD→GIS 数据融合

## 功能特性

### 1. CAD 文件解析
- **DXF 文件解析**: 支持解析 AutoCAD DXF 格式文件
- **DWG 文件解析**: 支持通过 ODAFileConverter 或 LibreCAD 转换 DWG 文件
- **实体提取**: 提取线、圆、弧、多边形、文字等 CAD 实体
- **图层识别**: 识别并分类 CAD 图层信息

### 2. 坐标系转换
- **多种坐标系支持**: WGS84、CGCS2000、Beijing1954、Xi'an1980 等
- **批量转换**: 支持批量坐标转换
- **高精度转换**: 使用 proj4j 库实现精确的坐标转换
- **预置常用转换**: WGS84↔CGCS2000、Beijing54→WGS84 等快速转换接口

### 3. CAD→GIS 数据融合
- **智能映射**: 自动将 CAD 实体类型映射为 GIS 几何类型
- **图层分类**: 根据 CAD 图层名自动分类为建筑物、道路、管线等
- **GeoJSON 输出**: 生成标准 GeoJSON 格式的 GIS 数据
- **属性保留**: 保留 CAD 原始属性并添加融合元数据

## 技术栈

- **Java 17**
- **Spring Boot 3.1.10**
- **MyBatis-Plus 3.5.5**
- **proj4j 1.2.3** (坐标转换)
- **MySQL 8.0**
- **JWT** (认证)

## 目录结构

```
packages/m02-cad-fusion/
├── backend/
│   ├── src/main/java/com/comm/m02/
│   │   ├── M02CadFusionApplication.java    # 启动类
│   │   ├── common/                          # 通用组件
│   │   │   ├── Result.java                  # 统一返回结果
│   │   │   ├── BusinessException.java       # 业务异常
│   │   │   └── GlobalExceptionHandler.java  # 全局异常处理
│   │   ├── config/                          # 配置类
│   │   │   ├── SecurityConfig.java          # 安全配置
│   │   │   ├── JwtAuthenticationFilter.java # JWT过滤器
│   │   │   ├── WebConfig.java               # Web配置
│   │   │   └── FileStorageConfig.java       # 文件存储配置
│   │   ├── controller/                      # 控制器
│   │   │   ├── CadFileController.java       # CAD文件管理API
│   │   │   ├── CoordinateController.java    # 坐标转换API
│   │   │   └── FusionController.java        # 数据融合API
│   │   ├── entity/                          # 实体类
│   │   ├── mapper/                          # MyBatis Mapper
│   │   ├── service/                         # 服务层
│   │   ├── parser/                          # CAD解析器
│   │   │   ├── CadEntity.java               # CAD实体模型
│   │   │   ├── DxfParser.java               # DXF解析器
│   │   │   ├── DwgParser.java               # DWG解析器
│   │   │   └── CadEntityExtractor.java      # 实体提取器
│   │   ├── transform/                       # 转换引擎
│   │   │   ├── CoordinateTransformer.java   # 坐标转换器
│   │   │   └── CadToGisMapper.java          # CAD→GIS映射器
│   │   ├── fusion/                          # 融合引擎
│   │   │   └── FusionEngine.java             # 融合引擎核心
│   │   ├── dto/                             # 数据传输对象
│   │   └── utils/                           # 工具类
│   ├── src/main/resources/
│   │   ├── application.yml                  # 应用配置
│   │   └── schema.sql                       # 数据库表结构
│   └── pom.xml                              # Maven配置
```

## API 接口

### CAD 文件管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/m02/cad-files/upload` | 上传 CAD 文件 (DWG/DXF) |
| GET | `/api/m02/cad-files/{id}` | 获取文件信息 |
| GET | `/api/m02/cad-files` | 获取文件列表 |
| DELETE | `/api/m02/cad-files/{id}` | 删除文件 |
| POST | `/api/m02/cad-files/{id}/parse` | 解析 DXF 文件 |
| GET | `/api/m02/cad-files/{id}/content` | 下载原文件 |

### 坐标转换

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/m02/coordinate/transform` | 单点坐标转换 |
| POST | `/api/m02/coordinate/batch-transform` | 批量坐标转换 |
| POST | `/api/m02/coordinate/wgs84-to-cgcs2000` | WGS84→CGCS2000 |
| POST | `/api/m02/coordinate/beijing54-to-wgs84` | Beijing54→WGS84 |
| GET | `/api/m02/coordinate/supported-systems` | 获取支持的坐标系 |

### 数据融合

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/m02/fusion/tasks` | 创建融合任务 |
| GET | `/api/m02/fusion/tasks/{id}` | 获取任务状态 |
| POST | `/api/m02/fusion/tasks/{id}/execute` | 执行融合任务 |
| POST | `/api/m02/fusion/auto-fuse` | 一键融合（创建+执行） |
| DELETE | `/api/m02/fusion/tasks/{id}` | 删除任务 |
| GET | `/api/m02/fusion/tasks/{id}/geojson` | 获取融合结果(GeoJSON) |

## 使用示例

### 1. 上传并解析 DXF 文件

```bash
# 上传文件
POST /api/m02/cad-files/upload
Content-Type: multipart/form-data

file: @drawing.dxf
projectId: 101
sourceEpsg: EPSG:4490
targetEpsg: EPSG:4326
```

### 2. 坐标转换

```bash
# WGS84 转 CGCS2000
POST /api/m02/coordinate/wgs84-to-cgcs2000?lon=114.39&lat=30.51

# 通用转换
POST /api/m02/coordinate/transform
{
  "sourceX": 114.39,
  "sourceY": 30.51,
  "sourceZ": 0,
  "sourceEpsg": "EPSG:4326",
  "targetEpsg": "EPSG:4490",
  "transformationType": "AUTO"
}
```

### 3. 一键融合 CAD→GIS

```bash
POST /api/m02/fusion/auto-fuse
{
  "taskName": "东湖基站设计融合",
  "projectId": 101,
  "sourceFileId": 1,
  "sourceEpsg": "EPSG:4490",
  "targetEpsg": "EPSG:4326",
  "transformationType": "AUTO"
}
```

### 4. 获取融合结果

```bash
GET /api/m02/fusion/tasks/{taskId}/geojson
```

## 快速开始

### 1. 初始化数据库

```sql
-- 执行 schema.sql
mysql -u root -p comm_platform < src/main/resources/schema.sql
```

### 2. 配置应用

修改 `application.yml` 中的数据库连接和文件存储路径：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/comm_platform
    username: root
    password: your_password

file:
  upload-dir: /path/to/uploads/m02
```

### 3. 构建运行

```bash
cd packages/m02-cad-fusion/backend
mvn clean package
java -jar target/m02-cad-fusion-1.0.0.jar
```

服务启动后访问 http://localhost:8082

## 支持的 CAD 实体类型

| CAD 类型 | GIS 几何类型 | 说明 |
|----------|-------------|------|
| LINE | LineString | 直线 |
| LWPOLYLINE | Polygon | 闭合多段线 |
| POLYLINE | LineString | 开放多段线 |
| CIRCLE | Polygon | 圆 |
| ARC | LineString | 弧 |
| POINT | Point | 点 |
| TEXT/MTEXT | Point | 文字 |
| INSERT | Point | 图块引用 |

## 图层分类映射

| CAD 图层关键词 | GIS 要素类型 |
|---------------|-------------|
| BUILDING | building |
| ROAD | road |
| PIPELINE | pipeline |
| TREE/VEGETATION | vegetation |
| WATER | water |
| BOUNDARY | boundary |
| EQUIPMENT | equipment |
| CABLE | cable |
| TOWER | tower |

## 注意事项

1. **DWG 文件处理**: DWG 文件需要通过 ODAFileConverter 或 LibreCAD 预转换为 DXF 格式
2. **大文件处理**: 建议单文件不超过 50MB，过大文件可能影响解析性能
3. **坐标系选择**: 武汉地区推荐使用 EPSG:4549 (CGCS2000 3度带 41°N)
4. **精度说明**: 坐标转换精度优于 0.001 度（约 0.1 米）

## 后续扩展

- [ ] 支持更多 CAD 实体类型（椭圆、样条曲线等）
- [ ] 添加坐标网格（CGCS2000 6度带投影转换）
- [ ] 实现语义化的图层识别
- [ ] 支持批量融合多个 CAD 文件
- [ ] 添加 REST API 文档（Swagger/SpringDoc）
