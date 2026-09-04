package com.commplatform.s4.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.commplatform.s4.config.S4Config;
import com.commplatform.s4.entity.BomItem;
import com.commplatform.s4.entity.BomTask;
import com.commplatform.s4.mapper.BomItemMapper;
import com.commplatform.s4.mapper.BomTaskMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;

/**
 * BOM 异步执行器 — 独立 Service 避免 @Async 自调用 AOP 代理失效。
 *
 * <p>由 {@link BomService} 注入，通过 Spring 代理正确触发异步执行。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BomAsyncExecutor {

    private final BomTaskMapper bomTaskMapper;
    private final BomItemMapper bomItemMapper;
    private final S5NotifyService s5NotifyService;
    private final S3FeedbackService s3FeedbackService;
    private final S4Config s4Config;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Async("bomExecutor")
    public void executeGenerateAsync(String taskId, String designTaskId, String projectId, Object taskName) {
        BomTask task = findTask(taskId);
        if (task == null) return;

        int maxRetries = s4Config.getEngine().getRetry();
        String engineUrl = s4Config.getEngine().getUrl() + "/api/v1/bom/generate";
        Map<String, Object> engineResp = null;
        Exception lastException = null;

        // ── 重试循环 (AC-6) ──
        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                Map<String, Object> engineReq = new HashMap<>();
                engineReq.put("taskId", taskId);
                engineReq.put("designTaskId", designTaskId);
                engineReq.put("projectId", projectId);

                if (attempt > 0) {
                    log.info("BOM engine retry {}/{} for taskId={}", attempt, maxRetries, taskId);
                }

                @SuppressWarnings("unchecked")
                Map<String, Object> resp = restTemplate.postForObject(engineUrl, engineReq, Map.class);
                engineResp = resp;
                lastException = null;
                break; // 成功，退出重试循环

            } catch (org.springframework.web.client.ResourceAccessException e) {
                // 连接/读超时
                lastException = e;
                log.warn("BOM engine timeout (attempt {}): taskId={} msg={}", attempt, taskId, e.getMessage());
                if (attempt < maxRetries) {
                    try { Thread.sleep(2000L * (attempt + 1)); } catch (InterruptedException ignored) {}
                }
            } catch (Exception e) {
                lastException = e;
                log.error("BOM engine call failed (attempt {}): taskId={}", attempt, taskId, e);
                if (attempt < maxRetries) {
                    try { Thread.sleep(1500L * (attempt + 1)); } catch (InterruptedException ignored) {}
                }
            }
        }

        // ── 全部重试失败 → fallback (AC-6) ──
        if (engineResp == null) {
            log.error("BOM engine exhausted all {} retries: taskId={}", maxRetries, taskId);
            task.setStatus("failed");
            task.setErrorMessage(lastException != null ? lastException.getMessage() : "引擎不可达");
            task.setFinishedAt(LocalDateTime.now());
            bomTaskMapper.updateById(task);
            return;
        }

        // ── 引擎返回正常 ──
        try {
            if ("ok".equals(engineResp.get("status"))) {
                @SuppressWarnings("unchecked")
                Map<String, Object> bomBlock = (Map<String, Object>) engineResp.get("bom");
                if (bomBlock != null) {
                    @SuppressWarnings("unchecked")
                    List<Map<String, Object>> items = (List<Map<String, Object>>) bomBlock.get("items");
                    if (items != null) {
                        for (Map<String, Object> itemMap : items) {
                            BomItem item = objectMapper.convertValue(itemMap, BomItem.class);
                            item.setId(null);
                            item.setTaskId(taskId);
                            bomItemMapper.insert(item);
                        }
                    }

                    task.setMainDeviceQty(toInt(bomBlock.get("mainDeviceQty")));
                    task.setAuxiliaryQty(toInt(bomBlock.get("auxiliaryQty")));
                    task.setCableQty(toInt(bomBlock.get("cableQty")));
                    task.setTotalQty(toInt(bomBlock.get("totalItems")));

                    Set<String> codes = new HashSet<>();
                    List<BomItem> savedItems = bomItemMapper.selectByTaskId(taskId);
                    for (BomItem it : savedItems) {
                        codes.add(it.getMaterialCode());
                    }
                    task.setTotalCategories(codes.size());
                }

                Object procReq = engineResp.get("processRequirements");
                if (procReq != null) {
                    task.setProcessRequirements(toJson(procReq));
                }

                Object fiberAlloc = engineResp.get("fiberAllocation");
                if (fiberAlloc != null) {
                    task.setFiberAllocation(toJson(fiberAlloc));
                }

                task.setStatus("done");
                task.setFinishedAt(LocalDateTime.now());
                bomTaskMapper.updateById(task);

                log.info("BOM task done: taskId={} items={}", taskId, task.getTotalQty());

                // [I4] 推送 S5 施工监管（旁路通知，失败不阻断）
                Map<String, Object> stats = new LinkedHashMap<>();
                stats.put("totalItems", task.getTotalQty());
                stats.put("totalCategories", task.getTotalCategories());
                stats.put("mainDeviceQty", task.getMainDeviceQty());
                stats.put("auxiliaryQty", task.getAuxiliaryQty());
                stats.put("cableQty", task.getCableQty());
                s5NotifyService.notifyBomGenerated(
                        taskId, designTaskId, projectId,
                        taskName == null ? null : String.valueOf(taskName), stats);

                // [反馈回路] BOM→S3 回灌施工可行性结论（旁路，失败不阻断）
                String gateDecision = "allowed";
                Map<String, Object> violationCounts = Map.of();
                int rectCount = 0;
                Object reviewGate = engineResp.get("reviewGate");
                if (reviewGate instanceof Map<?, ?> rg) {
                    gateDecision = String.valueOf(rg.get("decision"));
                    if (rg.get("counts") instanceof Map<?, ?> c) {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> counts = (Map<String, Object>) c;
                        violationCounts = counts;
                    }
                    if (rg.get("rectificationSteps") instanceof List<?> l) {
                        rectCount = l.size();
                    }
                }
                s3FeedbackService.feedbackConstructability(
                        taskId, designTaskId, gateDecision, violationCounts, rectCount, stats);

            } else {
                task.setStatus("failed");
                task.setErrorMessage("引擎返回非 ok: " + engineResp.get("status"));
                task.setFinishedAt(LocalDateTime.now());
                bomTaskMapper.updateById(task);
                log.warn("Python engine returned non-ok for taskId={} status={}", taskId, engineResp.get("status"));
            }
        } catch (Exception e) {
            log.error("BOM result processing failed: taskId={}", taskId, e);
            task.setStatus("failed");
            task.setErrorMessage("结果解析失败: " + e.getMessage());
            task.setFinishedAt(LocalDateTime.now());
            bomTaskMapper.updateById(task);
        }
    }

    private BomTask findTask(String taskId) {
        List<BomTask> list = bomTaskMapper.selectList(
                new LambdaQueryWrapper<BomTask>().eq(BomTask::getTaskId, taskId)
        );
        return list.isEmpty() ? null : list.get(0);
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
}
