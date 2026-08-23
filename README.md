# M02 多源异构工程数据融合（CAD→GIS）

通信基建数智化平台子模块：将历史 CAD 图纸（DXF）自动转换为标准 GIS 数据，打通「历史图纸 → 数字化底座」的数据通道。

## 核心能力

- **CAD 文件解析**：DXF 实体提取（LINE / LWPOLYLINE / POINT / TEXT），图层语义映射
- **坐标系转换**：CGCS2000 投影坐标 → WGS84 经纬度（proj4j）
- **数据融合**：CAD 图层 → GIS 要素（建筑 / 铁塔 / 电缆 / 道路 / 设备）
- **标准输出**：GeoJSON / CSV 导出，可直接加载到 Cesium、QGIS 等平台

## 技术栈

Spring Boot 3 + MyBatis-Plus + proj4j + MySQL

## 目录结构

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

## 快速启动

```bash
cd packages/m02-cad-fusion/backend
mvn spring-boot:run
# 服务地址 http://localhost:8082/api/m02/
```
