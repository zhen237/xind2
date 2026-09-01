package com.commplatform.s4.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

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

    /** CORS 跨域配置 */
    private Cors cors = new Cors();

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
        /** S1 内部接口 X-API-Key（对应 m03.api-key，默认 CHANGE_ME） */
        private String s1ApiKey = "CHANGE_ME";
        private int timeoutSeconds = 15;
    }

    /** CORS 允许来源（默认本地前端 5190）。 */
    @Data
    public static class Cors {
        private List<String> allowedOrigins = new ArrayList<>(
                List.of("http://localhost:5190", "http://127.0.0.1:5190"));
        private long maxAgeSeconds = 3600;
    }

    @Bean
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        int millis = (int) Duration.ofSeconds(engine.getTimeoutSeconds()).toMillis();
        factory.setConnectTimeout(millis);
        factory.setReadTimeout(millis);
        return new RestTemplate(factory);
    }
}
