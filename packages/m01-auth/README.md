# M01 — 统一认证服务

**类型**: Java Spring Boot 微服务
**端口**: 8080
**归属**: 共享基础设施
**维护人**: 高

## 职责

- 用户认证（登录/登出）
- JWT 签发与验证
- 用户管理（CRUD）
- 角色与菜单管理

## 启动

```bash
cd packages/m01-auth/backend
mvn spring-boot:run
```

## 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/m01/auth/login | 登录，返回 JWT |
| GET | /api/m01/auth/user/info | 获取当前用户信息 |
| GET | /api/m01/auth/menus | 获取动态菜单 |

## 依赖

- MySQL: `comm_platform` 数据库，表前缀 `m01_`
- 无外部模块依赖（shared 除外）

## 配置

- 启动前确保 MySQL 已运行
- 默认端口 8080，通过 `SERVER_PORT` 环境变量修改
- JWT Secret 通过 `JWT_SECRET` 环境变量设置
- 数据库表由 `scripts/init-mysql.sql` 初始化
