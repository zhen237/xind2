package com.commplatform.s4.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.commplatform.s4.config.S4Config;
import com.commplatform.s4.entity.BomItem;
import com.commplatform.s4.entity.BomTask;
import com.commplatform.s4.mapper.BomItemMapper;
import com.commplatform.s4.mapper.BomTaskMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;

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
     * @throws IllegalArgumentException 审查未通过或被拦截时抛出（由 Controller 转 4xx）
     */
    public String generate(String designTaskId, String projectId) {
        // [FR-10] 审查闸门：设计必须已通过 S3 审查才能进入 BOM 生成
        if (!s1S3DataService.isApproved(designTaskId)) {
            log.warn("[FR-10] BOM 生成被审查闸门拦截: designTaskId={}", designTaskId);
            throw new IllegalArgumentException("设计未通过审查，不能生成施工指令 BOM: " + designTaskId);
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
        BomTask task = findTask(taskId);
        if (task == null) {
            return Map.of("error", "task not found");
        }
        return buildDetailMap(task);
    }

    /**
     * [FR-9] 全量查询 — 物料 + 工序工艺 + 纤芯分配。
     */
    public Map<String, Object> getFull(String taskId) {
        BomTask task = findTask(taskId);
        if (task == null) {
            return Map.of("error", "task not found");
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
     * [FR-8] 导出 Excel — 返回 Python 引擎的文件下载链接。
     */
    public String exportExcel(String taskId) {
        return s4Config.getEngine().getUrl() + "/api/v1/bom/export?taskId=" + taskId;
    }

    // ────────────────────────────────────────
    //  内部工具方法
    // ────────────────────────────────────────

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

    private int toInt(Object val) {
        if (val instanceof Number n) return n.intValue();
        if (val instanceof String s) {
            try { return Integer.parseInt(s); } catch (NumberFormatException ignored) {}
        }
        return 0;
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
