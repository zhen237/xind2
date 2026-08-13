package com.comm.m03.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;

/**
 * 内部接口 API Key 鉴权拦截器
 *
 * 作用于 /api/m03/design/**（写/删类内部接口）与 /api/m03/ftth/**（插件成果同步）。
 * QGIS 插件与内部服务调用时必须在请求头携带正确的 X-API-Key，否则返回 401。
 * 这些接口通过 Security 的 permit-paths 放行了 JWT，因此由本拦截器提供内部凭据校验，
 * 避免被公网匿名调用。
 *
 * 只读豁免：{@code m03.api-key-readonly-paths} 列出的路径前缀，其 GET/HEAD 请求免鉴权，
 * 保持「内网只读随便看、写入必须持钥」的既有约定（FTTH 数据集展示就靠这条）。
 */
@Slf4j
@Component
public class DesignApiKeyInterceptor implements HandlerInterceptor {

    @Value("${m03.api-key}")
    private String expectedKey;

    /** 逗号分隔的路径前缀；这些前缀下的 GET/HEAD 免 API Key。 */
    @Value("${m03.api-key-readonly-paths:/api/m03/ftth}")
    private String readOnlyPaths;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws IOException {
        // 放行 CORS 预检(OPTIONS)：浏览器预检不带自定义头，由 CorsFilter 处理跨域，
        // 否则前端跨域调用 /api/m03/design/** 会因预检 401 而整体失败。
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }
        if (isReadOnlyExempt(request)) {
            return true;
        }
        String key = request.getHeader("X-API-Key");
        if (expectedKey != null && expectedKey.equals(key)) {
            return true;
        }
        log.warn("内部接口拒绝访问: 缺少或错误的 X-API-Key, method={} path={}",
                request.getMethod(), request.getRequestURI());
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"code\":401,\"message\":\"Invalid or missing X-API-Key\"}");
        return false;
    }

    private boolean isReadOnlyExempt(HttpServletRequest request) {
        String method = request.getMethod();
        if (!"GET".equalsIgnoreCase(method) && !"HEAD".equalsIgnoreCase(method)) {
            return false;
        }
        if (readOnlyPaths == null || readOnlyPaths.isBlank()) {
            return false;
        }
        String uri = request.getRequestURI();
        for (String prefix : readOnlyPaths.split(",")) {
            String p = prefix.trim();
            if (!p.isEmpty() && uri.startsWith(p)) {
                return true;
            }
        }
        return false;
    }
}
