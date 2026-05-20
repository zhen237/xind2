package com.comm.m05.controller;

import com.comm.m05.entity.Alert;
import com.comm.m05.service.AlertService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/m05/alert")
public class AlertController {
    @Autowired
    private AlertService alertService;

    @GetMapping("/recent")
    public ResponseEntity<List<Alert>> getRecentAlerts(@RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(alertService.findRecent(limit));
    }

    @GetMapping("/status/{status}")
    public ResponseEntity<List<Alert>> getAlertsByStatus(@PathVariable Integer status) {
        return ResponseEntity.ok(alertService.findByStatus(status));
    }

    @GetMapping("/level/{level}")
    public ResponseEntity<List<Alert>> getAlertsByLevel(@PathVariable Integer level) {
        return ResponseEntity.ok(alertService.findByLevel(level));
    }

    @GetMapping("/statistics")
    public ResponseEntity<Map<String, Long>> getAlertStatistics() {
        return ResponseEntity.ok(alertService.getAlertStatistics());
    }

    @GetMapping("/count/unprocessed")
    public ResponseEntity<Long> getUnprocessedCount() {
        return ResponseEntity.ok(alertService.countUnprocessed());
    }

    @PutMapping("/{id}/confirm")
    public ResponseEntity<Void> confirmAlert(@PathVariable Long id) {
        alertService.confirmAlert(id);
        return ResponseEntity.ok().build();
    }

    @PutMapping("/{id}/resolve")
    public ResponseEntity<Void> resolveAlert(@PathVariable Long id, @RequestParam(required = false) String orderNo) {
        alertService.resolveAlert(id, orderNo);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Alert> getAlertById(@PathVariable Long id) {
        Alert alert = alertService.findById(id);
        if (alert == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(alert);
    }

    @PostMapping
    public ResponseEntity<Alert> createAlert(@RequestBody Alert alert) {
        return ResponseEntity.ok(alertService.create(alert));
    }
}
