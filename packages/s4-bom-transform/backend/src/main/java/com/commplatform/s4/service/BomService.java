package com.commplatform.s4.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.commplatform.s4.config.S4Config;
import com.commplatform.s4.entity.BomItem;
import com.commplatform.s4.entity.BomTask;
import com.commplatform.s4.exception.S4BusinessException;
import com.commplatform.s4.exception.S4ErrorCode;
import com.commplatform.s4.mapper.BomItemMapper;
import com.commplatform.s4.mapper.BomTaskMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;
import java.util.regex.Pattern;

/**
 * BOM 核心服务 — 异步生成 + 状态轮询。
 *
 * <p>流程:
 * <ol>
 *   <li>POST /api/s4/bom/generate → 立即返回 taskId（status=running）</li>
 *   <li>后台异步调用 Python 引擎 → 落库 → status=done</li>
 *   <li>前端轮询 GET /api/s4/bom/{taskId}/status</li>
 *   <li>done 后请求 GET /api/s4/bom/{taskId}/full</li>
 * </ol>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BomService {

    /** 安全 taskId 格式（与 Python 引擎一致）：字母数字、下划线、连字符，1~64 位 */
    private static final Pattern TASK_ID_PATTERN = Pattern.compile("^[A-Za-z0-9_-]{1,64}$");

    private static final MediaType XLSX_MEDIA_TYPE =
            MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

    private final BomTaskMapper bomTaskMapper;
    private final BomItemMapper bomItemMapper;
    private final BomAsyncExecutor bomAsyncExecutor;
    private final S1S3DataService s1S3DataService;
    private final S4Config s4Config;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    // ────────────────────────────────────────
    //  generate — 同步入口（立即返回 taskId）
    // ────────────────────────────────────────

    /**
     * [FR-7] 创建 BOM 任务 → 启动异步生成 → 立即返回 taskId。
     *
     * @throws S4BusinessException INVALID_PARAM — designTaskId 为空或格式非法
     * @throws S4BusinessException REVIEW_BLOCKED — 分级审查闸门判定 BLOCKED（critical/error 违规）
     */
    public String generate(String designTaskId, String projectId) {
        // 入参校验（Java 侧第一道门，与引擎侧白名单一致）
        if (designTaskId == null || designTaskId.isBlank()) {
            throw new S4BusinessException(S4ErrorCode.INVALID_PARAM, "designTaskId 不能为空");
        }
        if (!TASK_ID_PATTERN.matcher(designTaskId).matches()) {
            throw new S4BusinessException(S4ErrorCode.INVALID_PARAM,
                    "designTaskId 格式非法（仅允许字母数字、下划线、连字符，1~64 位）");
        }

        // [FR-10] 四档分级审查闸门：critical/error → 拦截；warning/pending → 放行携带整改标记
        Map<String, Object> gate = s1S3DataService.checkGate(designTaskId);
        String decision = String.valueOf(gate.get("decision"));
        if ("blocked".equals(decision)) {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> blockers = (List<Map<String, Object>>) gate.get("blockers");
            String summary = blockers == null ? "" : blockers.stream()
                    .map(b -> "[" + b.getOrDefault("riskLevel", b.get("severity")) + "] " + b.get("ruleId") + " " + b.get("ruleName"))
                    .reduce((a, b) -> a + "; " + b).orElse("");
            log.warn("[FR-10] BOM 生成被分级审查闸门拦截: designTaskId={} counts={} blockers={}",
                    designTaskId, gate.get("counts"), summary);
            throw new S4BusinessException(S4ErrorCode.REVIEW_BLOCKED,
                    "设计存在致命/严重审查违规，已拦截 BOM 生成（" + summary + "），请先完成整改并重新提交 S3 审查");
        }
        if ("allowed_with_warnings".equals(decision)) {
            log.info("[FR-10] BOM 放行（携带警告）: designTaskId={} counts={}", designTaskId, gate.get("counts"));
        }

        String taskId = UUID.randomUUID().toString();

        BomTask task = new BomTask();
        task.setTaskId(taskId);
        task.setDesignTaskId(designTaskId);
        task.setProjectId(projectId);
        task.setStatus("running");
        task.setCreatedAt(LocalDateTime.now());
        bomTaskMapper.insert(task);

        log.info("BOM task created: taskId={} designTaskId={}", taskId, designTaskId);

        // 通过独立 Executor 避免 @Async AOP 自调用失效
        bomAsyncExecutor.executeGenerateAsync(taskId, designTaskId, projectId);

        return taskId;
    }

    // ────────────────────────────────────────
    //  查询接口
    // ────────────────────────────────────────

    /**
     * [FR-9] 查询 BOM 任务状态（供前端轮询）。
     */
    public Map<String, Object> getStatus(String taskId) {
        validateTaskId(taskId);
        BomTask task = findTask(taskId);
        if (task == null) {
            return Map.of("taskId", taskId, "status", "not_found");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("taskId", task.getTaskId());
        result.put("status", task.getStatus());
        result.put("createdAt", task.getCreatedAt());
        if ("done".equals(task.getStatus())) {
            result.put("totalItems", task.getTotalQty());
            result.put("totalCategories", task.getTotalCategories());
            result.put("finishedAt", task.getFinishedAt());
        }
        if ("failed".equals(task.getStatus())) {
            result.put("error", "BOM 生成失败，请重试");
        }
        return result;
    }

    /**
     * [FR-9] 查 BOM 详情（仅物料清单，前提 status=done）。
     */
    public Map<String, Object> getDetail(String taskId) {
        validateTaskId(taskId);
        BomTask task = findTask(taskId);
        if (task == null) {
            throw new S4BusinessException(S4ErrorCode.TASK_NOT_FOUND, "BOM 任务不存在: " + taskId);
        }
        return buildDetailMap(task);
    }

    /**
     * [FR-9] 全量查询 — 物料 + 工序工艺 + 纤芯分配。
     */
    public Map<String, Object> getFull(String taskId) {
        validateTaskId(taskId);
        BomTask task = findTask(taskId);
        if (task == null) {
            throw new S4BusinessException(S4ErrorCode.TASK_NOT_FOUND, "BOM 任务不存在: " + taskId);
        }
        Map<String, Object> result = buildDetailMap(task);

        if (task.getProcessRequirements() != null) {
            result.put("processRequirements", fromJson(task.getProcessRequirements()));
        }
        if (task.getFiberAllocation() != null) {
            result.put("fiberAllocation", fromJson(task.getFiberAllocation()));
        }
        return result;
    }

    /**
     * [FR-9] 历史列表（分页）。
     */
    public Map<String, Object> listHistory(int pageNum, int size) {
        if (pageNum < 1 || size < 1 || size > 100) {
            throw new S4BusinessException(S4ErrorCode.INVALID_PARAM,
                    "分页参数非法（page ≥ 1，1 ≤ size ≤ 100）");
        }
        Page<BomTask> mpPage = new Page<>(pageNum, size);
        var result = bomTaskMapper.selectHistoryPage(mpPage, null);
        return Map.of(
                "records", result.getRecords(),
                "total", result.getTotal(),
                "page", pageNum,
                "size", size
        );
    }

    // ────────────────────────────────────────
    //  导出
    // ────────────────────────────────────────

    /**
     * [FR-8] 导出 Excel — Java 后端作为字节流中转站：
     * 校验任务存在且完成 → 从 Python 引擎拉取 .xlsx 字节 →
     * 以 attachment 响应返回（引擎不再直接暴露给前端）。
     *
     * @throws S4BusinessException TASK_NOT_FOUND / EXPORT_NOT_READY / ENGINE_TIMEOUT / ENGINE_ERROR
     */
    public ResponseEntity<byte[]> exportExcel(String taskId) {
        validateTaskId(taskId);
        BomTask task = findTask(taskId);
        if (task == null) {
            throw new S4BusinessException(S4ErrorCode.TASK_NOT_FOUND, "BOM 任务不存在: " + taskId);
        }
        if (!"done".equals(task.getStatus())) {
            throw new S4BusinessException(S4ErrorCode.EXPORT_NOT_READY,
                    "Excel 尚未就绪，当前任务状态: " + task.getStatus());
        }

        String url = s4Config.getEngine().getUrl() + "/api/v1/bom/export?taskId=" + taskId;
        byte[] bytes;
        try {
            bytes = restTemplate.getForObject(url, byte[].class);
        } catch (ResourceAccessException e) {
            throw new S4BusinessException(S4ErrorCode.ENGINE_TIMEOUT,
                    "引擎导出超时或不可达: " + e.getMessage(), e);
        } catch (Exception e) {
            throw new S4BusinessException(S4ErrorCode.ENGINE_ERROR,
                    "引擎导出失败: " + e.getMessage(), e);
        }
        if (bytes == null || bytes.length == 0) {
            throw new S4BusinessException(S4ErrorCode.EXPORT_NOT_READY,
                    "导出文件为空或不存在: " + taskId);
        }

        // taskId 已通过白名单校验，文件名安全（防文件名注入）
        String filename = "BOM_" + taskId + ".xlsx";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(XLSX_MEDIA_TYPE);
        headers.setContentDisposition(ContentDisposition.attachment()
                .filename(filename, StandardCharsets.UTF_8)
                .build());
        headers.setContentLength(bytes.length);

        log.info("BOM Excel exported: taskId={} size={}B", taskId, bytes.length);
        return new ResponseEntity<>(bytes, headers, HttpStatus.OK);
    }

    // ────────────────────────────────────────
    //  内部工具方法
    // ────────────────────────────────────────

    /** taskId 白名单校验 — 防路径穿越/注入，与 Python 引擎侧规则保持一致。 */
    private void validateTaskId(String taskId) {
        if (taskId == null || !TASK_ID_PATTERN.matcher(taskId).matches()) {
            throw new S4BusinessException(S4ErrorCode.INVALID_PARAM,
                    "taskId 格式非法（仅允许字母数字、下划线、连字符，1~64 位）");
        }
    }

    private BomTask findTask(String taskId) {
        List<BomTask> list = bomTaskMapper.selectList(
                new LambdaQueryWrapper<BomTask>().eq(BomTask::getTaskId, taskId)
        );
        return list.isEmpty() ? null : list.get(0);
    }

    private Map<String, Object> buildDetailMap(BomTask task) {
        List<BomItem> items = bomItemMapper.selectByTaskId(task.getTaskId());
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("taskId", task.getTaskId());
        result.put("designTaskId", task.getDesignTaskId());
        result.put("projectId", task.getProjectId());
        result.put("status", task.getStatus());
        result.put("totalCategories", task.getTotalCategories());
        result.put("totalQty", task.getTotalQty());
        result.put("mainDeviceQty", task.getMainDeviceQty());
        result.put("auxiliaryQty", task.getAuxiliaryQty());
        result.put("cableQty", task.getCableQty());
        result.put("items", items);
        result.put("createdAt", task.getCreatedAt());
        result.put("finishedAt", task.getFinishedAt());
        return result;
    }

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("JSON serialize failed", e);
            return "[]";
        }
    }

    @SuppressWarnings("unchecked")
    private Object fromJson(String json) {
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (JsonProcessingException e) {
            log.error("JSON deserialize failed", e);
            return Collections.emptyList();
        }
    }
}
