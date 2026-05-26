package com.comm.screen.controller;

import com.comm.screen.common.Result;
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

        // 设备统计
        int totalDevices = queryInt("SELECT COUNT(*) FROM m05_device");
        int onlineDevices = queryInt("SELECT COUNT(*) FROM m05_device WHERE status = 1");
        int offlineDevices = queryInt("SELECT COUNT(*) FROM m05_device WHERE status = 0");
        int faultDevices = queryInt("SELECT COUNT(*) FROM m05_device WHERE status = 2");
        data.put("deviceTotal", totalDevices);
        data.put("deviceOnline", onlineDevices);
        data.put("deviceOffline", offlineDevices);
        data.put("deviceFault", faultDevices);
        data.put("deviceOnlineRate", totalDevices > 0 ? Math.round(onlineDevices * 10000.0 / totalDevices) / 100.0 : 0);

        // 告警统计
        int alertTotal = queryInt("SELECT COUNT(*) FROM m05_alert");
        int alertUnprocessed = queryInt("SELECT COUNT(*) FROM m05_alert WHERE status = 0");
        int alertConfirmed = queryInt("SELECT COUNT(*) FROM m05_alert WHERE status = 1");
        int alertResolved = queryInt("SELECT COUNT(*) FROM m05_alert WHERE status = 2");
        data.put("alertTotal", alertTotal);
        data.put("alertUnprocessed", alertUnprocessed);
        data.put("alertConfirmed", alertConfirmed);
        data.put("alertResolved", alertResolved);

        // 工单统计
        int workOrderPending = queryInt("SELECT COUNT(*) FROM m04_work_order WHERE status = 0");
        int workOrderProcessing = queryInt("SELECT COUNT(*) FROM m04_work_order WHERE status = 1");
        int workOrderDone = queryInt("SELECT COUNT(*) FROM m04_work_order WHERE status = 2");
        data.put("workOrderPending", workOrderPending);
        data.put("workOrderProcessing", workOrderProcessing);
        data.put("workOrderDone", workOrderDone);

        // 项目统计
        int projectTotal = queryInt("SELECT COUNT(*) FROM m04_project WHERE status = 1");
        int projectCompleted = queryInt("SELECT COUNT(*) FROM m04_project WHERE status = 2");
        data.put("projectTotal", projectTotal);
        data.put("projectCompleted", projectCompleted);
        data.put("projectCompletionRate", projectTotal > 0 ? Math.round(projectCompleted * 10000.0 / projectTotal) / 100.0 : 0);

        return Result.success(data);
    }

    /** 告警监控大屏数据 */
    @GetMapping("/alert-monitor")
    public Result<Map<String, Object>> alertMonitor() {
        Map<String, Object> data = new LinkedHashMap<>();

        // 告警按级别统计
        List<Map<String, Object>> alertByLevel = jdbc.queryForList(
                "SELECT level, COUNT(*) as count FROM m05_alert GROUP BY level ORDER BY level");
        data.put("alertByLevel", alertByLevel);

        // 最近告警列表
        List<Map<String, Object>> recentAlerts = jdbc.queryForList(
                "SELECT id, device_code, alert_content, level, status, source, create_time " +
                "FROM m05_alert ORDER BY create_time DESC LIMIT 20");
        data.put("recentAlerts", recentAlerts);

        // 告警TOP10设备
        List<Map<String, Object>> topAlertDevices = jdbc.queryForList(
                "SELECT device_code, COUNT(*) as count FROM m05_alert GROUP BY device_code ORDER BY count DESC LIMIT 10");
        data.put("topAlertDevices", topAlertDevices);

        // 近7天告警趋势
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

        // 各阶段项目数量
        List<Map<String, Object>> byPhase = jdbc.queryForList(
                "SELECT current_phase, COUNT(*) as count FROM m04_project WHERE status = 1 GROUP BY current_phase");
        data.put("projectsByPhase", byPhase);

        // 项目列表
        List<Map<String, Object>> projects = jdbc.queryForList(
                "SELECT id, project_name, project_code, current_phase, phase_progress, total_progress, " +
                "planned_end_date, construction_unit, status FROM m04_project ORDER BY create_time DESC");
        data.put("projects", projects);

        // 延期项目
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

        // 设备类型分布
        List<Map<String, Object>> deviceTypeDistribution = jdbc.queryForList(
                "SELECT device_type, COUNT(*) as count FROM m05_device GROUP BY device_type");
        data.put("deviceTypeDistribution", deviceTypeDistribution);

        // 站点设备数量
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

    private int queryInt(String sql) {
        Integer result = jdbc.queryForObject(sql, Integer.class);
        return result != null ? result : 0;
    }
}
