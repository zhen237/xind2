package com.comm.m03.config;

import com.comm.utils.JwtUtils;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;

/**
 * 大模型接口「JWT 或 X-API-Key」双通道鉴权拦截器
 *
 * 作用于 /api/m03/llm/**。该路径已通过 security.permit-paths 放行 Security 的 JWT 强制校验，
 * 因此由本拦截器决定放行策略，同时支持两类调用方：
 *   通道1：前端 —— 携带 Authorization: Bearer <JWT>，校验签名有效即放行；
 *   通道2：QGIS 插件 / 内部服务 —— 携带 X-API-Key 头，与 m03.api-key 匹配即放行。
 * 两者皆无或皆无效 → 401。CORS 预检(OPTIONS)无条件放行，避免前端跨域调用被阻断。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class LlmAuthInterceptor implements HandlerInterceptor {

    private final JwtUtils jwtUtils;

    @Value("${m03.api-key}")
    private String expectedKey;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws IOException {
        // 放行 CORS 预检(OPTIONS)：浏览器预检不带认证头，由 CorsFilter 处理跨域
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        // 通道1：前端 JWT（Authorization: Bearer <token>），校验签名有效即放行
        String auth = request.getHeader("Authorization");
        if (StringUtils.hasText(auth) && auth.toLowerCase().startsWith("bearer ")) {
            String token = auth.substring(7).trim();
            if (jwtUtils.validateToken(token)) {
                return true;
            }
            log.debug("大模型接口 JWT 校验未通过, path={}", request.getRequestURI());
        }

        // 通道2：QGIS 插件 / 内部服务 X-API-Key
        String key = request.getHeader("X-API-Key");
        if (expectedKey != null && expectedKey.equals(key)) {
            return true;
        }

        log.warn("大模型接口拒绝访问: 缺少有效 JWT 或 X-API-Key, path={}", request.getRequestURI());
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"code\":401,\"message\":\"Unauthorized: valid JWT or X-API-Key required\"}");
        return false;
    }
}
