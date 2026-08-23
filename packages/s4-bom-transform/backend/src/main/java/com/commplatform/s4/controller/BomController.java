package com.commplatform.s4.controller;

import com.commplatform.s4.service.BomService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * BOM 施工指令转化 REST API。
 * <p>
 * 端点前缀: /api/s4/bom
 * </p>
 */
@RestController
@RequestMapping("/api/s4/bom")
@RequiredArgsConstructor
public class BomController {

    private final BomService bomService;

    /**
     * [FR-7] 创建 BOM 生成任务（异步）。
     * <p>
     * POST body: { "designTaskId": "str", "projectId": "str" }
     * 立即返回 taskId（status=running），后台异步执行。
     */
    @PostMapping("/generate")
    public ResponseEntity<?> generate(@RequestBody Map<String, String> req) {
        try {
            String taskId = bomService.generate(req.get("designTaskId"), req.get("projectId"));
            return ResponseEntity.ok(Map.of("taskId", taskId, "status", "running"));
        } catch (IllegalArgumentException e) {
            // [FR-10] 审查闸门拦截 → 400 + 业务错误码
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "blocked",
                    "code", "S4_REVIEW_NOT_APPROVED",
                    "message", e.getMessage()
            ));
        }
    }

    /**
     * [FR-7] 查询 BOM 任务状态（供前端轮询）。
     * <p>
     * 返回: { taskId, status: "running"|"done"|"failed", ... }
     */
    @GetMapping("/{taskId}/status")
    public ResponseEntity<?> status(@PathVariable String taskId) {
        return ResponseEntity.ok(bomService.getStatus(taskId));
    }

    /**
     * [FR-9] 查询 BOM 详情（仅物料清单）。
     */
    @GetMapping("/{taskId}")
    public ResponseEntity<?> detail(@PathVariable String taskId) {
        return ResponseEntity.ok(bomService.getDetail(taskId));
    }

    /**
     * [FR-9] 全量查询 — BOM + 工序工艺 + 纤芯分配。
     */
    @GetMapping("/{taskId}/full")
    public ResponseEntity<?> full(@PathVariable String taskId) {
        return ResponseEntity.ok(bomService.getFull(taskId));
    }

    /**
     * [FR-9] 历史列表（分页）。
     */
    @GetMapping("/history")
    public ResponseEntity<?> history(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(bomService.listHistory(page, size));
    }

    /**
     * [FR-8] 导出 Excel（.xlsx）。
     */
    @GetMapping("/{taskId}/export")
    public ResponseEntity<?> export(@PathVariable String taskId) {
        String fileUrl = bomService.exportExcel(taskId);
        return ResponseEntity.ok(Map.of("fileUrl", fileUrl));
    }
}
