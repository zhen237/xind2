package com.comm.m05;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.comm.m05.mapper")
public class M05TwinOpsApplication {

    public static void main(String[] args) {
        SpringApplication.run(M05TwinOpsApplication.class, args);
    }
}
