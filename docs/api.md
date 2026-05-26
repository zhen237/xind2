# 通信基建数智化全流程平台 – API 文档（规范与示例）

**版本**：1.1
**最后更新**：2026-05-26
**基础路径**：各模块后端独立部署，通过 Nginx 路由到不同端口或路径前缀
**认证方式**：JWT Bearer Token（除登录接口外，所有请求需在 Header 中携带 `Authorization: Bearer <token>`）

> **说明**：本文档包含两部分：
> - **已实现接口**：M01 认证、M03 BIM+GIS（基础CRUD）、M05 数字孪生（基础CRUD）
> - **设计规范接口**：M02 网络规划、M03 高级功能（碰撞检测等）、M04 交付、M05 高级功能（遥测、巡检等）——这些是目标接口设计，尚未实现

---

## 目录

1. [通用规范](#1-通用规范)
2. [M01 统一认证与权限](#2-m01-统一认证与权限)
3. [M02 数通网络规划与仿真](#3-m02-数通网络规划与仿真)
4. [M03 BIM+GIS 三维设计引擎](#4-m03-bimgis-三维设计引擎)
5. [M04 数智化交付与工作流](#5-m04-数智化交付与工作流)
6. [M05 数字孪生与智慧运维](#6-m05-数字孪生与智慧运维)
7. [错误码表](#7-错误码表)

---

## 1. 通用规范

### 1.1 基础路径

| 模块 | 基础路径   | 示例                            |
| ---- | ---------- | ------------------------------- |
| M01  | `/api/m01` | `http://localhost:8080/api/m01` |
| M02  | `/api/m02` | `http://localhost:8081/api/m02` |
| M03  | `/api/m03` | `http://localhost:8083/api/m03` |
| M04  | `/api/m04` | `http://localhost:8084/api/m04` |
| M05  | `/api/m05` | `http://localhost:8085/api/m05` |

### 1.2 统一响应格式

所有接口成功时返回：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }   // 可以是对象、数组或 null
}
```

失败时返回：

```json
{
  "code": 40001,
  "message": "用户名或密码错误",
  "data": null
}
```

### 1.3 HTTP 状态码

- `200` OK
- `400` 客户端错误（参数错误、业务逻辑错误）
- `401` 未认证（token 缺失或无效）
- `403` 无权限（token 有效但权限不足）
- `404` 资源不存在
- `500` 服务器内部错误

### 1.4 认证方式

除 `/auth/login` 接口外，所有接口必须携带 JWT：

```
Authorization: Bearer <your-jwt-token>
```

JWT 由 M01 签发，其他模块使用相同密钥验证。

---

## 2. M01 统一认证与权限

### 2.1 用户登录

**接口**：`POST /api/m01/auth/login`

**请求体**：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsImlhdCI6MTcxNjIwNDAwMCwiZXhwIjoxNzE2ODA4ODAwfQ.xxx",
    "userId": 1,
    "username": "admin",
    "realName": "管理员"
  }
}
```

### 2.2 Token验证

**接口**：`GET /api/m01/auth/validate`

**请求头**：`Authorization: Bearer <token>`

**响应**：

```json
{
  "userId": 1,
  "username": "admin"
}
```

### 2.3 获取用户列表

**接口**：`GET /api/m01/user`

**响应**：

```json
[
  {
    "id": 1,
    "username": "admin",
    "realName": "超级管理员",
    "email": "admin@example.com",
    "phone": null,
    "status": 1
  }
]
```

### 2.4 获取指定用户

**接口**：`GET /api/m01/user/{id}`

**响应**：

```json
{
  "id": 1,
  "username": "admin",
  "realName": "超级管理员",
  "email": "admin@example.com",
  "status": 1
}
```

### 2.5 获取用户菜单树

**接口**：`GET /api/m01/menu/user`

**响应**：

```json
{
  "code": 200,
  "data": [
    {
      "id": 10,
      "menuCode": "design",
      "menuName": "设计仿真",
      "menuType": 1,
      "children": [
        {
          "id": 11,
          "menuCode": "m03",
          "menuName": "三维设计",
          "menuType": 2,
          "iframeUrl": "/modules/m03/index.html",
          "permissionCode": "m03:view"
        },
        {
          "id": 12,
          "menuCode": "m02",
          "menuName": "网络规划",
          "menuType": 2,
          "iframeUrl": "/modules/m02/index.html",
          "permissionCode": "m02:view"
        }
      ]
    },
    {
      "id": 20,
      "menuCode": "ops",
      "menuName": "运维监控",
      "menuType": 1,
      "children": [
        {
          "id": 21,
          "menuCode": "m05",
          "menuName": "数字孪生",
          "menuType": 2,
          "iframeUrl": "/modules/m05/index.html",
          "permissionCode": "m05:view"
        }
      ]
    }
  ]
}
```

### 2.6 获取用户权限码列表（待实现）

**接口**：`GET /api/m01/permissions`

**响应**：

```json
{
  "code": 200,
  "data": ["m03:model:upload", "m05:alert:handle", "m04:workorder:assign"]
}
```

---

## 3. M02 数通网络规划与仿真

### 3.1 创建规划方案

**接口**：`POST /api/m02/plan`

**请求体**：

```json
{
  "planName": "城东新区5G覆盖方案",
  "description": "覆盖面积20平方公里",
  "stations": [
    {
      "longitude": 118.783,
      "latitude": 32.042,
      "height": 45,
      "antennaType": "AAU5313"
    }
  ],
  "params": {
    "propagationModel": "Okumura-Hata",
    "frequency": 3500
  }
}
```

**响应**：

```json
{
  "code": 200,
  "data": { "planId": 101 }
}
```

### 3.2 执行覆盖仿真

**接口**：`POST /api/m02/simulation/coverage`

**请求体**：

```json
{
  "planId": 101,
  "resolution": 20,
  "outputFormat": "geojson"
}
```

**响应**（异步任务模式，返回任务 ID）：

```json
{
  "code": 200,
  "data": { "taskId": "sim-abc123" }
}
```

**查询仿真结果**：`GET /api/m02/simulation/task/{taskId}`

```json
{
  "code": 200,
  "data": {
    "status": "COMPLETED",
    "resultUrl": "/api/m02/simulation/result/sim-abc123.geojson",
    "coverageHeatmap": "base64-image-string"
  }
}
```

### 3.3 获取规划方案列表

**接口**：`GET /api/m02/plan?page=1&size=10`

**响应**：

```json
{
  "code": 200,
  "data": {
    "total": 25,
    "list": [
      {
        "planId": 101,
        "planName": "城东新区5G覆盖方案",
        "createTime": "2026-05-18T10:30:00",
        "status": "SIMULATED"
      }
    ]
  }
}
```

---

## 4. M03 BIM+GIS 三维设计引擎

### 4.1 上传 BIM 模型

**接口**：`POST /api/m03/model/upload`

**请求**：`multipart/form-data`

| 参数      | 类型   | 说明                     |
| --------- | ------ | ------------------------ |
| file      | File   | 模型文件（IFC/glTF/SKP） |
| projectId | Long   | 关联项目 ID              |
| modelName | String | 模型名称（可选）         |

**响应**：

```json
{
  "code": 200,
  "data": { "modelId": 5001, "filePath": "m03-models/xxx.gltf" }
}
```

### 4.2 碰撞检测

**接口**：`POST /api/m03/collision/check`

**请求体**：

```json
{
  "projectId": 101,
  "modelIds": [5001, 5002],
  "tolerance": 0.05
}
```

**响应**：

```json
{
  "code": 200,
  "data": {
    "collisions": [
      {
        "type": "HARD",
        "position": [118.783, 32.042, 12.5],
        "message": "机柜与立柱碰撞",
        "suggestion": "向右移动0.3米"
      }
    ],
    "reportUrl": "/api/m03/collision/report/xxx.pdf"
  }
}
```

### 4.3 获取设计数据（机房布局）

**接口**：`GET /api/m03/design/layout?projectId=101`

**响应**：

```json
{
  "code": 200,
  "data": {
    "rooms": [
      {
        "roomId": 201,
        "name": "核心机房",
        "boundary": { "minX": 0, "minY": 0, "maxX": 20, "maxY": 15 },
        "devices": [
          {
            "deviceId": 301,
            "type": "机柜",
            "position": [5, 6, 0],
            "rotation": 90,
            "modelUrl": "/modules/m03/models/cabinet.glb"
          }
        ]
      }
    ]
  }
}
```

### 4.4 保存设计（机房布局）

**接口**：`POST /api/m03/design/layout`

**请求体**：同 `GET` 返回的结构，加上 `projectId`。

**响应**：`{ "code": 200, "data": { "layoutId": 401 } }`

---

## 5. M04 数智化交付与工作流

### 5.1 创建工单（手动或由 M05 自动触发）

**接口**：`POST /api/m04/workorder`

**请求体**：

```json
{
  "title": "基站高温告警处理",
  "description": "BTS1024 机柜温度超过阈值",
  "priority": "HIGH",
  "assignedTo": 1002,
  "source": "ALERT",
  "sourceId": 9001
}
```

**响应**：

```json
{
  "code": 200,
  "data": { "orderId": 6001, "orderNo": "WO20260520001" }
}
```

### 5.2 获取工单列表（运维人员）

**接口**：`GET /api/m04/workorder?status=0&page=1&size=10`

**状态**：`0`=待处理，`1`=处理中，`2`=已完成，`3`=已关闭

**响应**：

```json
{
  "code": 200,
  "data": {
    "total": 8,
    "list": [
      {
        "orderId": 6001,
        "orderNo": "WO20260520001",
        "title": "基站高温告警处理",
        "status": 0,
        "createTime": "2026-05-20T14:30:00"
      }
    ]
  }
}
```

### 5.3 更新工单状态（处理进度）

**接口**：`PUT /api/m04/workorder/{orderId}/status`

**请求体**：

```json
{
  "status": 1,
  "comment": "已派发维修人员",
  "attachmentUrls": ["/minio/m04/photo1.jpg"]
}
```

**响应**：`{ "code": 200, "message": "updated" }`

### 5.4 生成交付包（竣工归档）

**接口**：`POST /api/m04/delivery/package`

**请求体**：

```json
{
  "projectId": 101,
  "includeModels": true,
  "includeReports": true,
  "includePhotos": true
}
```

**响应**（异步任务）：

```json
{
  "code": 200,
  "data": { "packageTaskId": "pkg-abc", "downloadUrl": "/api/m04/delivery/download/pkg-abc.zip" }
}
```

---

## 6. M05 数字孪生与智慧运维

### 6.1 设备资产列表

**按站点查询**：`GET /api/m05/device/station/{stationCode}`

| 参数        | 说明     |
| ----------- | -------- |
| stationCode | 站点编码 |

**按状态查询**：`GET /api/m05/device/status/{status}`

| 参数   | 说明                   |
| ------ | ---------------------- |
| status | 1=在线，0=离线，2=故障 |

**获取全部**：`GET /api/m05/device`

**响应**：

```json
{
  "code": 200,
  "data": {
    "total": 45,
    "list": [
      {
        "deviceId": 10001,
        "deviceCode": "BTS-1024",
        "deviceName": "华为AAU5313",
        "status": 2,
        "lastTelemetry": {
          "temperature": 78,
          "voltage": 53.2,
          "timestamp": "2026-05-20T15:00:00"
        }
      }
    ]
  }
}
```

### 6.2 实时告警规则配置

**接口**：`POST /api/m05/alert/rule`

**请求体**：

```json
{
  "deviceType": "AAU",
  "metric": "temperature",
  "operator": ">",
  "threshold": 75,
  "level": 2,
  "notifyChannels": ["sms", "webhook"]
}
```

**响应**：`{ "code": 200, "data": { "ruleId": 301 } }`

### 6.3 处理告警（闭环）

**接口**：`PUT /api/m05/alert/{alertId}/handle`

**请求体**：

```json
{
  "action": "ACK",   // ACK确认, RESOLVE解决
  "comment": "已派单维修，临时调高空调温度"
}
```

**响应**：`{ "code": 200, "message": "告警已确认" }`

### 6.4 获取设备最新遥测数据（用于大屏）

**接口**：`GET /api/m05/telemetry/latest?deviceId=10001`

**响应**：

```json
{
  "code": 200,
  "data": {
    "deviceId": 10001,
    "temperature": 78.2,
    "humidity": 45.5,
    "voltage": 53.1,
    "power": 1200,
    "timestamp": "2026-05-20T15:05:00"
  }
}
```

### 6.5 启动智能巡检计划

**接口**：`POST /api/m05/inspection/plan`

**请求体**：

```json
{
  "name": "每周基站巡检",
  "cron": "0 0 9 * * 1",
  "stationIds": [1001, 1002, 1003],
  "checkItems": ["温度", "电压", "告警灯"]
}
```

**响应**：`{ "code": 200, "data": { "planId": 500 } }`

---

## 7. 错误码表

| 错误码 | 说明                           | 处理建议                     |
| ------ | ------------------------------ | ---------------------------- |
| 40001  | 用户名或密码错误               | 核对用户名密码               |
| 40002  | 参数校验失败                   | 检查请求参数格式             |
| 40003  | 资源已存在（如重复命名）       | 修改名称后重试               |
| 40004  | 业务规则冲突（如碰撞检测）     | 根据提示修改设计             |
| 40101  | Token 无效或过期               | 重新登录获取新 token         |
| 40102  | 未携带 Token                   | 在请求头中添加 Authorization |
| 40301  | 无操作权限                     | 联系管理员分配权限           |
| 40401  | 资源不存在                     | 检查 ID 是否正确             |
| 50001  | 服务器内部错误                 | 查看服务日志，联系开发人员   |
| 50002  | 第三方服务调用失败（如 MinIO） | 检查依赖服务是否正常         |

---

## 附录：已实现接口清单

以下是当前代码中实际实现的接口，可直接调用测试。

### A. M01 认证服务（端口 8080）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/m01/auth/login | 用户登录 |
| GET | /api/m01/auth/validate | Token验证 |
| GET | /api/m01/user | 获取所有用户 |
| GET | /api/m01/user/{id} | 获取指定用户 |
| POST | /api/m01/user | 创建用户 |
| PUT | /api/m01/user/{id} | 更新用户 |
| DELETE | /api/m01/user/{id} | 删除用户 |
| GET | /api/m01/menu/user | 获取当前用户菜单树 |

### B. M03 BIM+GIS 服务（端口 8083）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/m03/device | 获取所有设备 |
| GET | /api/m03/device/{id} | 获取指定设备 |
| GET | /api/m03/device/project/{projectId} | 按项目获取设备 |
| GET | /api/m03/device/station/{stationCode} | 按站点获取设备 |
| GET | /api/m03/device/type/{deviceType} | 按类型获取设备 |
| POST | /api/m03/device | 添加设备 |
| PUT | /api/m03/device/{id} | 更新设备 |
| DELETE | /api/m03/device/{id} | 删除设备 |
| GET | /api/m03/model | 获取所有模型 |
| GET | /api/m03/model/{id} | 获取指定模型 |
| GET | /api/m03/model/type/{modelType} | 按类型获取模型 |
| POST | /api/m03/model | 添加模型 |
| PUT | /api/m03/model/{id} | 更新模型 |
| DELETE | /api/m03/model/{id} | 删除模型 |
| GET | /api/m03/project | 获取所有项目 |
| GET | /api/m03/project/{id} | 获取指定项目 |
| POST | /api/m03/project | 创建项目 |
| PUT | /api/m03/project/{id} | 更新项目 |
| DELETE | /api/m03/project/{id} | 删除项目 |
| GET | /api/m03/region | 获取所有区域 |
| GET | /api/m03/region/{id} | 获取指定区域 |
| GET | /api/m03/region/parent/{parentCode} | 按父级获取子区域 |

### C. M05 数字孪生服务（端口 8085）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/m05/device | 获取所有设备 |
| GET | /api/m05/device/{id} | 获取指定设备 |
| GET | /api/m05/device/test | 测试数据库连接 |
| GET | /api/m05/device/station/{stationCode} | 按站点获取设备 |
| GET | /api/m05/device/status/{status} | 按状态获取设备 |
| POST | /api/m05/device | 添加设备 |
| PUT | /api/m05/device/{id} | 更新设备 |
| DELETE | /api/m05/device/{id} | 删除设备 |
| GET | /api/m05/alert/recent | 获取最近告警 |
| GET | /api/m05/alert/status/{status} | 按状态获取告警 |
| GET | /api/m05/alert/level/{level} | 按级别获取告警 |
| GET | /api/m05/alert/statistics | 获取告警统计 |
| GET | /api/m05/alert/count/unprocessed | 获取未处理告警数 |
| GET | /api/m05/alert/{id} | 获取告警详情 |
| POST | /api/m05/alert | 创建告警 |
| PUT | /api/m05/alert/{id}/confirm | 确认告警 |
| PUT | /api/m05/alert/{id}/resolve | 解决告警 |

---

**文档说明**：

- 以上接口中，"附录"部分为**已实现接口**，其余为**设计规范与示例**。
- 各模块开发者在实现时，请保持响应格式与错误码一致。
- 使用 OpenAPI（Swagger）工具生成交互式文档，便于联调。