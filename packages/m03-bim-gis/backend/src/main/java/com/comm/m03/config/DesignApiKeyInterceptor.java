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
 * 仅作用于 /api/m03/design/**（写/删类内部接口）。QGIS 插件与内部服务调用时
 * 必须在请求头携带正确的 X-API-Key，否则返回 401。这些接口通过 Security 的
 * permit-paths 放行了 JWT，因此由本拦截器提供内部凭据校验，避免被公网匿名调用。
 */
@Slf4j
@Component
public class DesignApiKeyInterceptor implements HandlerInterceptor {

    @Value("${m03.api-key}")
    private String expectedKey;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws IOException {
        // 放行 CORS 预检(OPTIONS)：浏览器预检不带自定义头，由 CorsFilter 处理跨域，
        // 否则前端跨域调用 /api/m03/design/** 会因预检 401 而整体失败。
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }
        String key = request.getHeader("X-API-Key");
        if (expectedKey != null && expectedKey.equals(key)) {
            return true;
        }
        log.warn("设计接口拒绝访问: 缺少或错误的 X-API-Key, path={}", request.getRequestURI());
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"code\":401,\"message\":\"Invalid or missing X-API-Key\"}");
        return false;
    }
}
