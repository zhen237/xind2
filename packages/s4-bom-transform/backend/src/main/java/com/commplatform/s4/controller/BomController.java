package com.commplatform.s4.controller;

import com.commplatform.s4.dto.GenerateRequest;
import com.commplatform.s4.entity.BomItem;
import com.commplatform.s4.entity.BomTask;
import com.commplatform.s4.exception.S4BusinessException;
import com.commplatform.s4.exception.S4ErrorCode;
import com.commplatform.s4.mapper.BomItemMapper;
import com.commplatform.s4.service.BomService;
import com.commplatform.s4.service.CostEstimationService;
import com.commplatform.s4.service.MaterialCatalogService;
import com.commplatform.s4.service.S1S3DataService;
import com.commplatform.s4.service.VolumeReportExporter;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

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
    private final VolumeReportExporter volumeReportExporter;
    private final CostEstimationService costEstimationService;
    private final BomItemMapper bomItemMapper;

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

    /**
     * [S4-S1-迁移 2026-09-22] 工程量报表 JSON 数据接口。
     * <p>聚合 S1→S4 设计数据（含 devices + pipelines），调用 CostEstimationService 算造价。</p>
     * <p>GET /api/s4/bom/{designTaskId}/volume-report 返回：</p>
     * <ul>
     *   <li>design — 设备清单 + 管线明细（含已落库 pipelines）</li>
     *   <li>cost — 造价估算明细 + 汇总（标注"概算/示意"）</li>
     *   <li>bomItems — 已有 BOM 任务时附带物料清单（无任务时空字段）</li>
     * </ul>
     */
    @GetMapping("/{designTaskId}/volume-report")
    public ResponseEntity<?> volumeReport(@PathVariable String designTaskId,
                                          @RequestParam(required = false) Double fiberPricePerMeter) {
        Map<String, Object> designReview = bomService.getDesignReview(designTaskId);
        @SuppressWarnings("unchecked")
        Map<String, Object> design = (Map<String, Object>) designReview.getOrDefault("design", Collections.emptyMap());

        // 拉取最近一次 done 任务的物料清单（如有）
        List<Map<String, Object>> bomItems = loadBomItemsForLatestTask(designTaskId);

        // 造价（可整体覆盖光缆基准单价 — 对应 QGIS「每米价格」SpinBox，默认不覆盖）
        Map<String, Object> cost = costEstimationService.estimate(
                extractPipelines(design), fiberPricePerMeter);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("designTaskId", designTaskId);
        result.put("realId",       designReview.get("realId"));
        result.put("design",       design);
        result.put("bomItems",     bomItems);
        result.put("cost",         cost);
        result.put("fallback",     designReview.get("fallback"));
        return ResponseEntity.ok(result);
    }

    /**
     * [S4-S1-迁移 2026-09-22] 工程量报表 Excel 导出 — 4 sheet 工作簿：
     * BOM物料 / 设备清单 / 管线明细 / 造价估算汇总（标注"概算/示意"）。
     * <p>GET /api/s4/bom/{designTaskId}/volume-report/export → application/vnd.openxmlformats-officedocument.spreadsheetml.sheet</p>
     * <p>可选查询参数 fiberPricePerMeter：整体覆盖光缆基准单价（元/m），对应 QGIS「每米价格」SpinBox（默认 15）。</p>
     */
    @GetMapping("/{designTaskId}/volume-report/export")
    public ResponseEntity<byte[]> exportVolumeReport(@PathVariable String designTaskId,
                                                    @RequestParam(required = false) Double fiberPricePerMeter) {
        Map<String, Object> designReview = bomService.getDesignReview(designTaskId);
        @SuppressWarnings("unchecked")
        Map<String, Object> design = (Map<String, Object>) designReview.getOrDefault("design", Collections.emptyMap());
        List<Map<String, Object>> bomItems = loadBomItemsForLatestTask(designTaskId);
        return volumeReportExporter.export(designTaskId, bomItems, design, fiberPricePerMeter);
    }

    /**
     * [S4-S1-迁移 2026-09-27] 工程量报表 TXT 导出 — 对应 QGIS 插件 _export_report_txt 产物形态。
     * <p>GET /api/s4/bom/{designTaskId}/volume-report/export-txt → text/plain; charset=UTF-8</p>
     * <p>可选查询参数 fiberPricePerMeter：整体覆盖光缆基准单价（元/m）。</p>
     */
    @GetMapping("/{designTaskId}/volume-report/export-txt")
    public ResponseEntity<byte[]> exportVolumeReportTxt(@PathVariable String designTaskId,
                                                       @RequestParam(required = false) Double fiberPricePerMeter) {
        Map<String, Object> designReview = bomService.getDesignReview(designTaskId);
        @SuppressWarnings("unchecked")
        Map<String, Object> design = (Map<String, Object>) designReview.getOrDefault("design", Collections.emptyMap());
        List<Map<String, Object>> bomItems = loadBomItemsForLatestTask(designTaskId);
        return volumeReportExporter.exportTxt(designTaskId, bomItems, design, fiberPricePerMeter);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> extractPipelines(Map<String, Object> design) {
        Object v = design == null ? null : design.get("pipelines");
        return v instanceof List ? (List<Map<String, Object>>) v : Collections.emptyList();
    }

    private List<Map<String, Object>> loadBomItemsForLatestTask(String designTaskId) {
        try {
            BomTask task = bomService.findLatestDoneTaskForDesign(designTaskId);
            if (task == null) return Collections.emptyList();
            List<BomItem> items = bomItemMapper.selectByTaskId(task.getTaskId());
            return items.stream().map(this::toBomItemMap).collect(Collectors.toList());
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    private Map<String, Object> toBomItemMap(BomItem it) {
        Map<String, Object> m = new LinkedHashMap<>();
        // siteId → 用 deviceName 作为所属站点/设备的标识（BomItem 表里没 siteId 字段）
        m.put("siteId",        it.getDeviceName());
        // installMethod → category 反映 main_device/auxiliary/cable 三类
        m.put("installMethod", it.getCategory());
        m.put("materialName",  it.getMaterialName());
        m.put("spec",          it.getSpec());
        m.put("qty",           it.getQty());
        m.put("unit",          it.getUnit());
        return m;
    }
}
