# M04 数智化交付模块

## 项目结构

```
m04-delivery/
├── backend/                    # 后端服务
│   ├── src/main/java/com/comm/m04/
│   │   ├── controller/        # REST API 控制层
│   │   ├── service/           # 业务逻辑层
│   │   ├── mapper/            # 数据访问层
│   │   ├── entity/            # 实体类
│   │   ├── config/            # 配置类
│   │   └── common/            # 通用类
│   ├── src/main/resources/
│   │   └── application.yml    # 应用配置
│   └── pom.xml                # Maven 依赖
└── frontend/                  # 前端应用
    ├── src/
    │   ├── views/             # 页面组件
    │   ├── router/            # 路由配置
    │   ├── utils/             # 工具函数
    │   └── components/        # 公共组件
    ├── package.json           # npm 依赖
    └── vite.config.js         # Vite 配置
```

## 技术栈

### 后端
- Java 17
- Spring Boot 3.1.10
- MyBatis-Plus 3.5.5
- Spring Security (JWT)
- MinIO 8.5.3
- MySQL 8.0+

### 前端
- Vue 3.4+
- Vue Router 4.3+
- Element Plus 2.6+
- Axios 1.6+
- Vite 5.1+

## 快速开始

### 1. 数据库配置

创建数据库并执行初始化脚本：

```sql
CREATE DATABASE IF NOT EXISTS comm_platform DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE comm_platform;
```

执行 SQL 脚本：
```bash
mysql -u root -p123456 comm_platform < scripts/init-m04.sql
```

### 2. 启动后端服务

```bash
cd packages/m04-delivery/backend
mvn spring-boot:run
```

服务将在 `http://localhost:8084` 启动。

### 3. 启动前端服务

```bash
cd packages/m04-delivery/frontend
npm install
npm run dev
```

前端将在 `http://localhost:5175` 启动。

## API 接口列表

| 模块 | API 路径 | 说明 |
|------|----------|------|
| 项目管理 | `/api/m04/project` | CRUD 操作 |
| 工单管理 | `/api/m04/work-order` | CRUD 操作 |
| 施工记录 | `/api/m04/construction-record` | CRUD 操作 |
| 验收管理 | `/api/m04/acceptance/task` | 验收任务 |
| 验收管理 | `/api/m04/acceptance/problem` | 验收问题 |
| 交付包管理 | `/api/m04/delivery-package` | CRUD 操作 |

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `m04_project` | 项目信息表 |
| `m04_work_order` | 工单表 |
| `m04_safety_check` | 安全检查表 |
| `m04_cert_verification` | 资质验证表 |
| `m04_construction_record` | 施工记录表 |
| `m04_barrier_check` | 围挡检查表 |
| `m04_electricity_check` | 用电检查表 |
| `m04_delivery_package` | 交付包表 |
| `m04_delivery_file` | 交付文件明细表 |
| `m04_acceptance_task` | 验收任务表 |
| `m04_acceptance_problem` | 验收问题表 |

## 核心功能

### 1. 项目管理
- 项目信息的增删改查
- 项目进度跟踪
- 项目统计报表

### 2. 工单管理
- 工单创建与派发
- 工单状态流转（待处理→处理中→已完成→已关闭）
- 工单优先级管理

### 3. 施工记录
- 施工任务记录
- 施工人员管理
- 环境评估与危险源描述

### 4. 验收管理
- 验收任务创建与分配
- 验收问题记录与整改闭环
- 验收统计报表

### 5. 交付包管理
- 交付包创建与打包
- 文件归档至 MinIO
- 交付包状态管理