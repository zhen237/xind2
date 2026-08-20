package com.commplatform.s4.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 健康检查 - 端口 8090 存活验证。
 */
@RestController
public class HealthController {

    @GetMapping("/api/s4/bom/health")
    public Map<String, Object> health() {
        return Map.of(
                "module", "s4-bom-transform",
                "version", "0.0.1-SNAPSHOT",
                "status", "UP",
                "timestamp", LocalDateTime.now().toString()
        );
    }
}
