package com.comm.security;

import com.comm.utils.JwtUtils;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * 统一安全自动配置
 *
 * 各模块只需:
 * 1. 确保 shared-backend 在 classpath 上（已引入）
 * 2. 在 application.yml 中配置 security.permit-paths
 * 3. 如需自定义安全规则，可定义自己的 SecurityFilterChain Bean 覆盖此默认实现
 *
 * 注意: 如果某个模块已经定义了 SecurityFilterChain Bean，
 * 此配置的 @ConditionalOnMissingBean 会自动退让。
 */
@Slf4j
@AutoConfiguration
@RequiredArgsConstructor
@EnableWebSecurity
@EnableConfigurationProperties(SecurityProperties.class)
@ConditionalOnWebApplication
@ConditionalOnClass({JwtUtils.class})
public class SecurityAutoConfiguration {

    private final JwtUtils jwtUtils;
    private final SecurityProperties securityProperties;

    @PostConstruct
    public void init() {
        log.info("Security auto-configuration activated, permit paths: {}", securityProperties.getPermitPaths());
    }

    /**
     * 默认的 SecurityFilterChain
     * 如果模块需要更复杂的规则，定义自己的 Bean 即可（@ConditionalOnMissingBean 自动退让）
     */
    @Bean
    @ConditionalOnMissingBean(SecurityFilterChain.class)
    public SecurityFilterChain defaultSecurityFilterChain(HttpSecurity http) throws Exception {
        String[] permitPaths = securityProperties.getPermitPaths().toArray(new String[0]);

        http.csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(permitPaths).permitAll()
                        .anyRequest().authenticated())
                .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class);

        log.info("Default SecurityFilterChain configured with {} permit paths", permitPaths.length);
        return http.build();
    }

    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter(jwtUtils);
    }
}
