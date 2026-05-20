package com.comm.m01;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.comm.m01.mapper")
public class M01AuthApplication {

    public static void main(String[] args) {
        SpringApplication.run(M01AuthApplication.class, args);
    }
}
