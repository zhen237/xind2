package com.comm.m04;

import com.comm.security.SecurityAutoConfiguration;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

// 排除共享库安全自动配置：它依赖 com.comm.utils.JwtUtils，与 m04 自带的
// com.comm.m04.utils.JwtUtils 同名冲突（fat jar 下两者都会被扫描）；m04 使用自带 SecurityConfig。
@SpringBootApplication(exclude = {SecurityAutoConfiguration.class})
@ComponentScan(basePackages = {"com.comm.m04"})
@MapperScan("com.comm.m04.mapper")
public class M04DeliveryApplication {
    public static void main(String[] args) {
        SpringApplication.run(M04DeliveryApplication.class, args);
    }
}
