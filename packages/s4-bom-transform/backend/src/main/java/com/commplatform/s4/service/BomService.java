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

    /**
     * [FR-10] 聚合查询 S1 设计成果 + S3 审查报告，供 S4 前端流水线概览卡片展示。
     *
     * <p>实现策略：
     * <ul>
     *   <li>前端场景码 D001/D002/D003 映射为真实数字 ID（S1 设计任务 ID 与 S3 审查任务 ID 同号配对）。</li>
     *   <li>调用真实 S1（POST generate 取设备清单）+ 真实 S3（results + 任务详情）。</li>
     *   <li>任一拉取失败则对单 card 降级为内置演示数据，并在返回中标注 fallback，绝不伪造。</li>
     * </ul>
     *
     * @param designTaskId 前端场景码（D001/D002/D003）或真实数字 ID
     * @return { designTaskId, realId, design:{...}, review:{...}, fallback: true|false }
     */
    public Map<String, Object> getDesignReview(String designTaskId) {
        // 场景码 → 真实数字 ID 映射（遗留演示场景；真实任务直接传任务ID或taskNo）
        String realId = mapSceneToRealId(designTaskId);

        Map<String, Object> design = null;
        Map<String, Object> review = null;
        String taskNo = null;
        boolean fallback = true;

        // 1) 真实 S1 任务成果（只读，不重跑设计）
        try {
            Map<String, Object> taskPayload = s1S3DataService.fetchTaskResult(realId);
            if (taskPayload != null) {
                taskNo = String.valueOf(taskPayload.get("taskNo"));
                design = normalizeDesignData(taskPayload);
            }
        } catch (Exception e) {
            log.warn("[design-review] 拉取 S1 任务成果失败，将使用 fallback: realId={} err={}",
                    realId, e.getMessage());
        }

        // 2) 真实 S3 审查：优先按 designTaskId(=taskNo) 查，无则回退按数字 ID
        try {
            Map<String, Object> reviewPayload = taskNo != null ? s1S3DataService.fetchReviewByDesign(taskNo) : null;
            if (reviewPayload != null && reviewPayload.get("task") != null) {
                @SuppressWarnings("unchecked")
                Map<String, Object> taskMeta = (Map<String, Object>) reviewPayload.get("task");
                review = normalizeReviewData(reviewPayload.get("results"), taskMeta);
            } else {
                Map<String, Object> rawReview = s1S3DataService.fetchReview(realId);
                Map<String, Object> rawMeta = s1S3DataService.fetchReviewTaskMeta(realId);
                review = normalizeReviewData(rawReview, rawMeta);
            }
        } catch (Exception e) {
            log.warn("[design-review] 拉取 S3 审查结果失败，将使用 fallback: realId={} err={}",
                    realId, e.getMessage());
        }

        // 3) 任一为空则对单 card 降级为演示数据
        if (design == null || review == null) {
            Map<String, Object> fallbackData = buildFallbackDesignReview(designTaskId);
            if (design == null) {
                @SuppressWarnings("unchecked")
                Map<String, Object> fd = (Map<String, Object>) fallbackData.get("design");
                design = fd;
            }
            if (review == null) {
                @SuppressWarnings("unchecked")
                Map<String, Object> fr = (Map<String, Object>) fallbackData.get("review");
                review = fr;
            }
        } else {
            fallback = false;
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("designTaskId", designTaskId);
        result.put("realId", realId);
        result.put("taskNo", taskNo);
        result.put("design", design);
        result.put("review", review);
        result.put("fallback", fallback);
        return result;
    }

    /** 前端场景码映射为真实数字 ID；已是数字则原样返回。 */
    private String mapSceneToRealId(String designTaskId) {
        if (designTaskId == null || designTaskId.isBlank()) {
            return "1";
        }
        return switch (designTaskId) {
            case "D001" -> "1";
            case "D002" -> "2";
            case "D003" -> "3";
            default -> designTaskId;
        };
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> normalizeDesignData(Map<String, Object> payload) {
        if (payload == null) return null;

        // 任务主线负载 {taskId, taskNo, taskName, projectId, status, result:{schemeName,sites,deviceLayout,...}}
        // 兼容遗留直接传 DesignData 的调用（无 taskNo/result 包装）
        Map<String, Object> raw = payload;
        Object resultObj = payload.get("result");
        if (resultObj instanceof Map<?, ?> rm) {
            raw = (Map<String, Object>) rm;
        }

        // 如果上游返回的是错误响应（含 code/message），视为无有效数据，走 fallback
        Object codeObj = raw.get("code");
        if (codeObj != null) {
            int code = toInt(codeObj);
            if (code != 200 && code != 0) {
                log.warn("[design-review] S1 返回错误响应，使用 fallback: code={} message={}", code, raw.get("message"));
                return null;
            }
        }

        // 无成果（任务未执行成功）视为无有效数据
        if (raw.get("deviceLayout") == null && raw.get("sites") == null && raw.get("devices") == null) {
            log.warn("[design-review] S1 任务无成果数据，使用 fallback: taskNo={} status={}",
                    payload.get("taskNo"), payload.get("status"));
            return null;
        }

        Map<String, Object> design = new LinkedHashMap<>();

        // 方案名优先取成果 schemeName，其次任务名；并保留任务编号用于来源标注
        String projectName = coalesceString(raw.get("schemeName"),
                String.valueOf(payload.getOrDefault("taskName", "")),
                String.valueOf(payload.getOrDefault("taskNo", "")),
                "未命名项目");
        design.put("projectName", projectName);
        design.put("projectId", String.valueOf(payload.getOrDefault("projectId", raw.getOrDefault("projectId", ""))));
        design.put("taskNo", payload.get("taskNo"));
        design.put("taskName", payload.get("taskName"));

        // 站点类型推断：优先取 designType / siteType，否则按场景默认 macro
        String siteType = coalesceString(raw.get("siteType"), raw.get("designType"), "macro");
        design.put("siteType", siteType);

        // 设备清单提取：优先取 deviceLayout，其次 sites，最后 devices
        List<Map<String, Object>> devices = extractDevices(raw);
        design.put("devices", devices);
        design.put("deviceCount", devices.size());

        return design;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> extractDevices(Map<String, Object> raw) {
        Object layoutObj = raw.get("deviceLayout");
        if (layoutObj instanceof List<?> list) {
            // 聚合同类设备（按 名称+型号+类型）为一条清单项，qty = 出现次数，避免 190 行明细刷屏
            Map<String, Map<String, Object>> agg = new LinkedHashMap<>();
            int idx = 0;
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    Map<String, Object> mm = (Map<String, Object>) m;
                    String name = coalesceString(mm.get("deviceName"), mm.get("name"), "未命名设备");
                    String model = coalesceString(mm.get("modelSpec"), mm.get("model"), "");
                    String type = coalesceString(mm.get("deviceType"), mm.get("type"), "unknown");
                    String key = type + "|" + name + "|" + model;
                    Map<String, Object> item = agg.get(key);
                    if (item == null) {
                        item = new LinkedHashMap<>();
                        item.put("deviceId", coalesceString(mm.get("positionId"), mm.get("deviceId"), mm.get("id"), "DEV-" + (++idx)));
                        item.put("deviceName", name);
                        item.put("modelSpec", model);
                        item.put("deviceType", type);
                        item.put("qty", 0);
                        agg.put(key, item);
                    }
                    item.put("qty", toInt(item.get("qty")) + 1);
                }
            }
            if (!agg.isEmpty()) {
                return new ArrayList<>(agg.values());
            }
        }

        Object sitesObj = raw.get("sites");
        if (sitesObj instanceof List<?> list) {
            List<Map<String, Object>> devices = new ArrayList<>();
            int idx = 0;
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> mm = (Map<String, Object>) m;
                    Map<String, Object> device = new LinkedHashMap<>();
                    device.put("deviceId", "SITE-" + (++idx));
                    device.put("deviceName", String.valueOf(mm.getOrDefault("siteName", "站点" + idx)));
                    device.put("deviceType", "site");
                    device.put("qty", 1);
                    devices.add(device);
                }
            }
            if (!devices.isEmpty()) return devices;
        }

        Object devicesObj = raw.get("devices");
        if (devicesObj instanceof List<?> list) {
            List<Map<String, Object>> devices = new ArrayList<>();
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> mm = (Map<String, Object>) m;
                    Map<String, Object> device = new LinkedHashMap<>();
                    device.put("deviceId", String.valueOf(mm.getOrDefault("deviceId", mm.get("id"))));
                    device.put("deviceName", String.valueOf(mm.getOrDefault("deviceName", mm.get("deviceName"))));
                    device.put("deviceType", String.valueOf(mm.getOrDefault("deviceType", mm.get("deviceType"))));
                    device.put("qty", mm.getOrDefault("qty", 1));
                    devices.add(device);
                }
            }
            return devices;
        }

        return Collections.emptyList();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> normalizeReviewData(Object rawObj, Map<String, Object> meta) {
        if (rawObj == null) return null;

        // meta 兼容两种形态：直接 task map，或 {task:{...}}（来自 S3 任务详情内层）
        Map<String, Object> task = meta;
        if (task != null && task.get("task") instanceof Map<?, ?> tm) {
            task = (Map<String, Object>) tm;
        }

        // 如果 raw 是 Map 且带错误响应（code/message），视为无有效数据，走 fallback
        if (rawObj instanceof Map<?, ?> rawMap) {
            Object codeObj = rawMap.get("code");
            if (codeObj != null) {
                int code = toInt(codeObj);
                if (code != 200 && code != 0) {
                    log.warn("[design-review] S3 返回错误响应，使用 fallback: code={} message={}",
                            code, rawMap.get("message"));
                    return null;
                }
            }
        }

        // 从任务详情抽取来源标注字段（taskName / coverageRate / 计数）
        String taskName = "";
        Double coverageRate = null;
        int criticalCount = 0, errorCount = 0, warningCount = 0, totalCount = 0;
        if (task != null) {
            taskName = String.valueOf(task.getOrDefault("taskName", ""));
            coverageRate = toDouble(task.get("coverageRate"));
            criticalCount = toInt(task.get("criticalCount"));
            errorCount = toInt(task.get("errorCount"));
            warningCount = toInt(task.get("warningCount"));
            totalCount = toInt(task.get("totalCount"));
        }

        Map<String, Object> review = new LinkedHashMap<>();
        review.put("taskName", taskName);
        review.put("coverageRate", coverageRate);
        Object reviewedAt = null;
        if (rawObj instanceof Map<?, ?> rm) {
            reviewedAt = rm.get("reviewedAt") != null ? rm.get("reviewedAt") : rm.get("createTime");
        }
        review.put("reviewedAt", reviewedAt);

        // violations 来源兼容：by-design 直接传 List；/results 传 {code,data:[...]}
        List<Map<String, Object>> violations = new ArrayList<>();
        Object dataObj = rawObj;
        if (rawObj instanceof Map<?, ?> rm) {
            dataObj = rm.get("data");
            if (dataObj == null) dataObj = rm.get("violations");
        }
        if (dataObj instanceof List<?> list) {
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> mm = (Map<String, Object>) m;
                    Map<String, Object> v = new LinkedHashMap<>();
                    v.put("rule", String.valueOf(mm.getOrDefault("ruleCode", mm.get("ruleId"))));
                    v.put("name", String.valueOf(mm.getOrDefault("ruleName", mm.get("ruleName"))));
                    v.put("riskLevel", String.valueOf(mm.getOrDefault("riskLevel", mm.get("severity"))));
                    v.put("actualValue", String.valueOf(mm.getOrDefault("actualValue", "")));
                    v.put("standardValue", String.valueOf(mm.getOrDefault("standardValue", "")));
                    violations.add(v);
                }
            }
        }

        // 空审查守卫：任务从未跑过规则（totalCount=0 且无任何条目）视为无有效数据，走 fallback，
        // 避免「演示设备清单 + 空真实审查」的混合展示造成误导
        if (totalCount == 0 && violations.isEmpty()) {
            log.warn("[design-review] S3 审查任务无有效内容（totalCount=0），使用 fallback");
            return null;
        }

        // 优先采用 S3 任务详情的权威计数，缺省再用 violations 列表推算
        long critical = criticalCount > 0 ? criticalCount
                : violations.stream().filter(v -> "critical".equalsIgnoreCase(String.valueOf(v.get("riskLevel")))).count();
        long error = errorCount > 0 ? errorCount
                : violations.stream().filter(v -> "error".equalsIgnoreCase(String.valueOf(v.get("riskLevel")))).count();
        long warning = warningCount > 0 ? warningCount
                : violations.stream().filter(v -> "warning".equalsIgnoreCase(String.valueOf(v.get("riskLevel")))).count();
        long pending = violations.stream().filter(v -> "pending".equalsIgnoreCase(String.valueOf(v.get("riskLevel")))).count();

        // 审查结论：有 critical/error 即不通过，仅 warning 为带问题通过，否则通过
        String result = (critical + error > 0) ? "rejected" : (warning > 0 ? "warning" : "approved");
        review.put("result", result);
        review.put("violations", critical + error);
        review.put("warnings", warning);
        review.put("pending", pending);
        review.put("totalCount", totalCount > 0 ? totalCount : violations.size());
        review.put("checks", violations);
        return review;
    }

    private Map<String, Object> buildFallbackDesignReview(String sceneId) {
        Map<String, Object> result = new LinkedHashMap<>();

        String projectName;
        String siteType;
        List<Map<String, Object>> devices;
        List<Map<String, Object>> checks;

        switch (sceneId == null ? "" : sceneId) {
            case "D002" -> {
                projectName = "万象城商业综合体室分设计";
                siteType = "indoor";
                devices = List.of(
                        device("RU-01", "室内远端单元 RU", "ru", 6),
                        device("HUB-01", "室分集线器 HUB", "hub", 2),
                        device("ANT-01", "全向吸顶天线", "antenna", 8),
                        device("ANT-02", "定向板状天线", "antenna", 6),
                        device("BBU-IND", "室内基带处理单元 BBU", "bbu", 1),
                        device("CABLE-01", "1/2\" 馈线", "cable", 120),
                        device("JUMPER-01", "跳线", "jumper", 48)
                );
                checks = List.of(
                        check("R-STR-001", "机房承重满足设备荷载", "warning"),
                        check("R-EMC-002", "室内电磁暴露功率密度", "approved"),
                        check("R-GND-003", "接地电阻 ≤ 5Ω", "approved"),
                        check("R-FIRE-004", "弱电井防火封堵", "approved"),
                        check("R-CABLE-005", "馈线弯曲半径合规", "approved")
                );
            }
            case "D003" -> {
                projectName = "解放路步行街微站群设计";
                siteType = "micro";
                devices = List.of(
                        device("RU-MIC-01", "微站远端单元 RU", "ru", 3),
                        device("HUB-MIC-01", "微站集线器 HUB", "hub", 1),
                        device("CAB-01", "室外一体化机柜", "cabinet", 3),
                        device("ANT-MIC-01", "微站定向天线", "antenna", 3),
                        device("CABLE-02", "光电复合缆", "cable", 80),
                        device("OPT-01", "光纤配线箱", "box", 3),
                        device("POWER-01", "室外电源模块", "power", 3)
                );
                checks = List.of(
                        check("R-EMC-001", "人行区域电磁暴露评估", "approved"),
                        check("R-STR-002", "机柜抗风压 ≥ 0.65kN/m²", "approved"),
                        check("R-GND-004", "机柜联合接地电阻", "warning"),
                        check("R-PIPE-003", "管道埋深 ≥ 0.8m", "approved"),
                        check("R-LIGHT-002", "防雷接地引下线", "approved")
                );
            }
            default -> { // D001 or any other
                projectName = "运城南风广场 5G 宏站设计";
                siteType = "macro";
                devices = List.of(
                        device("AAU-01", "64T64R 有源天线单元 AAU", "aau", 3),
                        device("RRU-01", "远端射频单元 RRU", "rru", 3),
                        device("BBU-MAC", "基带处理单元 BBU", "bbu", 1),
                        device("TOWER-01", "三管塔", "tower", 1),
                        device("GPS-01", "GPS 授时天线", "antenna", 2),
                        device("CABLE-PWR", "电力电缆 YJV22-3×25", "cable", 120),
                        device("CABLE-OPT", "单模光缆 GYTA53-48B1", "cable", 320),
                        device("GROUND-01", "接地极", "grounding", 6),
                        device("CAB-OUT", "室外机柜", "cabinet", 1)
                );
                checks = List.of(
                        check("R-PWR-001", "市电容量 ≥ 25kVA", "approved"),
                        check("R-GND-001", "接地电阻 ≤ 10Ω", "approved"),
                        check("R-STR-001", "铁塔风荷载校核", "approved"),
                        check("R-EMC-001", "电磁暴露公众限值", "approved"),
                        check("R-LIGHT-001", "防雷等级第三类", "approved"),
                        check("R-PIPE-001", "馈线窗密封及防水", "approved")
                );
            }
        }

        Map<String, Object> design = new LinkedHashMap<>();
        design.put("projectName", projectName);
        design.put("projectId", sceneId);
        design.put("siteType", siteType);
        design.put("deviceCount", devices.size());
        design.put("devices", devices);

        Map<String, Object> review = new LinkedHashMap<>();
        review.put("result", "approved");
        review.put("reviewedAt", LocalDateTime.now().toString());
        review.put("violations", 0);
        review.put("warnings", 1);
        review.put("pending", 0);
        review.put("checks", checks);
        review.put("degraded", true);

        result.put("design", design);
        result.put("review", review);
        return result;
    }

    /**
     * 任务看板：聚合 S1 任务 + S3 审查 + S4 BOM 状态，按任务主线串联。
     * <p>调用：S1 /api/m03/design/tasks、S3 /api/v1/s3/review/task、本地 bomTaskMapper。</p>
     */
    public Map<String, Object> getKanban() {
        Map<String, Object> result = new LinkedHashMap<>();
        List<Map<String, Object>> s1Tasks = new ArrayList<>();
        Map<String, Map<String, Object>> s3ByTaskNo = new LinkedHashMap<>();
        int s1Total = 0, s1Completed = 0, s3Total = 0, s4Total = 0;

        try {
            s1Tasks = s1S3DataService.fetchS1Tasks();
        } catch (Exception e) {
            log.warn("[kanban] 拉取 S1 任务失败: {}", e.getMessage());
        }
        s1Total = s1Tasks.size();
        for (Map<String, Object> t : s1Tasks) {
            if ("completed".equalsIgnoreCase(String.valueOf(t.get("status")))) s1Completed++;
        }

        try {
            List<Map<String, Object>> s3Tasks = s1S3DataService.fetchS3Tasks();
            s3Total = s3Tasks.size();
            for (Map<String, Object> t : s3Tasks) {
                String dtk = String.valueOf(t.get("designTaskId"));
                if (dtk != null && !dtk.isBlank() && !"null".equals(dtk)) {
                    s3ByTaskNo.putIfAbsent(dtk, t);
                }
            }
        } catch (Exception e) {
            log.warn("[kanban] 拉取 S3 任务列表失败: {}", e.getMessage());
        }

        // S4 BOM 任务：按 designTaskId 聚合（取最新一条 + 总数）
        Map<String, Map<String, Object>> bomByDesign = new LinkedHashMap<>();
        Map<String, Integer> bomCountByDesign = new LinkedHashMap<>();
        try {
            List<BomTask> allBom = bomTaskMapper.selectList(
                    new LambdaQueryWrapper<BomTask>()
                            .orderByDesc(BomTask::getCreatedAt)
                            .last("LIMIT 200"));
            for (BomTask bt : allBom) {
                if (bt.getDesignTaskId() == null) continue;
                if (!bomByDesign.containsKey(bt.getDesignTaskId())) {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("taskId", bt.getTaskId());
                    m.put("status", bt.getStatus());
                    m.put("totalQty", bt.getTotalQty());
                    m.put("projectId", bt.getProjectId());
                    m.put("createTime", bt.getCreatedAt() == null ? null
                            : bt.getCreatedAt().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));
                    bomByDesign.put(bt.getDesignTaskId(), m);
                }
                bomCountByDesign.merge(bt.getDesignTaskId(), 1, Integer::sum);
            }
            s4Total = bomByDesign.size();
        } catch (Exception e) {
            log.warn("[kanban] 拉取 S4 BOM 任务失败: {}", e.getMessage());
        }

        // 组装每个 S1 任务的看板行
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Map<String, Object> t : s1Tasks) {
            String taskNo = String.valueOf(t.get("taskNo"));
            Map<String, Object> s3 = s3ByTaskNo.get(taskNo);
            String designIdStr = String.valueOf(t.get("id"));
            Map<String, Object> bom = bomByDesign.get(designIdStr);
            int bomCount = bomCountByDesign.getOrDefault(designIdStr, 0);

            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", t.get("id"));
            row.put("taskNo", t.get("taskNo"));
            row.put("taskName", t.get("taskName"));
            row.put("projectId", t.get("projectId"));
            row.put("updatedAt", t.get("updatedAt"));
            // S1 状态
            Map<String, Object> s1Cell = new LinkedHashMap<>();
            s1Cell.put("status", t.get("status"));
            row.put("s1", s1Cell);
            // S3 状态
            Map<String, Object> s3Cell = new LinkedHashMap<>();
            if (s3 != null) {
                s3Cell.put("status", s3.get("taskStatus"));
                s3Cell.put("taskName", s3.get("taskName"));
                s3Cell.put("coverageRate", s3.get("coverageRate"));
                s3Cell.put("totalCount", s3.get("totalCount"));
                s3Cell.put("criticalCount", s3.get("criticalCount"));
                s3Cell.put("errorCount", s3.get("errorCount"));
                s3Cell.put("warningCount", s3.get("warningCount"));
            }
            row.put("s3", s3Cell);
            // S4 状态
            Map<String, Object> s4Cell = new LinkedHashMap<>();
            s4Cell.put("status", bom != null ? bom.get("status") : null);
            s4Cell.put("taskId", bom != null ? bom.get("taskId") : null);
            s4Cell.put("totalQty", bom != null ? bom.get("totalQty") : null);
            s4Cell.put("createTime", bom != null ? bom.get("createTime") : null);
            s4Cell.put("bomCount", bomCount);
            row.put("s4", s4Cell);
            rows.add(row);
        }

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("s1Total", s1Total);
        summary.put("s1Completed", s1Completed);
        summary.put("s3Total", s3Total);
        summary.put("s3MatchedByTaskNo", rows.stream().filter(r -> r.get("s3") instanceof Map
                && ((Map<?, ?>) r.get("s3")).get("taskName") != null).count());
        summary.put("s4Total", s4Total);

        result.put("summary", summary);
        result.put("rows", rows);
        return result;
    }

    private Map<String, Object> device(String deviceId, String deviceName, String deviceType, int qty) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("deviceId", deviceId);
        m.put("deviceName", deviceName);
        m.put("deviceType", deviceType);
        m.put("qty", qty);
        return m;
    }

    private Map<String, Object> check(String rule, String name, String riskLevel) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("rule", rule);
        m.put("name", name);
        m.put("riskLevel", riskLevel);
        return m;
    }

    private String coalesceString(Object... values) {
        for (Object v : values) {
            if (v != null && !String.valueOf(v).isBlank()) {
                return String.valueOf(v);
            }
        }
        return "";
    }

    /** 将计数对象安全转为 int（兼容 Integer / String / null）。 */
    private int toInt(Object o) {
        if (o instanceof Number n) {
            return n.intValue();
        }
        if (o instanceof String s) {
            try {
                return Integer.parseInt(s.trim());
            } catch (NumberFormatException ignored) {
                return 0;
            }
        }
        return 0;
    }

    /** 将对象安全转为 Double（兼容 Number / String / null），无法解析返回 null。 */
    private Double toDouble(Object o) {
        if (o instanceof Number n) {
            return n.doubleValue();
        }
        if (o instanceof String s) {
            try {
                return Double.parseDouble(s.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
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
