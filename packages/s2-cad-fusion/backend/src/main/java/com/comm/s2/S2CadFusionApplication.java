package com.comm.s2;

import com.comm.security.SecurityAutoConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(exclude = {SecurityAutoConfiguration.class})
public class S2CadFusionApplication {
    public static void main(String[] args) {
        SpringApplication.run(S2CadFusionApplication.class, args);
    }
}
