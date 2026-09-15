package com.comm.screen;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import com.comm.security.SecurityAutoConfiguration;

/**
 * 大屏模块启动类。
 *
 * exclude = SecurityAutoConfiguration 是必须的：shared-backend 通过
 * META-INF/spring/...AutoConfiguration.imports 把 SecurityAutoConfiguration 注册为
 * 全局自动配置，它 @ConditionalOnClass({com.comm.utils.JwtUtils.class}) 在类路径上恒为真，
 * 但其构造器强依赖 com.comm.utils.JwtUtils 这个 bean。本模块的组件扫描根是
 * com.comm.screen，不覆盖 com.comm.utils，也没有同名 bean（本模块自带的
 * com.comm.screen.utils.JwtUtils 是另一个类型），于是启动即失败：
 *   Parameter 0 of constructor in com.comm.security.SecurityAutoConfiguration
 *   required a bean of type 'com.comm.utils.JwtUtils' that could not be found.
 * 本模块后端仅本地调用、无公网路由，不需要 JWT 鉴权，故直接排除。
 * 与 m04-delivery / m05-twin-ops / s2-cad-fusion 的处理方式保持一致。
 */
@SpringBootApplication(exclude = {SecurityAutoConfiguration.class})
public class ScreenApplication {
    public static void main(String[] args) {
        SpringApplication.run(ScreenApplication.class, args);
    }
}
