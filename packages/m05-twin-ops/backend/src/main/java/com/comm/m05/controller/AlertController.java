package com.comm.m05.controller;

import com.comm.common.Result;
import com.comm.m05.entity.Alert;
import com.comm.m05.service.AlertService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/m05/alert")
public class AlertController {
    @Autowired
    private AlertService alertService;

    @GetMapping("/recent")
    public Result<List<Alert>> getRecentAlerts(@RequestParam(defaultValue = "20") int limit) {
        return Result.success(alertService.findRecent(limit));
    }

    @GetMapping("/status/{status}")
    public Result<List<Alert>> getAlertsByStatus(@PathVariable Integer status) {
        return Result.success(alertService.findByStatus(status));
    }

    @GetMapping("/level/{level}")
    public Result<List<Alert>> getAlertsByLevel(@PathVariable Integer level) {
        return Result.success(alertService.findByLevel(level));
    }

    @GetMapping("/statistics")
    public Result<Map<String, Long>> getAlertStatistics() {
        return Result.success(alertService.getAlertStatistics());
    }

    @GetMapping("/count/unprocessed")
    public Result<Long> getUnprocessedCount() {
        return Result.success(alertService.countUnprocessed());
    }

    @PutMapping("/{id}/confirm")
    public Result<Boolean> confirmAlert(@PathVariable Long id) {
        alertService.confirmAlert(id);
        return Result.success(true);
    }

    @PutMapping("/{id}/resolve")
    public Result<Boolean> resolveAlert(@PathVariable Long id, @RequestParam(required = false) String orderNo) {
        alertService.resolveAlert(id, orderNo);
        return Result.success(true);
    }

    @GetMapping("/{id}")
    public Result<Alert> getAlertById(@PathVariable Long id) {
        Alert alert = alertService.findById(id);
        if (alert == null) {
            return Result.notFound("告警不存在");
        }
        return Result.success(alert);
    }

    @PostMapping
    public Result<Alert> createAlert(@RequestBody Alert alert) {
        return Result.success(alertService.create(alert));
    }
}
