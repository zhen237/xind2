package com.comm.s3;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

// 必须扫描 com.comm.utils 以加载 shared 的 JwtUtils bean（SecurityAutoConfiguration 强依赖它）。
// 该扫描曾在 PR #15 加入，S3 功能分支 921ddee 误删导致合并后 s3 启动报缺 JwtUtils bean。
@ComponentScan(basePackages = {"com.comm.s3", "com.comm.utils"})
@SpringBootApplication
public class S3ReviewApplication {
    public static void main(String[] args) {
        SpringApplication.run(S3ReviewApplication.class, args);
    }
}
