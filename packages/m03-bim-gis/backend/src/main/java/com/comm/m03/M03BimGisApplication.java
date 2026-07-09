package com.comm.m03;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@EnableCaching
@ComponentScan(basePackages = {"com.comm.m03", "com.comm.utils", "com.comm.common"})
@MapperScan({"com.comm.m03.mapper", "com.comm.m03.design.mapper"})
public class M03BimGisApplication {

    public static void main(String[] args) {
        SpringApplication.run(M03BimGisApplication.class, args);
    }
}