package com.comm.security;

import com.comm.utils.JwtUtils;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;
import java.util.List;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

/**
 * 统一 JWT 认证过滤器
 *
 * 功能:
 * 1. 从 Authorization 头提取 Bearer token
 * 2. 验证 token 有效性
 * 3. 将用户信息设置到 SecurityContextHolder（供 @PreAuthorize 等使用）
 * 4. 将 userId 设置到 request attribute（供 Controller 直接读取）
 * 5. token 无效时不阻断请求，交由 SecurityConfig 的 .authenticated() 决策
 */
@Slf4j
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtUtils jwtUtils;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        String authHeader = request.getHeader("Authorization");

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);

            if (jwtUtils.validateToken(token)) {
                Long userId = jwtUtils.getUserIdFromToken(token);
                String username = jwtUtils.getUsernameFromToken(token);

                // 设置 request attribute（向后兼容旧代码中 request.getAttribute("userId")）
                request.setAttribute("userId", userId);
                request.setAttribute("username", username);

                // 从 JWT 提取角色，填充 Authority（支持 @PreAuthorize 方法级授权）
                List<String> roles = jwtUtils.getRolesFromToken(token);
                List<SimpleGrantedAuthority> authorities = roles.stream()
                        .map(SimpleGrantedAuthority::new)
                        .toList();

                // 设置 SecurityContext（支持 Spring Security 注解授权）
                UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(userId, null, authorities);
                authentication.setDetails(username);
                SecurityContextHolder.getContext().setAuthentication(authentication);
            } else {
                log.warn("JWT token validation failed for request: {} {}", request.getMethod(), request.getRequestURI());
            }
        }

        filterChain.doFilter(request, response);
    }
}
