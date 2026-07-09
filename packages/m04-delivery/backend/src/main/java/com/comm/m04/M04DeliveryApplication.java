package com.comm.m04;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"com.comm.m04", "com.comm.utils", "com.comm.common"})
@MapperScan("com.comm.m04.mapper")
public class M04DeliveryApplication {
    public static void main(String[] args) {
        SpringApplication.run(M04DeliveryApplication.class, args);
    }
}
