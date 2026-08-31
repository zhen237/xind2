package com.commplatform.s4.controller;

import com.commplatform.s4.dto.GenerateRequest;
import com.commplatform.s4.service.BomService;
import com.commplatform.s4.service.MaterialCatalogService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * BOM 施工指令转化 REST API。
 * <p>
 * 端点前缀: /api/s4/bom
 * 异常统一由 GlobalExceptionHandler 转换为 {code, message, timestamp}。
 * </p>
 */
@RestController
@RequestMapping("/api/s4/bom")
@RequiredArgsConstructor
public class BomController {

    private final BomService bomService;
    private final MaterialCatalogService materialCatalogService;

    /**
     * [FR-7] 创建 BOM 生成任务（异步）。
     * <p>
     * POST body: { "designTaskId": "str", "projectId": "str" }
     * 立即返回 taskId（status=running），后台异步执行。
     * designTaskId 必填（@Valid 校验，缺失 → 400 S4_INVALID_PARAM）。
     */
    @PostMapping("/generate")
    public ResponseEntity<Map<String, String>> generate(@Valid @RequestBody GenerateRequest req) {
        String taskId = bomService.generate(req.getDesignTaskId(), req.getProjectId());
        return ResponseEntity.ok(Map.of("taskId", taskId, "status", "running"));
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
     * [FR-8] 导出 Excel（.xlsx）— Java 后端字节流中转。
     * <p>
     * 成功: 200 + application/vnd...spreadsheetml.sheet + Content-Disposition: attachment。
     * 失败: 404/409/502/504 + {code, message, timestamp}（GlobalExceptionHandler）。
     * </p>
     */
    @GetMapping("/{taskId}/export")
    public ResponseEntity<byte[]> export(@PathVariable String taskId) {
        return bomService.exportExcel(taskId);
    }

    /**
     * [FR-2] 物料编码库查询 — 支持按设备类型过滤。
     * <p>GET /api/s4/bom/catalog?deviceType=antenna</p>
     */
    @GetMapping("/catalog")
    public ResponseEntity<?> catalog(
            @RequestParam(required = false) String deviceType) {
        return ResponseEntity.ok(materialCatalogService.getCatalog(deviceType));
    }
}
