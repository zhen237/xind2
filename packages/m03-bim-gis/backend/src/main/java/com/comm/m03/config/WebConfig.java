package com.comm.m03.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Arrays;
import java.util.List;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final DesignApiKeyInterceptor apiKeyInterceptor;
    private final LlmAuthInterceptor llmAuthInterceptor;

    public WebConfig(DesignApiKeyInterceptor apiKeyInterceptor, LlmAuthInterceptor llmAuthInterceptor) {
        this.apiKeyInterceptor = apiKeyInterceptor;
        this.llmAuthInterceptor = llmAuthInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // design 写删接口：内部 API Key 鉴权
        registry.addInterceptor(apiKeyInterceptor)
                .addPathPatterns("/api/m03/design/**");
        // llm 接口：JWT 或 X-API-Key 双通道鉴权（前端走 JWT，QGIS/内部服务走 X-API-Key）
        registry.addInterceptor(llmAuthInterceptor)
                .addPathPatterns("/api/m03/llm/**");
    }

    @Bean
    public CorsFilter corsFilter(@Value("${cors.allowed-origins:http://localhost:9000,http://localhost:8080,http://127.0.0.1:9000}") String allowedOrigins) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowCredentials(true);
        List<String> origins = Arrays.asList(allowedOrigins.split(","));
        config.setAllowedOrigins(origins);
        config.setAllowedHeaders(Arrays.asList("*"));
        config.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        config.setExposedHeaders(Arrays.asList("Authorization"));

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
