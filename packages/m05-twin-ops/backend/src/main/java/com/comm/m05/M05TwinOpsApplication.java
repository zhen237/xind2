package com.comm.m05;

import com.comm.security.SecurityAutoConfiguration;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication(exclude = {SecurityAutoConfiguration.class})
@ComponentScan(basePackages = {"com.comm.m05", "com.comm.utils", "com.comm.common"})
@MapperScan("com.comm.m05.mapper")
public class M05TwinOpsApplication {

    public static void main(String[] args) {
        SpringApplication.run(M05TwinOpsApplication.class, args);
    }
}
