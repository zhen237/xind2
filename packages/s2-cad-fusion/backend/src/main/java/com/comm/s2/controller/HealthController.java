package com.comm.s2.controller;

import com.comm.s2.common.Result;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 服务健康检查接口。
 */
@RestController
@RequestMapping("/api/s2/cad")
public class HealthController {

    @Value("${spring.application.name:s2-cad-fusion}")
    private String applicationName;

    @GetMapping("/health")
    public Result<Map<String, Object>> health() {
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("service", "s2-cad-fusion");
        info.put("applicationName", applicationName);
        info.put("module", "多源异构数据融合服务（CAD→GIS）");
        info.put("status", "UP");
        info.put("time", LocalDateTime.now().toString());
        return Result.success("服务正常", info);
    }
}
