package com.comm.screen.controller;

import com.comm.common.Result;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.*;

/**
 * 大屏中心数据聚合 API
 * 通过调用各模块 REST API 获取数据，不再直接查询数据库
 */
@RestController
@RequestMapping("/api/screen")
public class ScreenController {

    private final RestTemplate restTemplate;

    @Value("${screen.m04-base-url:http://localhost:8084}")
    private String m04BaseUrl;

    @Value("${screen.m05-base-url:http://localhost:8085}")
    private String m05BaseUrl;

    public ScreenController() {
        this.restTemplate = new RestTemplate();
    }

    /** 运维总览大屏数据 */
    @GetMapping("/ops-overview")
    public Result<Map<String, Object>> opsOverview() {
        Map<String, Object> data = new LinkedHashMap<>();

        // 调用 M05: 设备统计
        Map<String, Object> deviceStats = callM05("/api/m05/internal/screen/device-stats");
        int deviceTotal = getInt(deviceStats, "deviceTotal");
        int onlineDevices = getInt(deviceStats, "deviceOnline");
        int offlineDevices = getInt(deviceStats, "deviceOffline");
        int faultDevices = getInt(deviceStats, "deviceFault");

        data.put("deviceTotal", deviceTotal);
        data.put("deviceOnline", onlineDevices);
        data.put("deviceOffline", offlineDevices);
        data.put("deviceFault", faultDevices);
        data.put("deviceOnlineRate", deviceTotal > 0
                ? Math.round(onlineDevices * 10000.0 / deviceTotal) / 100.0 : 0);

        // 调用 M05: 告警统计
        Map<String, Object> alertStats = callM05("/api/m05/internal/screen/alert-stats");
        data.put("alertTotal", getInt(alertStats, "alertTotal"));
        data.put("alertUnprocessed", getInt(alertStats, "alertUnprocessed"));
        data.put("alertConfirmed", getInt(alertStats, "alertConfirmed"));
        data.put("alertResolved", getInt(alertStats, "alertResolved"));

        // 调用 M04: 工单统计
        Map<String, Object> woStats = callM04("/api/m04/internal/screen/work-order-stats");
        data.put("workOrderPending", getInt(woStats, "workOrderPending"));
        data.put("workOrderProcessing", getInt(woStats, "workOrderProcessing"));
        data.put("workOrderDone", getInt(woStats, "workOrderDone"));

        // 调用 M04: 项目统计
        Map<String, Object> projectStats = callM04("/api/m04/internal/screen/project-stats");
        int projectTotal = getInt(projectStats, "projectTotal");
        int projectCompleted = getInt(projectStats, "projectCompleted");
        data.put("projectTotal", projectTotal);
        data.put("projectCompleted", projectCompleted);
        data.put("projectCompletionRate", projectTotal > 0
                ? Math.round(projectCompleted * 10000.0 / projectTotal) / 100.0 : 0);

        return Result.success(data);
    }

    /** 告警监控大屏数据 */
    @GetMapping("/alert-monitor")
    public Result<Map<String, Object>> alertMonitor() {
        Map<String, Object> data = new LinkedHashMap<>();

        data.put("alertByLevel", callM05List("/api/m05/internal/screen/alert-by-level"));
        data.put("recentAlerts", callM05List("/api/m05/internal/screen/recent-alerts"));
        data.put("topAlertDevices", callM05List("/api/m05/internal/screen/top-alert-devices"));
        data.put("alertTrend", callM05List("/api/m05/internal/screen/alert-trend"));

        return Result.success(data);
    }

    /** 项目进度大屏数据 */
    @GetMapping("/project-progress")
    public Result<Map<String, Object>> projectProgress() {
        Map<String, Object> data = new LinkedHashMap<>();

        data.put("projectsByPhase", callM04List("/api/m04/internal/screen/project-by-phase"));
        data.put("projects", callM04List("/api/m04/internal/screen/project-list"));
        data.put("delayedProjects", callM04List("/api/m04/internal/screen/delayed-projects"));

        return Result.success(data);
    }

    /** 能耗分析大屏数据 */
    @GetMapping("/energy-analysis")
    public Result<Map<String, Object>> energyAnalysis() {
        Map<String, Object> data = new LinkedHashMap<>();

        data.put("deviceTypeDistribution", callM05List("/api/m05/internal/screen/device-type-distribution"));
        data.put("stationDeviceCount", callM05List("/api/m05/internal/screen/station-device-count"));

        return Result.success(data);
    }

    /** 站点GIS数据（用于热力图） */
    @GetMapping("/station-gis")
    public Result<List<Map<String, Object>>> stationGis() {
        // 站点数据来自 shared_station 表，M05 可代理
        List<Map<String, Object>> stations = callM05List("/api/m05/internal/screen/station-device-count");
        return Result.success(stations);
    }

    // ==================== 内部 HTTP 调用工具方法 ====================

    @SuppressWarnings("unchecked")
    private Map<String, Object> callM04(String path) {
        try {
            ResponseEntity<Map<String, Object>> resp = restTemplate.exchange(
                    m04BaseUrl + path,
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            );
            Map<String, Object> body = resp.getBody();
            if (body != null && body.get("data") instanceof Map) {
                return (Map<String, Object>) body.get("data");
            }
        } catch (Exception e) {
            // 服务不可用时返回空数据，避免大屏白屏
        }
        return Collections.emptyMap();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> callM05(String path) {
        try {
            ResponseEntity<Map<String, Object>> resp = restTemplate.exchange(
                    m05BaseUrl + path,
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            );
            Map<String, Object> body = resp.getBody();
            if (body != null && body.get("data") instanceof Map) {
                return (Map<String, Object>) body.get("data");
            }
        } catch (Exception e) {
            // 服务不可用时返回空数据
        }
        return Collections.emptyMap();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> callM04List(String path) {
        try {
            ResponseEntity<Map<String, Object>> resp = restTemplate.exchange(
                    m04BaseUrl + path,
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            );
            Map<String, Object> body = resp.getBody();
            if (body != null && body.get("data") instanceof List) {
                return (List<Map<String, Object>>) body.get("data");
            }
        } catch (Exception e) {
            // 服务不可用时返回空列表
        }
        return Collections.emptyList();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> callM05List(String path) {
        try {
            ResponseEntity<Map<String, Object>> resp = restTemplate.exchange(
                    m05BaseUrl + path,
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            );
            Map<String, Object> body = resp.getBody();
            if (body != null && body.get("data") instanceof List) {
                return (List<Map<String, Object>>) body.get("data");
            }
        } catch (Exception e) {
            // 服务不可用时返回空列表
        }
        return Collections.emptyList();
    }

    private int getInt(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        return 0;
    }
}
