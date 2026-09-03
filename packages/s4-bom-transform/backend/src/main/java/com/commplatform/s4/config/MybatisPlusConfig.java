package com.commplatform.s4.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * MyBatis-Plus 分页插件。
 *
 * <p>缺失时 {@code Page<>} 不会被织入 LIMIT/COUNT，导致 {@code selectHistoryPage} 这类分页查询
 * 退化为全表返回且 {@code IPage.getTotal()} 恒为 0——前端分页器与"共 N 条"判断失效。
 * 本类对齐 m04 / s3 模块的配置，注册 {@link PaginationInnerInterceptor}(MySQL)。
 */
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
        return interceptor;
    }
}
