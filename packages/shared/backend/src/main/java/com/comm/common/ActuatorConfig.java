package com.comm.common;

import org.springframework.boot.actuate.web.exchanges.HttpExchangeRepository;
import org.springframework.boot.actuate.web.exchanges.InMemoryHttpExchangeRepository;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Actuator 监控配置
 * 提供 httpexchanges 端点所需的 Bean
 */
@Configuration
public class ActuatorConfig {

    /**
     * HTTP 请求追踪仓库（内存实现，保留最近 100 条）
     * 生产环境可替换为数据库存储
     */
    @Bean
    public HttpExchangeRepository httpExchangeRepository() {
        InMemoryHttpExchangeRepository repository = new InMemoryHttpExchangeRepository();
        repository.setCapacity(100);
        return repository;
    }
}
