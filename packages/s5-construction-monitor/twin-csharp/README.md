# S5 孪生后端（C# / ASP.NET Core）

独立的 C# Web API 服务，为 S5 施工过程智能监管前端提供数据。按 S5 手册要求：
- 接口前缀统一为 `/api/s5/`
- CORS 仅放行前端 `http://localhost:5191`
- 开启 Swagger
- 设备 / 告警实体字段对齐 `packages/m05-twin-ops/backend` 的 `Device.java` / `Alert.java`

> 该后端作为独立服务运行，**不塞进 S5 的 Java 空壳**（`packages/s5-construction-monitor/backend/` 是预留的 Java 服务位置）。

## 技术依赖

- **.NET 8 SDK**（运行时需安装，建议 8.0.x）
- Swashbuckle.AspNetCore 6.5.0（Swagger）
- 当前数据来源：内存种子（`InMemoryTwinDataService`），无外部数据库。
  后续接入 M05 / MySQL 时，只需替换 `ITwinDataService` 的实现，接口契约不变。

## 目录结构

```
twin-csharp/
├─ TwinCsharp/
│  ├─ Program.cs                  # 启动配置：CORS / Swagger / 端口 8091
│  ├─ appsettings.json
│  ├─ Properties/launchSettings.json
│  ├─ Models/                    # Device / Alert / DashboardDto（对齐 m05）
│  ├─ Services/                  # ITwinDataService + 内存种子实现
│  └─ Controllers/               # S5Device / S5Alert / S5Dashboard
└─ twin-csharp.sln
```

## 启动

```bash
cd packages/s5-construction-monitor/twin-csharp
dotnet restore
dotnet run
```

- 监听端口：**8091**
- Swagger 地址：**http://localhost:8091/swagger**
- API 基址：**http://localhost:8091/api/s5**

## 接口列表

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET  | `/api/s5/devices` | 设备列表 |
| GET  | `/api/s5/devices/{code}` | 单个设备（含孪生状态） |
| GET  | `/api/s5/alerts?level=&status=&deviceCode=` | 告警列表（可按级别/状态/设备过滤） |
| GET  | `/api/s5/dashboard` | 施工监测看板聚合数据 |

## 字段对齐说明（与 m05）

- **Device**：id, deviceCode, deviceName, deviceType, stationCode, installTime, status, manufacturer, model, createTime；
  另加孪生扩展 `twin`（temperature / load / runtimeMinutes / lastSync / health）。
- **Alert**：id, deviceId, deviceCode, alertContent, level, status, source, orderNo, createTime, updateTime。
- 枚举约定：`Device.status` 0=离线/1=在线/2=故障；`Alert.level` 1=提示/2=警告/3=严重；`Alert.status` 0=未处理/1=已处理。

## 与 S5 总 README 的差异

- 端口：本服务用 **8091**（避开 Java 后端的 8091）。
- 接口前缀：本服务用 **`/api/s5/`**（按 S5 手册"不要自创前缀"约束）；
  S5 总 README 旧示例写的是 `/api/v1/s5/`，以本服务为准，总 README 后续需统一。
