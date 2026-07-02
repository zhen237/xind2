package com.comm.screen.controller;

import com.comm.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 大屏中心数据聚合API
 * 只读查询各模块数据表，不做写入操作
 */
@RestController
@RequestMapping("/api/screen")
public class ScreenController {

    @Autowired
    private JdbcTemplate jdbc;

    /** 运维总览大屏数据 */
    @GetMapping("/ops-overview")
    public Result<Map<String, Object>> opsOverview() {
        Map<String, Object> data = new LinkedHashMap<>();

        // 合并所有统计查询为单个SQL，减少数据库往返次数
        Map<String, Object> stats = jdbc.queryForMap(
                "SELECT " +
                "  (SELECT COUNT(*) FROM m05_device) as deviceTotal, " +
                "  (SELECT COUNT(*) FROM m05_device WHERE status = 1) as deviceOnline, " +
                "  (SELECT COUNT(*) FROM m05_device WHERE status = 0) as deviceOffline, " +
                "  (SELECT COUNT(*) FROM m05_device WHERE status = 2) as deviceFault, " +
                "  (SELECT COUNT(*) FROM m05_alert) as alertTotal, " +
                "  (SELECT COUNT(*) FROM m05_alert WHERE status = 0) as alertUnprocessed, " +
                "  (SELECT COUNT(*) FROM m05_alert WHERE status = 1) as alertConfirmed, " +
                "  (SELECT COUNT(*) FROM m05_alert WHERE status = 2) as alertResolved, " +
                "  (SELECT COUNT(*) FROM m04_work_order WHERE status = 0) as workOrderPending, " +
                "  (SELECT COUNT(*) FROM m04_work_order WHERE status = 1) as workOrderProcessing, " +
                "  (SELECT COUNT(*) FROM m04_work_order WHERE status = 2) as workOrderDone, " +
                "  (SELECT COUNT(*) FROM m04_project WHERE status = 1) as projectTotal, " +
                "  (SELECT COUNT(*) FROM m04_project WHERE status = 2) as projectCompleted"
        );

        int deviceTotal = getInt(stats, "deviceTotal");
        int onlineDevices = getInt(stats, "deviceOnline");
        int offlineDevices = getInt(stats, "deviceOffline");
        int faultDevices = getInt(stats, "deviceFault");
        data.put("deviceTotal", deviceTotal);
        data.put("deviceOnline", onlineDevices);
        data.put("deviceOffline", offlineDevices);
        data.put("deviceFault", faultDevices);
        data.put("deviceOnlineRate", deviceTotal > 0 ? Math.round(onlineDevices * 10000.0 / deviceTotal) / 100.0 : 0);

        data.put("alertTotal", getInt(stats, "alertTotal"));
        data.put("alertUnprocessed", getInt(stats, "alertUnprocessed"));
        data.put("alertConfirmed", getInt(stats, "alertConfirmed"));
        data.put("alertResolved", getInt(stats, "alertResolved"));

        data.put("workOrderPending", getInt(stats, "workOrderPending"));
        data.put("workOrderProcessing", getInt(stats, "workOrderProcessing"));
        data.put("workOrderDone", getInt(stats, "workOrderDone"));

        int projectTotal = getInt(stats, "projectTotal");
        int projectCompleted = getInt(stats, "projectCompleted");
        data.put("projectTotal", projectTotal);
        data.put("projectCompleted", projectCompleted);
        data.put("projectCompletionRate", projectTotal > 0 ? Math.round(projectCompleted * 10000.0 / projectTotal) / 100.0 : 0);

        return Result.success(data);
    }

    /** 告警监控大屏数据 */
    @GetMapping("/alert-monitor")
    public Result<Map<String, Object>> alertMonitor() {
        Map<String, Object> data = new LinkedHashMap<>();

        List<Map<String, Object>> alertByLevel = jdbc.queryForList(
                "SELECT level, COUNT(*) as count FROM m05_alert GROUP BY level ORDER BY level");
        data.put("alertByLevel", alertByLevel);

        List<Map<String, Object>> recentAlerts = jdbc.queryForList(
                "SELECT id, device_code, alert_content, level, status, source, create_time " +
                "FROM m05_alert ORDER BY create_time DESC LIMIT 20");
        data.put("recentAlerts", recentAlerts);

        List<Map<String, Object>> topAlertDevices = jdbc.queryForList(
                "SELECT device_code, COUNT(*) as count FROM m05_alert GROUP BY device_code ORDER BY count DESC LIMIT 10");
        data.put("topAlertDevices", topAlertDevices);

        List<Map<String, Object>> alertTrend = jdbc.queryForList(
                "SELECT DATE(create_time) as date, COUNT(*) as count FROM m05_alert " +
                "WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) " +
                "GROUP BY DATE(create_time) ORDER BY date");
        data.put("alertTrend", alertTrend);

        return Result.success(data);
    }

    /** 项目进度大屏数据 */
    @GetMapping("/project-progress")
    public Result<Map<String, Object>> projectProgress() {
        Map<String, Object> data = new LinkedHashMap<>();

        List<Map<String, Object>> byPhase = jdbc.queryForList(
                "SELECT current_phase, COUNT(*) as count FROM m04_project WHERE status = 1 GROUP BY current_phase");
        data.put("projectsByPhase", byPhase);

        List<Map<String, Object>> projects = jdbc.queryForList(
                "SELECT id, project_name, project_code, current_phase, phase_progress, total_progress, " +
                "planned_end_date, construction_unit, status FROM m04_project ORDER BY create_time DESC");
        data.put("projects", projects);

        List<Map<String, Object>> delayedProjects = jdbc.queryForList(
                "SELECT id, project_name, project_code, current_phase, planned_end_date " +
                "FROM m04_project WHERE status = 1 AND planned_end_date < CURDATE()");
        data.put("delayedProjects", delayedProjects);

        return Result.success(data);
    }

    /** 能耗分析大屏数据 */
    @GetMapping("/energy-analysis")
    public Result<Map<String, Object>> energyAnalysis() {
        Map<String, Object> data = new LinkedHashMap<>();

        List<Map<String, Object>> deviceTypeDistribution = jdbc.queryForList(
                "SELECT device_type, COUNT(*) as count FROM m05_device GROUP BY device_type");
        data.put("deviceTypeDistribution", deviceTypeDistribution);

        List<Map<String, Object>> stationDeviceCount = jdbc.queryForList(
                "SELECT d.station_code, s.station_name, COUNT(*) as count " +
                "FROM m05_device d LEFT JOIN shared_station s ON d.station_code = s.station_code " +
                "GROUP BY d.station_code, s.station_name");
        data.put("stationDeviceCount", stationDeviceCount);

        return Result.success(data);
    }

    /** 站点GIS数据（用于热力图） */
    @GetMapping("/station-gis")
    public Result<List<Map<String, Object>>> stationGis() {
        List<Map<String, Object>> stations = jdbc.queryForList(
                "SELECT station_code, station_name, longitude, latitude, status FROM shared_station");
        return Result.success(stations);
    }

    private int getInt(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        return 0;
    }
}
