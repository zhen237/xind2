# M05 — 数字孪生与智慧运维

**类型**: Java Spring Boot 微服务
**端口**: 8085
**归属**: S5 — 施工过程智能监管
**负责人**: 李

## 职责

- 设备状态实时监控
- 告警管理
- MQTT 消息接入（EMQX）
- 时序数据存储（InfluxDB）

## 启动

```bash
cd packages/m05-twin-ops/backend
mvn spring-boot:run
```

## 依赖

- **MySQL**: 表前缀 `m05_`，Flyway 表 `flyway_schema_history_m05`
- **Redis**: 缓存设备状态
- **InfluxDB**: 端口 8086，遥测时序数据
- **EMQX MQTT**: 端口 1883，设备消息
- **MinIO**: 文件存储

## 配置

```env
MQTT_BROKER=tcp://localhost:1883
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=my-super-token
INFLUXDB_ORG=comm
INFLUXDB_BUCKET=telemetry
```

## 前端

前端目录存在但为空骨架（暂未开发）。S5 施工监管大屏功能在 s5-construction-monitor 中开发。
