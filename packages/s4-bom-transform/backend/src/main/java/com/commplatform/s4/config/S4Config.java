package com.commplatform.s4.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/**
 * S4 模块专属配置。
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "s4")
public class S4Config {

    /** Python BOM 引擎配置 */
    private Engine engine = new Engine();

    /** BOM 导出配置 */
    private Export export = new Export();

    /** 跨赛题集成配置（S1/S3/S5） */
    private Integration integration = new Integration();

    @Data
    public static class Engine {
        private String url = "http://localhost:8100";
        private int timeoutSeconds = 60;
        private int retry = 1;
    }

    @Data
    public static class Export {
        private String storage = "local";
        private String localPath = "./exports/bom";
    }

    /**
     * 跨赛题集成（闭合 FR-10 审查闸门 + I4 S5 推送契约）。
     * <p>
     * dataSource: mock | real
     *   mock — 指向 dev-proxy（默认 8090），由 dev-proxy 模拟 S1/S3/S5
     *   real — 指向 S1/S3/S5 各子题真实服务地址
     */
    @Data
    public static class Integration {
        private String dataSource = "mock";
        private String s1Url = "http://localhost:8090";
        private String s3Url = "http://localhost:8090";
        private String s5Url = "http://localhost:8090";
        private String authToken = "";
        private int timeoutSeconds = 15;
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplateBuilder()
                .connectTimeout(Duration.ofSeconds(engine.getTimeoutSeconds()))
                .readTimeout(Duration.ofSeconds(engine.getTimeoutSeconds()))
                .build();
    }
}
