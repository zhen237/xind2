package com.comm.security;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * 统一安全配置属性
 * 各模块在 application.yml 中配置自己的放行路径
 *
 * 示例:
 * <pre>
 * security:
 *   permit-paths:
 *     - /api/m01/auth/login
 *     - /api/m01/health/**
 * </pre>
 */
@Data
@Component
@ConfigurationProperties(prefix = "security")
public class SecurityProperties {

    /**
     * 无需认证的路径列表（Ant 风格匹配）
     * 默认放行健康检查端点
     */
    private List<String> permitPaths = new ArrayList<>();

    public SecurityProperties() {
        // 默认放行路径
        permitPaths.add("/api/**/health/**");
    }
}
