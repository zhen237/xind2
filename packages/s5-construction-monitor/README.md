# S5 — 施工过程智能监管

**类型**: Java Spring Boot + Vue 3（新建）
**端口**: 后端 8091 / 前端 5191
**归属**: S5 — 施工过程智能监管
**负责人**: 李

## 职责

- 施工过程实时监管
- 安全帽/围挡 AI 检测（调用 M07 CV 引擎）
- 施工进度跟踪
- 告警与事件管理
- 施工监管大屏
- 从 M04 迁移施工记录代码（ConstructionRecord）

## 启动

```bash
# 后端（两种实现二选一，接口契约相同：/api/s5/*，端口 8092，同一端口不能同时启动）

# 方式一：Node.js（免安装，推荐日常演示，需 Node 18+）
cd packages/s5-construction-monitor/backend-node
npm install && npm start              # → http://localhost:8092

# 方式二：C# .NET 8（需 .NET 8 SDK）
cd packages/s5-construction-monitor/twin-csharp/TwinCsharp
dotnet run                            # → http://localhost:8092（Swagger: /swagger/index.html）

# 前端
cd packages/s5-construction-monitor/frontend
npm install && npm run dev            # → http://localhost:5191（/api/s5 代理到 8092）
```

## 依赖

- **M01 Auth**: JWT 鉴权
- **M05 Twin Ops**: 设备状态/告警数据
- **M07 CV Engine**: AI 视觉检测结果
- **S4 REST API**: 接收施工指令（接口契约见技术架构与开发规范 §5.5）
- **MySQL**: 表前缀 `s5_`，Flyway 表 `flyway_schema_history_s5`

## API 约定

```
POST /api/v1/s5/monitor/plan       # 创建监管计划
GET  /api/v1/s5/monitor/progress   # 施工进度
GET  /api/v1/s5/monitor/alerts     # 实时告警
GET  /api/v1/s5/screen-data        # 大屏数据接口
```

## M04 迁移清单

从 M04 迁移以下代码到 S5：
- ConstructionRecordController/ConstructionRecord
- VideoSurveillanceController
- 对应 Service/Mapper
- 前端 views/ConstructionRecord.vue

## 已补充：C# 孪生后端与前端（本仓库 S5 实测补充）

- **C# 后端 `twin-csharp/`**：.NET 8 ASP.NET Web API，接口前缀 `/api/s5/`，端口 **8092**，CORS 放行 `http://localhost:5191`，已开 Swagger。设备/告警字段对齐 `m05-twin-ops` 的 `Device.java` / `Alert.java`。启动见 `twin-csharp/README.md`。
- **Node 后端 `backend-node/`（免安装替代版）**：Express，接口/端口/CORS 与 C# 版完全一致（含 dashboard/devices/alerts 过滤、404），种子数据从 `InMemoryTwinDataService.cs` 移植，无需 .NET SDK，Node 18+ 即可 `npm start`。
- **前端 `frontend/`**：Vite + Vue3 + Element Plus，端口 **5191**，`/api/s5` 代理到 8092，三页（施工监测看板 / 设备孪生状态 / 告警列表）真实调用后端。
- **数字孪生 `lianxi/`**：Unity 2022.3.62f3c1 工程（3D 客户端，非 Web 后端），与本地 `C:\Users\李\lianxi` 一致（仓库副本不含 `Assets/model/备份/` 下的历史 fbx 备份）。
- **数字孪生页面 `frontend/src/views/TwinView.vue`**：前端 `/twin` 页自动嵌入 Unity WebGL 构建产物；无产物时显示构建指引占位。

### WebGL 构建与嵌入（把 3D 孪生放进网页）

1. 在装有 **Unity 2022.3.62f3c1 + WebGL Build Support 模块**的机器上打开 `lianxi/` 工程
2. 菜单 **Build → S5 → 构建 WebGL（数字孪生）**（脚本：`lianxi/Assets/Editor/S5WebGLBuilder.cs`），
   输出目录选仓库的 `packages/s5-construction-monitor/frontend/public/twin-webgl`
3. 或命令行构建：`Unity -batchmode -quit -projectPath <lianxi路径> -executeMethod S5WebGLBuilder.Build`
4. 启动前端后访问 **http://localhost:5191/twin**，3D 场景直接嵌入显示
5. 构建产物（`index.html` + `Build/` + `TemplateData/`）随仓库提交即可

> 说明：产物目录约定为 `frontend/public/twin-webgl/`（Unity 标准结构：`Build/twin-webgl.loader.js`、`twin-webgl.data.gz`、`twin-webgl.wasm.gz`、`twin-webgl.framework.js.gz`），
> 页面通过探测 `Build/twin-webgl.loader.js`（content-type 非 text/html）判断是否已构建。
> 本仓库已附带构建好的产物（2026-09-01，约 165MB），clone 后直接启动前端即可看到孪生场景。

> 注意：本文档旧版 API 示例写的是 `/api/v1/s5/`，实际 C# 服务统一使用 `/api/s5/`（按 S5 手册"不要自创前缀"约束），以 `twin-csharp/` 与 `backend-node/` 为准。
> 2026-09-01 修复：`twin-csharp` 的 `ITwinDataService.cs` 缺少 `using TwinCsharp.Models;` 导致编译失败，已补上；安装 .NET 8 SDK 后 `dotnet run` 验证通过。
