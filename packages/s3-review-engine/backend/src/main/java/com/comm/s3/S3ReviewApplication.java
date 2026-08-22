package com.comm.s3;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

// 临时本地补丁：shared 的 JwtUtils(@Component, com.comm.utils) 未被自动配置提供，
// 需消费方显式扫描该包，否则 SecurityAutoConfiguration 因缺 JwtUtils bean 启动失败。
// 正式修复应在 shared 的 AutoConfiguration 中以 @Bean 提供 JwtUtils。
@ComponentScan(basePackages = {"com.comm.s3", "com.comm.utils"})
@SpringBootApplication
public class S3ReviewApplication {
    public static void main(String[] args) {
        SpringApplication.run(S3ReviewApplication.class, args);
    }
}
