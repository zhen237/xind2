# API接口文档

**版本**: 1.0
**最后更新**: 2026-06-08
**适用对象**: 全体开发人员

---

## 一、接口总览

| 编号 | 方法 | 路径 | 说明 | 提供方 |
|------|------|------|------|--------|
| API-01 | POST | `/api/m03/design/upload` | 上传设计方案 | M03后端 |
| API-02 | GET | `/api/m03/design/{projectId}` | 获取设计方案 | M03后端 |
| API-03 | GET | `/api/m03/design/{schemeId}/sites` | 获取站点数据 | M03后端 |
| API-04 | POST | `/api/m03/design/{schemeId}/sites` | 上传站点数据 | M03后端 |
| API-05 | GET | `/api/m03/design/{projectId}/geojson` | 获取GeoJSON数据 | M03后端 |
| API-06 | DELETE | `/api/m03/design/{schemeId}` | 删除设计方案 | M03后端 |

---

## 二、M03后端接口

### 2.1 上传设计方案

**请求**:
```
POST /api/m03/design/upload
Content-Type: application/json
```

**请求体**:
```json
{
    "projectId": 101,
    "schemeName": "基站智能设计",
    "frequencyBand": "3.5GHz",
    "towerHeight": 45,
    "gridSize": "4x4",
    "totalSites": 16,
    "validSites": 14,
    "invalidSites": 2,
    "avgRsrp": -75.5,
    "sites": [
        {
            "siteId": "BTS-001",
            "siteName": "基站1",
            "longitude": 114.39,
            "latitude": 30.506,
            "towerHeight": 45,
            "rsrp": -75.5,
            "isValid": true
        }
    ]
}
```

**响应**:
```json
{
    "code": 200,
    "message": "上传成功",
    "data": 1
}
```

### 2.2 获取设计方案

**请求**:
```
GET /api/m03/design/{projectId}
```

**响应**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "id": 1,
        "projectId": 101,
        "schemeName": "基站智能设计",
        "frequencyBand": "3.5GHz",
        "towerHeight": 45,
        "gridSize": "4x4",
        "totalSites": 16,
        "validSites": 14,
        "invalidSites": 2,
        "avgRsrp": -75.5
    }
}
```

### 2.3 获取站点数据

**请求**:
```
GET /api/m03/design/{schemeId}/sites
```

**响应**:
```json
{
    "code": 200,
    "message": "success",
    "data": [
        {
            "id": 1,
            "schemeId": 1,
            "siteId": "BTS-001",
            "siteName": "基站1",
            "longitude": 114.39,
            "latitude": 30.506,
            "towerHeight": 45,
            "rsrp": -75.5,
            "isValid": 1
        }
    ]
}
```

### 2.4 上传站点数据

**请求**:
```
POST /api/m03/design/{schemeId}/sites
Content-Type: application/json
```

**请求体**:
```json
{
    "siteId": "BTS-001",
    "siteName": "基站1",
    "longitude": 114.39,
    "latitude": 30.506,
    "towerHeight": 45,
    "rsrp": -75.5,
    "isValid": true
}
```

**响应**:
```json
{
    "code": 200,
    "message": "上传成功",
    "data": null
}
```

---

## 三、数据库表结构

### 3.1 设计方案表 (m03_design_scheme)

```sql
CREATE TABLE m03_design_scheme (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    scheme_name VARCHAR(200),
    frequency_band VARCHAR(50),
    tower_height DECIMAL(8,2),
    grid_size VARCHAR(20),
    total_sites INT,
    valid_sites INT,
    invalid_sites INT,
    avg_rsrp DECIMAL(10,2),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 3.2 站点数据表 (m03_site)

```sql
CREATE TABLE m03_site (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_id BIGINT NOT NULL,
    site_id VARCHAR(50),
    site_name VARCHAR(100),
    longitude DECIMAL(10,7),
    latitude DECIMAL(10,7),
    tower_height DECIMAL(8,2),
    rsrp DECIMAL(10,2),
    is_valid TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 四、错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

**文档维护人**: 人A
**最后更新**: 2026-06-08
