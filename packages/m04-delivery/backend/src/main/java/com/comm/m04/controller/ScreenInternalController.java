package com.comm.m04.controller;

import com.comm.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.*;

/**
 * M04 内部数据聚合 API（供 Screen 大屏调用）
 * 通过 Nginx 内网代理访问，不对外暴露
 */
@RestController
@RequestMapping("/api/m04/internal/screen")
public class ScreenInternalController {

    @Autowired
    private JdbcTemplate jdbc;

    /** 项目统计数据 */
    @GetMapping("/project-stats")
    @Cacheable(value = "longCache", key = "'m04:project-stats'")
    public Result<Map<String, Object>> projectStats() {
        Map<String, Object> stats = jdbc.queryForMap(
                "SELECT " +
                "  (SELECT COUNT(*) FROM m04_project WHERE status = 1) as projectTotal, " +
                "  (SELECT COUNT(*) FROM m04_project WHERE status = 2) as projectCompleted"
        );
        return Result.success(stats);
    }

    /** 项目按阶段分布 */
    @GetMapping("/project-by-phase")
    public Result<List<Map<String, Object>>> projectByPhase() {
        List<Map<String, Object>> byPhase = jdbc.queryForList(
                "SELECT current_phase, COUNT(*) as count FROM m04_project WHERE status = 1 GROUP BY current_phase");
        return Result.success(byPhase);
    }

    /** 项目列表 */
    @GetMapping("/project-list")
    public Result<List<Map<String, Object>>> projectList() {
        List<Map<String, Object>> projects = jdbc.queryForList(
                "SELECT id, project_name, project_code, current_phase, phase_progress, total_progress, " +
                "planned_end_date, construction_unit, status FROM m04_project ORDER BY create_time DESC");
        return Result.success(projects);
    }

    /** 延期项目 */
    @GetMapping("/delayed-projects")
    public Result<List<Map<String, Object>>> delayedProjects() {
        List<Map<String, Object>> projects = jdbc.queryForList(
                "SELECT id, project_name, project_code, current_phase, planned_end_date " +
                "FROM m04_project WHERE status = 1 AND planned_end_date < CURDATE()");
        return Result.success(projects);
    }

    /** 工单统计 */
    @GetMapping("/work-order-stats")
    @Cacheable(value = "longCache", key = "'m04:work-order-stats'")
    public Result<Map<String, Object>> workOrderStats() {
        Map<String, Object> stats = jdbc.queryForMap(
                "SELECT " +
                "  (SELECT COUNT(*) FROM m04_work_order WHERE status = 0) as workOrderPending, " +
                "  (SELECT COUNT(*) FROM m04_work_order WHERE status = 1) as workOrderProcessing, " +
                "  (SELECT COUNT(*) FROM m04_work_order WHERE status = 2) as workOrderDone"
        );
        return Result.success(stats);
    }
}
