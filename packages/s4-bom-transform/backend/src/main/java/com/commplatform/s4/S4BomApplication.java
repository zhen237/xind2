package com.commplatform.s4;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * S4 BOM 转化后端入口。
 * <p>
 * 端口: 8090 | 数据库: comm_platform (s4_ 前缀)
 * </p>
 */
@SpringBootApplication
@MapperScan("com.commplatform.s4.mapper")
@EnableAsync
public class S4BomApplication {

    public static void main(String[] args) {
        SpringApplication.run(S4BomApplication.class, args);
    }
}
