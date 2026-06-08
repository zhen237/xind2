# AI协作开发隔离指南

## 核心原则

五个人各自使用AI开发，通过**文件夹物理隔离**保证互不影响。每个人只需把自己的模块文件夹拖给AI，AI的修改范围天然受限。

## 一、文件夹隔离结构

```
xind2/
├── packages/
│   ├── m01-auth/          ← 人员一专属（认证中心）
│   │   └── backend/       ← 只有后端，无前端
│   │
│   ├── m03-bim-gis/       ← 人员二专属（3D孪生建模）
│   │   ├── backend/
│   │   └── frontend/
│   │
│   ├── m04-delivery/      ← 人员四专属（项目进程+视频监理）
│   │   ├── backend/
│   │   └── frontend/
│   │
│   ├── m05-twin-ops/      ← 人员三专属（智慧运维）
│   │   ├── backend/
│   │   └── frontend/
│   │
│   ├── m06-portal/        ← 门户（由最熟练者维护）
│   │
│   └── screen/            ← 人员五专属（数字大屏）
│       ├── backend/
│       └── frontend/
│
├── scripts/               ← 共享脚本（init-db.sql 等）
├── docs/                  ← 共享文档
└── docker-compose.yml     ← 共享基础设施
```

**关键规则：五个 packages 下的模块目录互相不引用、不依赖、不 import。**

## 二、AI使用方式

### 正确做法：把模块文件夹作为工作目录

每个人打开自己模块的文件夹作为AI工作目录：

| 人员 | AI工作目录 |
|------|-----------|
| 人员一 | `packages/m01-auth/` |
| 人员二 | `packages/m03-bim-gis/` |
| 人员三 | `packages/m05-twin-ops/` |
| 人员四 | `packages/m04-delivery/` |
| 人员五 | `packages/screen/` |

### 给AI的提示词示例

```
在当前目录下开发 xxx 功能。
后端代码在 backend/ 下，前端代码在 frontend/ 下。
不要修改其他目录的文件。
```

这样AI的视野和修改范围就被限定在你的模块内。

### 错误做法

- ❌ 以 `xind2/` 作为工作目录——AI可能修改别人的代码
- ❌ 在代码中 import 别的模块的类或组件
- ❌ 直接修改 `shared_` 开头的数据库表

## 三、隔离的具体规则

### 3.1 后端隔离

每个模块：
- 独立的 `pom.xml`（独立编译运行）
- 独立的包路径 `com.comm.m01` / `com.comm.m03` / ...
- 独立的 `application.yml` 配置
- 独立的端口（8080 / 8083 / 8084 / 8085 / 8087）
- 独立的数据库表前缀（m01_ / m03_ / m04_ / m05_）

```java
// ✅ 正确：只在自己的包路径下写代码
package com.comm.m04.controller;  // 人员四的代码

// ❌ 错误：跨模块引用
import com.comm.m03.entity.Device;  // 不要这样做
```

### 3.2 前端隔离

每个模块：
- 独立的 `package.json` 和 `node_modules`
- 独立的 `vite.config.js`（独立端口 5174-5177）
- 独立的 `src/` 目录
- 通过 iframe 嵌入 M06 门户，不直接引用其他模块组件

```javascript
// ✅ 正确：M03 前端的 router
{ path: '/design', component: () => import('@/views/Design.vue') }

// ❌ 错误：跨模块引用
import CesiumViewer from '../../../m06-portal/src/components/CesiumViewer.vue'
```

### 3.3 数据库隔离

每个模块的表使用自己的前缀，互不写入对方的表：

| 模块 | 表前缀 | 权限 |
|------|--------|------|
| M01 | `m01_` | 读写自己的表 |
| M03 | `m03_` | 读写自己的表 |
| M04 | `m04_` | 读写自己的表 |
| M05 | `m05_` | 读写自己的表 |
| 共享 | `shared_` | **所有模块只读** |

```sql
-- ✅ 正确：M04 建表
CREATE TABLE m04_project (...);

-- ❌ 错误：M04 修改 M03 的表
ALTER TABLE m03_device ADD COLUMN ...;  -- 不要这样做
```

### 3.4 跨模块通信方式

唯一允许的跨模块交互方式：

1. **API 调用**：通过 HTTP 调用其他模块的接口
2. **数据库只读**：读取 `shared_` 表和已约定的其他模块表

```
人员五（大屏）→ GET /api/m04/project  → 获取项目进度
人员五（大屏）→ GET /api/m05/device   → 获取设备状态
人员三（M05） → 写入 m04_work_order   → 生成工单（约定的接口）
```

## 四、Git 协作规范

### 提交前检查清单

- [ ] 只修改了自己模块 `packages/mXX/` 下的文件
- [ ] 如果改了共享文件（scripts/、docs/、docker-compose.yml），已在团队内同步
- [ ] 没有意外的 `import` 跨模块引用
- [ ] 前端 `vite.config.js` 的 proxy 目标端口正确

### 冲突处理

共享文件只有这几个，改之前打个招呼：
- `scripts/init-db.sql` — 数据库建表脚本
- `docker-compose.yml` — 基础设施
- `docs/` — 文档

你自己的模块目录 (`packages/mXX/`) 不会和别人冲突，放心改。

## 五、快速验证

每个人启动自己的服务即可独立开发，不需要等别人：

```bash
# 人员二开发 M03 前端，只需要：
cd packages/m03-bim-gis/frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5174

# 人员四开发 M04 后端，只需要：
cd packages/m04-delivery/backend
mvn spring-boot:run
# 服务运行在 http://localhost:8084
```

不需要启动 M06 门户也能独立开发调试自己的页面。联调时再走门户的 iframe 集成。

---

**一句话总结：每个人只在自己的 `packages/mXX/` 目录下工作，AI 也只看到这个目录，天然隔离。**
