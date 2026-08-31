# M02 多源异构工程数据融合（CAD→GIS）

通信基建数智化平台子模块：将历史 CAD 图纸（DWG/DXF）自动转换为标准 GIS 数据，并与既有 GIS 基准数据融合，打通「历史图纸 → 数字化底座」的数据通道。

## 核心能力

- **CAD 文件解析**：DXF 实体提取（LINE / LWPOLYLINE / POLYLINE / POINT / CIRCLE / ARC / TEXT / MTEXT），AutoCAD 2010+ 格式
- **图层语义识别**：按 `cad-layer-mapping.yml` 规则将 CAD 图层映射为 6 类标准要素——建筑轮廓 / 道路中心线 / 电力线 / 管井 / 等高线 / 用地红线
- **坐标转换**：CGCS2000 高斯投影 → WGS84 经纬度（pyproj / proj4j），满足亚米级精度
- **CAD+GIS 数据融合**：GIS 既有数据优先、同名 <5m 自动去重、同名属性冲突标记待人工审核
- **标准输出**：按要素类型分层的 GeoJSON，可直接加载到 Cesium、OpenLayers、QGIS 等平台

## 模块组成

| 模块 | 技术栈 | 说明 |
|---|---|---|
| `engine/` | Python 3 + ezdxf + pyproj + FastAPI | 解析/转换/融合引擎（CLI + HTTP 服务双入口） |
| `backend/` | Spring Boot 3 + MyBatis-Plus + proj4j + MySQL | 文件管理、任务编排、REST API |

### engine（解析引擎，本机可直接跑通）

```
packages/m02-cad-fusion/engine
├── cad_engine
│   ├── parser.py       # DXF 解析（ezdxf）：实体提取 + 文本就近挂接
│   ├── classifier.py   # 6 类要素图层识别（cad_layer_mapping.yml 驱动）
│   ├── transformer.py  # 坐标转换（pyproj）：CGCS2000 高斯 → WGS84
│   ├── geojson_writer.py # 按类型输出 GeoJSON
│   ├── fusion.py       # CAD+GIS 融合：GIS优先 / <5m去重 / 冲突标记
│   ├── cli.py          # 命令行入口
│   └── server.py       # FastAPI 服务（供 Java 后端进程间调用）
├── samples             # 试运行样例（运城通信工程图纸 DXF + GIS 基准数据）
└── cad_layer_mapping.yml
```

**全链路运行（解析 → 分类 → 转换 → GeoJSON → 融合）：**

```bash
cd packages/m02-cad-fusion/engine
pip install -r requirements.txt
python -m cad_engine.cli run --input samples/yuncheng_site.dxf --outdir out --gis-dir samples/gis
```

输出到 `out/`：6 类要素 GeoJSON + 2 个融合结果 + `parse_summary.json` 解析摘要。

**启动 HTTP 服务（供 Java 后端调用）：**

```bash
python -m cad_engine.server   # 端口 8092
```

### backend（Java 管理与服务层）

```
packages/m02-cad-fusion/backend
├── src/main/java/com/comm/m02
│   ├── parser    # DXF 解析引擎
│   ├── transform # 坐标转换
│   ├── fusion    # 融合引擎
│   ├── service   # 业务逻辑
│   └── controller# REST 接口（/api/m02/）
└── src/main/resources
    └── application.yml  # 端口 8082
```

```bash
cd packages/m02-cad-fusion/backend
mvn spring-boot:run
# 服务地址 http://localhost:8082/api/m02/
```

## 融合规则（FR-6 / FR-7）

1. **GIS 既有数据优先**：GIS 要素全部保留；
2. **同名去重**：CAD 要素与 GIS 要素同名且几何距离 < 5m 时丢弃 CAD 要素；
3. **冲突标记**：同名、相距 ≥5m 且 <50m、属性不一致时，标记 `fusion_conflict = 待人工审核` 并记录冲突字段。

## 样例数据

`samples/yuncheng_site.dxf` 为按通信工程图纸惯例生成的试运行样例（8 图层、24 实体，含等高线/道路/电力线/管井/红线/建筑轮廓 + 标注文本）；`samples/gis/` 为 GIS 基准数据，其中预置了 1 处同名同位管井（触发去重）和 1 处同名偏移建筑（触发冲突审核）。生成脚本：`python samples/make_samples.py`。
