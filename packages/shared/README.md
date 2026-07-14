# shared — 共享基础设施

**类型**: Java 库模块（不可独立运行）
**归属**: 共享（所有人调用，不归属任何赛题）
**维护人**: 高（修改需 PR + review）

## 职责

提供所有后端模块的公共能力：

- `com.comm.common` — 统一响应（`Result<T>`）、全局异常处理（`GlobalExceptionHandler`）、业务异常（`BusinessException`）、缓存配置
- `com.comm.security` — JWT 鉴权过滤器（`JwtAuthenticationFilter`）、安全自动配置（`SecurityAutoConfiguration`）
- `com.comm.utils` — JWT 工具类（`JwtUtils`）
- `application-shared.yml` — 共享配置（Redis/JWT/Actuator，各模块通过 `spring.config.import` 引入）

## 使用方法

```xml
<!-- 各模块 pom.xml -->
<dependency>
    <groupId>com.comm</groupId>
    <artifactId>shared-backend</artifactId>
</dependency>
```

```yaml
# 各模块 application.yml
spring:
  config:
    import:
      - classpath:application-shared.yml
```

## 修改流程

1. 在 `feature/shared-xxx` 分支修改
2. 提 PR，标注影响的模块
3. 高 review 通过后合并
4. 通知受影响模块负责人拉取最新代码

## 禁止事项

- 禁止在 shared 中添加业务逻辑
- 禁止修改 `SecurityAutoConfiguration` 而不通知所有人
- 修改 `application-shared.yml` 前评估对全部模块的影响
