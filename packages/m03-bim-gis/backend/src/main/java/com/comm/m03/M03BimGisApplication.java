package com.comm.m03;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.comm.m03.mapper")
public class M03BimGisApplication {

    public static void main(String[] args) {
        SpringApplication.run(M03BimGisApplication.class, args);
    }
}