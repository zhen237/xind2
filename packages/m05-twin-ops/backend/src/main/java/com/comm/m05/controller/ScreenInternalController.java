package com.comm.m05.controller;

import com.comm.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.*;

/**
 * M05 内部数据聚合 API（供 Screen 大屏调用）
 * 通过 Nginx 内网代理访问，不对外暴露
 */
@RestController
@RequestMapping("/api/m05/internal/screen")
public class ScreenInternalController {

    @Autowired
    private JdbcTemplate jdbc;

    /** 设备统计数据 */
    @GetMapping("/device-stats")
    @Cacheable(value = "longCache", key = "'m05:device-stats'")
    public Result<Map<String, Object>> deviceStats() {
        Map<String, Object> stats = jdbc.queryForMap(
                "SELECT " +
                "  (SELECT COUNT(*) FROM m05_device) as deviceTotal, " +
                "  (SELECT COUNT(*) FROM m05_device WHERE status = 1) as deviceOnline, " +
                "  (SELECT COUNT(*) FROM m05_device WHERE status = 0) as deviceOffline, " +
                "  (SELECT COUNT(*) FROM m05_device WHERE status = 2) as deviceFault"
        );
        return Result.success(stats);
    }

    /** 设备类型分布 */
    @GetMapping("/device-type-distribution")
    public Result<List<Map<String, Object>>> deviceTypeDistribution() {
        List<Map<String, Object>> distribution = jdbc.queryForList(
                "SELECT device_type, COUNT(*) as count FROM m05_device GROUP BY device_type");
        return Result.success(distribution);
    }

    /** 基站设备数量 */
    @GetMapping("/station-device-count")
    public Result<List<Map<String, Object>>> stationDeviceCount() {
        List<Map<String, Object>> data = jdbc.queryForList(
                "SELECT d.station_code, s.station_name, COUNT(*) as count " +
                "FROM m05_device d LEFT JOIN shared_station s ON d.station_code = s.station_code " +
                "GROUP BY d.station_code, s.station_name");
        return Result.success(data);
    }

    /** 告警统计数据 */
    @GetMapping("/alert-stats")
    @Cacheable(value = "longCache", key = "'m05:alert-stats'")
    public Result<Map<String, Object>> alertStats() {
        Map<String, Object> stats = jdbc.queryForMap(
                "SELECT " +
                "  (SELECT COUNT(*) FROM m05_alert) as alertTotal, " +
                "  (SELECT COUNT(*) FROM m05_alert WHERE status = 0) as alertUnprocessed, " +
                "  (SELECT COUNT(*) FROM m05_alert WHERE status = 1) as alertConfirmed, " +
                "  (SELECT COUNT(*) FROM m05_alert WHERE status = 2) as alertResolved"
        );
        return Result.success(stats);
    }

    /** 告警按级别分布 */
    @GetMapping("/alert-by-level")
    public Result<List<Map<String, Object>>> alertByLevel() {
        List<Map<String, Object>> data = jdbc.queryForList(
                "SELECT level, COUNT(*) as count FROM m05_alert GROUP BY level ORDER BY level");
        return Result.success(data);
    }

    /** 最近告警 */
    @GetMapping("/recent-alerts")
    public Result<List<Map<String, Object>>> recentAlerts() {
        List<Map<String, Object>> data = jdbc.queryForList(
                "SELECT id, device_code, alert_content, level, status, source, create_time " +
                "FROM m05_alert ORDER BY create_time DESC LIMIT 20");
        return Result.success(data);
    }

    /** 告警设备 TOP10 */
    @GetMapping("/top-alert-devices")
    public Result<List<Map<String, Object>>> topAlertDevices() {
        List<Map<String, Object>> data = jdbc.queryForList(
                "SELECT device_code, COUNT(*) as count FROM m05_alert GROUP BY device_code ORDER BY count DESC LIMIT 10");
        return Result.success(data);
    }

    /** 告警趋势（近7天） */
    @GetMapping("/alert-trend")
    public Result<List<Map<String, Object>>> alertTrend() {
        List<Map<String, Object>> data = jdbc.queryForList(
                "SELECT DATE(create_time) as date, COUNT(*) as count FROM m05_alert " +
                "WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) " +
                "GROUP BY DATE(create_time) ORDER BY date");
        return Result.success(data);
    }
}
