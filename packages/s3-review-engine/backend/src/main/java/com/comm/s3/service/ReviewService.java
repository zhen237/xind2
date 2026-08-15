package com.comm.s3.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.comm.s3.entity.S3ReviewResult;
import com.comm.s3.entity.S3ReviewTask;
import com.comm.s3.entity.S3SafetyRule;
import com.comm.s3.cache.DesignDataCacheService;
import com.comm.s3.service.S3ReviewResultService;
import com.comm.s3.service.S3SafetyRuleService;
import com.comm.s3.util.OkHttpUtil;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class ReviewService {

    // 任务状态枚举（严格遵循需求：PENDING排队中 → PROCESSING审查中 → COMPLETED完成 / FAILED失败）
    public static final String STATUS_PENDING = "PENDING";
    public static final String STATUS_PROCESSING = "PROCESSING";
    public static final String STATUS_COMPLETED = "COMPLETED";
    public static final String STATUS_FAILED = "FAILED";

    // 对接/执行异常原因写入结果表时使用的系统伪规则标识（不新增数据库列，复用 s3_review_result）
    public static final String SYSTEM_RULE_CODE = "SYSTEM";

    @Autowired
    private S3SafetyRuleService safetyRuleService;

    @Autowired
    private S3ReviewResultService reviewResultService;

    @Autowired
    private S3ReviewTaskService reviewTaskService;

    @Value("${s3.python.engine-url}")
    private String engineUrl;

    @Value("${s3.python.health-url:}")
    private String healthUrl;

    private final ObjectMapper objectMapper = new ObjectMapper();
    
    // S1 设计数据缓存：Redis 优先 + 内存兜底（见 DesignDataCacheService，B-1 需求）
    @Autowired
    private DesignDataCacheService designCache;

    /**
     * 存储S1传来的设计数据
     */
    public void setDesignData(Long taskId, Map<String, Object> designData) {
        String dtId = extractDesignTaskId(designData);
        designCache.store(taskId, dtId, designData);
        log.info("Stored design data for task {} (designTaskId={}), dataSource={}",
                taskId, dtId, designCache.isRedisAvailable() ? "Redis" : "memory");
    }

    /** 从 design_data 包装中提取 designTaskId（作为 Redis 持久化主键） */
    private String extractDesignTaskId(Map<String, Object> designData) {
        if (designData == null) return null;
        Object dd = designData.get("design_data");
        if (dd instanceof Map) {
            Object id = ((Map<?, ?>) dd).get("designTaskId");
            return id == null ? null : String.valueOf(id);
        }
        return null;
    }

    /** 同一份图纸（designTaskId）是否已在缓存中（供 S1 重复提交复用判断） */
    public boolean isDesignCached(String designTaskId) {
        return designCache.existsByDesignTaskId(designTaskId);
    }

    /** 按 designTaskId 取缓存的设计数据（供 S1 重复提交复用） */
    public Map<String, Object> getCachedDesign(String designTaskId) {
        return designCache.getByDesignTaskId(designTaskId);
    }

    /**
     * 获取S1传来的设计数据
     */
    public Map<String, Object> getDesignData(Long taskId) {
        return designCache.getByTaskId(taskId);
    }

    /**
     * 获取真实工程的设计元数据（供前端报告页展示真实工程信息：工程名称、区域、图层分布、设备总数等）。
     * 数据取自 S1 设计数据缓存（内存态，与现有实现一致），不新增任何表字段，不改端口与业务流程。
     * 若任务未注入真实设计数据（如演示用占位任务），返回 null。
     */
    public Map<String, Object> getDesignMeta(Long taskId) {
        // 带数据来源的三级读取（Redis → 内存 → MySQL），用于标识 dataSource
        DesignDataCacheService.LookupResult lr = designCache.getByTaskIdWithSource(taskId);
        Map<String, Object> wrapper = lr.getData();
        if (wrapper == null) {
            return null;
        }
        Object dd = wrapper.get("design_data");
        if (!(dd instanceof Map)) {
            return null;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> designData = (Map<String, Object>) dd;

        Map<String, Object> meta = new HashMap<>();
        meta.put("designTaskId", designData.get("designTaskId"));
        meta.put("designTaskName", designData.get("designTaskName"));
        meta.put("designType", designData.get("designType"));

        Object m = designData.get("metadata");
        if (m instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> md = (Map<String, Object>) m;
            meta.put("projectName", md.get("projectName"));
            meta.put("region", md.get("region"));
            meta.put("layerCounts", md.get("layerCounts"));
            meta.put("totalDevices", md.get("totalDevices"));
        }
        Object devs = designData.get("devices");
        if (devs instanceof java.util.List) {
            meta.put("deviceCount", ((java.util.List<?>) devs).size());
        }
        // 数据来源标识（三级存储）：Redis 持久化 / 内存态(重启即丢) / 数据库恢复（MySQL 永久落库）
        String src = lr.getSource();
        boolean fromDb = "DATABASE".equals(src);
        boolean fromRedis = "REDIS".equals(src);
        meta.put("cached", fromRedis || fromDb);
        if (fromDb) {
            meta.put("dataSource", "database(数据库恢复)");
        } else if (fromRedis) {
            meta.put("dataSource", "Redis缓存(持久化)");
        } else {
            meta.put("dataSource", "内存态(重启即丢)");
        }
        return meta;
    }

    /**
     * 计算审查覆盖率
     * 覆盖率口径：已具备设计数据、可对这些规则做真实参数比对的规则数 / 数据库实际规则总数 * 100%
     * 统计基准与数据库实际规则数量（totalRules，来自 s3_safety_rule 表）严格保持一致。
     */
    public double calculateCoverageRate(Long taskId, int violationCount, int totalRules) {
        if (totalRules == 0) {
            return 0.0;
        }

        // 是否已接收设计数据：有数据才能对规则做真实比对
        Map<String, Object> designData = designCache.getByTaskId(taskId);
        boolean hasDesignData = designData != null && designData.containsKey("design_data");
        if (!hasDesignData) {
            return 0.0;
        }

        // 动态探测真实数据实际具备的可比对参数，确定哪些规则可真实校验。
        // 真实通信光纤数据支撑：容量校验 FT-001（capacity+fibreUsed）；
        // 弯曲半径需缆径>0(EL-001)；载流量需截面+电流(EL-002)；接地电阻需电阻字段(EL-003)。
        @SuppressWarnings("unchecked")
        Map<String, Object> dd = (Map<String, Object>) designData.get("design_data");
        Object devObj = dd.get("devices");
        boolean cCapacity = false, cDiameter = false, cGrounding = false, cCurrent = false;
        if (devObj instanceof java.util.List) {
            for (Object o : (java.util.List<?>) devObj) {
                if (!(o instanceof Map)) continue;
                Map<String, Object> d = (Map<String, Object>) o;
                if (d.get("capacity") != null && d.get("fibreUsed") != null) cCapacity = true;
                Object dia = d.get("cableDiameter");
                if (dia instanceof Number && ((Number) dia).doubleValue() > 0) cDiameter = true;
                if (d.get("groundingResistance") != null) cGrounding = true;
                if (d.get("crossSection") != null && d.get("actualCurrent") != null) cCurrent = true;
            }
        }
        // 管线埋深可比对性(B-4)：pipeline 数组中存在「敷设方式+场景+实测埋深>0」的管线记录
        boolean cBuried = false;
        Object pipeObj = dd.get("pipeline");
        if (pipeObj instanceof java.util.List) {
            for (Object o : (java.util.List<?>) pipeObj) {
                if (!(o instanceof Map)) continue;
                Map<String, Object> p = (Map<String, Object>) o;
                Object laying = p.get("layingType") != null ? p.get("layingType") : p.get("laying_type");
                Object scenario = p.get("scenario") != null ? p.get("scenario") : p.get("burialScenario");
                Object depth = p.get("burialDepth") != null ? p.get("burialDepth") : p.get("burial_depth");
                if (laying != null && scenario != null && depth instanceof Number && ((Number) depth).doubleValue() > 0) {
                    cBuried = true;
                    break;
                }
            }
        }
        // 覆盖率口径：真实数据可支撑真实比对的规则大类数 / 数据库规则总数 * 100%
        int covered = (cCapacity ? 1 : 0) + (cDiameter ? 1 : 0) + (cGrounding ? 1 : 0) + (cCurrent ? 1 : 0) + (cBuried ? 1 : 0);
        double coverage = Math.min(100.0, (double) covered / totalRules * 100);
        return Math.round(coverage * 100) / 100.0;
    }

    @Transactional
    public void executeReview(S3ReviewTask task) {
        // 状态校验：仅"排队中(PENDING)"的任务可开始审查
        if (!STATUS_PENDING.equals(task.getTaskStatus())) {
            log.warn("Task {} cannot be executed, current status: {}", task.getId(), task.getTaskStatus());
            return;
        }

        try {
            // 更新状态为审查中
            task.setTaskStatus(STATUS_PROCESSING);
            task.setUpdateTime(LocalDateTime.now());
            reviewTaskService.updateById(task);
            log.info("Task {} status changed to PROCESSING", task.getId());

            // 删除该任务之前的审查结果
            LambdaQueryWrapper<S3ReviewResult> deleteWrapper = new LambdaQueryWrapper<>();
            deleteWrapper.eq(S3ReviewResult::getTaskId, task.getId());
            reviewResultService.remove(deleteWrapper);
            log.info("Cleared previous results for task {}", task.getId());

            // 获取所有安全规则
            List<S3SafetyRule> rules = safetyRuleService.list();
            log.info("Loaded {} safety rules for task {}", rules.size(), task.getId());

            // 构建请求参数
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("task_id", task.getId());
            // design_task_id 兜底，避免为空导致 Python 接口参数校验失败
            String designTaskId = (task.getDesignTaskId() != null && !task.getDesignTaskId().trim().isEmpty())
                    ? task.getDesignTaskId() : ("TASK-" + task.getId());
            requestBody.put("design_task_id", designTaskId);
            requestBody.put("task_name", task.getTaskName());

            // 下发真实设计数据，供 Python 引擎做真实参数化校验
            // 将缓存中的真实设计数据（来自真实工程竣工图）下发给引擎，
            // 所有违规均由真实参数比对公式计算得出，不存在随机/模拟违规。
            Map<String, Object> cachedDesign = designCache.getByTaskId(task.getId());
            if (cachedDesign != null && cachedDesign.get("design_data") != null) {
                requestBody.put("design_data", cachedDesign.get("design_data"));
            }
            
            List<Map<String, Object>> items = new ArrayList<>();
            for (S3SafetyRule rule : rules) {
                Map<String, Object> item = new HashMap<>();
                item.put("rule_id", rule.getId());
                item.put("rule_code", rule.getRuleCode());
                item.put("rule_name", rule.getRuleName());
                item.put("category", rule.getCategory());
                item.put("risk_level", rule.getRiskLevel());
                item.put("threshold", rule.getThreshold());
                items.add(item);
            }
            // 追加真实通信容量校验规则（FT-001）：对应真实数据具备的光纤容量字段，
            // 不写入 s3_safety_rule 表（保持数据库规则数量不变，仅作为内存附加校验项下发引擎），
            // 用于基于真实工程数据产出真实违规（已用光纤数 > 额定容量）。
            Map<String, Object> ftItem = new HashMap<>();
            ftItem.put("rule_id", 100L);
            ftItem.put("rule_code", "FT-001");
            ftItem.put("rule_name", "光缆/分纤箱容量校验");
            ftItem.put("category", "通信");
            ftItem.put("risk_level", "error");
            ftItem.put("threshold", "已用光纤数≤额定容量");
            items.add(ftItem);

            requestBody.put("items", items);

            String jsonRequest = objectMapper.writeValueAsString(requestBody);
            log.info("Calling Python engine, taskId: {}, requestSize: {}, url: {}", 
                    task.getId(), items.size(), engineUrl);

            // 调用Python引擎
            String response = OkHttpUtil.postJson(engineUrl, jsonRequest);

            if (response == null) {
                log.error("Python engine returned null response for task {}", task.getId());
                throw new RuntimeException("Python engine call failed, no response");
            }

            log.debug("Python engine response for task {}: {}", task.getId(), response.length() > 500 ? response.substring(0, 500) + "..." : response);

            // 解析响应
            JsonNode root = objectMapper.readTree(response);
            if (root.get("code").asInt() != 200) {
                String errorMsg = root.has("message") ? root.get("message").asText() : "unknown error";
                log.error("Python engine returned error for task {}: {}", task.getId(), errorMsg);
                throw new RuntimeException("Python engine returned error: " + errorMsg);
            }

            // 处理审查结果
            List<S3ReviewResult> results = new ArrayList<>();
            JsonNode data = root.get("data");
            
            int criticalCount = 0;
            int errorCount = 0;
            int warningCount = 0;

            if (data != null && data.isArray()) {
                for (JsonNode item : data) {
                    S3ReviewResult result = new S3ReviewResult();
                    result.setTaskId(task.getId());
                    result.setRuleId(item.has("rule_id") ? item.get("rule_id").asLong() : 0);
                    String ruleCode = item.has("rule_code") ? item.get("rule_code").asText() : "";
                    result.setRuleCode(ruleCode);
                    result.setRuleName(item.has("rule_name") ? item.get("rule_name").asText() : "");
                    result.setActualValue(item.has("actual_value") ? item.get("actual_value").asText() : "");
                    result.setStandardValue(item.has("standard_value") ? item.get("standard_value").asText() : "");
                    
                    // 处理坐标数据
                    if (item.has("coordinates") && item.get("coordinates").isArray()) {
                        JsonNode coords = item.get("coordinates");
                        StringBuilder sb = new StringBuilder();
                        sb.append("[");
                        for (int i = 0; i < coords.size(); i++) {
                            if (i > 0) sb.append(",");
                            sb.append(coords.get(i).asText());
                        }
                        sb.append("]");
                        result.setCoordinates(sb.toString());
                    }
                    
                    result.setRiskLevel(item.has("risk_level") ? item.get("risk_level").asText() : "warning");
                    result.setRemark(item.has("suggestion") ? item.get("suggestion").asText() : "");
                    result.setCreateTime(LocalDateTime.now());
                    
                    results.add(result);

                    // 系统伪规则(SYSTEM)为对接/执行异常说明，不计入违规统计
                    if (SYSTEM_RULE_CODE.equals(ruleCode)) {
                        continue;
                    }
                    // 统计各等级违规数量
                    String riskLevel = result.getRiskLevel();
                    if ("critical".equals(riskLevel)) criticalCount++;
                    else if ("error".equals(riskLevel)) errorCount++;
                    else if ("warning".equals(riskLevel)) warningCount++;
                }
            }

            // 批量保存审查结果
            if (!results.isEmpty()) {
                reviewResultService.saveBatch(results);
                log.info("Saved {} review results for task {}", results.size(), task.getId());
            }

            // 更新任务统计信息（使用新的覆盖率计算逻辑）
            int totalViolations = criticalCount + errorCount + warningCount;
            double coverage = calculateCoverageRate(task.getId(), totalViolations, rules.size());

            task.setTaskStatus(STATUS_COMPLETED);
            task.setCoverageRate(coverage);
            task.setTotalCount(rules.size());
            task.setCriticalCount(criticalCount);
            task.setErrorCount(errorCount);
            task.setWarningCount(warningCount);
            task.setUpdateTime(LocalDateTime.now());
            reviewTaskService.updateById(task);

            log.info("Review completed successfully, taskId: {}, coverage: {}, violations: {}", 
                    task.getId(), task.getCoverageRate(), results.size());

        } catch (Exception e) {
            // 接口容错与降级：审查执行（含 Python 引擎调用超时/500/格式异常）失败时，
            // 任务保存为 FAILED 状态，并在报告中写明对接异常原因，前端可展示失败状态，不直接崩溃。
            String reason = "审查执行失败: " + (e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName());
            log.error("Review failed for taskId: {}", task.getId(), e);
            recordIntegrationFailure(task.getId(), reason);
        }
    }

    /**
     * 记录对接/执行异常：将审查任务标记为 FAILED，并在结果表中写入一条 SYSTEM 伪规则行，
     * 其 remark 携带明确的异常原因，供前端报告页展示"对接异常原因"。
     * 不新增任何数据库列，复用 s3_review_result 表。
     */
    @Transactional
    public void recordIntegrationFailure(Long taskId, String reason) {
        S3ReviewTask task = reviewTaskService.getById(taskId);
        if (task == null) {
            log.warn("recordIntegrationFailure: task not found {}", taskId);
            return;
        }
        task.setTaskStatus(STATUS_FAILED);
        task.setUpdateTime(LocalDateTime.now());
        reviewTaskService.updateById(task);
        log.info("Task {} status changed to FAILED, reason: {}", taskId, reason);

        S3ReviewResult failRow = new S3ReviewResult();
        failRow.setTaskId(taskId);
        failRow.setRuleId(0L);
        failRow.setRuleCode(SYSTEM_RULE_CODE);
        failRow.setRuleName("S1/引擎对接异常");
        failRow.setActualValue("");
        failRow.setStandardValue("");
        failRow.setCoordinates("[]");
        failRow.setRiskLevel("error");
        failRow.setRemark(reason);
        failRow.setCreateTime(LocalDateTime.now());
        reviewResultService.save(failRow);
        log.info("Recorded integration failure reason for task {}", taskId);
    }

    @Transactional
    public void recheckReview(Long taskId) {
        S3ReviewTask task = reviewTaskService.getById(taskId);
        if (task == null) {
            throw new RuntimeException("Task not found: " + taskId);
        }
        
        log.info("Starting recheck for task {}", taskId);
        
        // 重置任务状态为排队中（仅 PENDING 可被 executeReview 执行）
        task.setTaskStatus(STATUS_PENDING);
        task.setCoverageRate(0.0);
        task.setCriticalCount(0);
        task.setErrorCount(0);
        task.setWarningCount(0);
        reviewTaskService.updateById(task);
        
        // 重新执行审查
        executeReview(task);
    }

    /**
     * 检查Python引擎健康状态
     */
    public boolean isEngineHealthy() {
        if (healthUrl == null || healthUrl.isEmpty()) {
            String baseUrl = engineUrl;
            if (baseUrl.contains("/check")) {
                baseUrl = baseUrl.substring(0, baseUrl.lastIndexOf("/check"));
            }
            healthUrl = baseUrl + "/health";
        }
        return OkHttpUtil.checkHealth(healthUrl);
    }
}
