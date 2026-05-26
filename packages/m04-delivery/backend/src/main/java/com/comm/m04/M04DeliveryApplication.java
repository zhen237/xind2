package com.comm.m04;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.comm.m04.mapper")
public class M04DeliveryApplication {
    public static void main(String[] args) {
        SpringApplication.run(M04DeliveryApplication.class, args);
    }
}
