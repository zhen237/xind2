package com.commplatform.s4.controller;

import com.commplatform.s4.dto.GenerateRequest;
import com.commplatform.s4.service.BomService;
import com.commplatform.s4.service.MaterialCatalogService;
import com.commplatform.s4.service.S1S3DataService;
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
    private final S1S3DataService s1S3DataService;

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

    /**
     * 任务主线（P1）：代理 S1 任务列表，供 S4 前端选择真实任务（不再依赖场景码）。
     * <p>GET /api/s4/bom/s1-tasks → S1 真实任务数组</p>
     */
    @GetMapping("/s1-tasks")
    public ResponseEntity<?> s1Tasks() {
        return ResponseEntity.ok(s1S3DataService.fetchS1Tasks());
    }

    /**
     * 任务看板：聚合 S1 任务 + S3 审查 + S4 BOM 状态，按任务主线串联。
     * <p>供门户「进度看板 → 任务看板」展示真实链路状态。</p>
     */
    @GetMapping("/kanban")
    public ResponseEntity<?> kanban() {
        return ResponseEntity.ok(bomService.getKanban());
    }

    /**
     * [FR-10] 聚合查询 S1 设计成果 + S3 审查报告，供流水线概览卡片展示。
     * <p>
     * GET /api/s4/bom/design-review/{designTaskId}
     * 返回: { designTaskId, design: {...}, review: {...}, fallback: true|false }
     * 真实服务不可达时自动降级返回场景化演示数据，保证 UI 不为空。
     */
    @GetMapping("/design-review/{designTaskId}")
    public ResponseEntity<?> designReview(@PathVariable String designTaskId) {
        return ResponseEntity.ok(bomService.getDesignReview(designTaskId));
    }
}
