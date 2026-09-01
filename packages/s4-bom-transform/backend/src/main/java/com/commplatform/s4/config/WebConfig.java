package com.commplatform.s4.config;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web MVC 配置 — CORS 跨域（前端 5190 → 后端 /api/s4/**）。
 * <p>允许来源经 application.yml {@code s4.cors.allowed-origins} 配置。</p>
 */
@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

    private final S4Config s4Config;

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/s4/**")
                .allowedOrigins(s4Config.getCors().getAllowedOrigins().toArray(new String[0]))
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(s4Config.getCors().getMaxAgeSeconds());
    }
}
