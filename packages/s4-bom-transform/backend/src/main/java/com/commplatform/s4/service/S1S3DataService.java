package com.commplatform.s4.service;

import com.commplatform.s4.config.S4Config;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 跨赛题数据服务 — 对接 S1 设计成果 与 S3 审查结果（闭合 FR-10 契约）。
 *
 * <p>dataSource 双模式：
 * <ul>
 *   <li>mock — 请求 dev-proxy（默认 8090），由 dev-proxy 模拟 S1/S3 返回</li>
 *   <li>real — 请求 S1/S3 真实服务地址（联调日配置 s4.integration.*-url）</li>
 * </ul>
 *
 * <p>审查闸门：BOM 生成前必须确认设计已审查通过（approved）；
 * 审查服务不可达时降级放行并告警（联调期避免阻断主链路）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class S1S3DataService {

    private final S4Config s4Config;
    private final RestTemplate restTemplate;

    /** 任务主线：按任务ID（数字）或任务编号 taskNo 查询 S1 任务成果（含解析后的设计数据）。
     * <p>只读不重跑设计：数字ID走 {@code GET /tasks/{id}/result}，taskNo 走
     * {@code GET /tasks/by-no/{taskNo}/result}，均携带 X-API-Key。</p>
     * @return {taskId, taskNo, taskName, projectId, status, result:{schemeName,sites,deviceLayout,...}}
     */
    public Map<String, Object> fetchTaskResult(String idOrTaskNo) {
        if (idOrTaskNo == null || idOrTaskNo.isBlank()) {
            return null;
        }
        String path = idOrTaskNo.matches("\\d+")
                ? "/api/m03/design/tasks/" + idOrTaskNo + "/result"
                : "/api/m03/design/tasks/by-no/" + idOrTaskNo + "/result";
        String url = join(s4Config.getIntegration().getS1Url(), path);
        return getWithKey(url, "S1 任务成果");
    }

    /** 任务主线：拉取 S1 任务列表（前端选真实任务用）。 */
    public List<Map<String, Object>> fetchS1Tasks() {
        String url = join(s4Config.getIntegration().getS1Url(), "/api/m03/design/tasks");
        Map<String, Object> body = getWithKey(url, "S1 任务列表");
        if (body != null && body.get("data") instanceof List<?> list) {
            List<Map<String, Object>> tasks = new ArrayList<>();
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> task = (Map<String, Object>) m;
                    tasks.add(task);
                }
            }
            return tasks;
        }
        return new ArrayList<>();
    }

    /** 任务看板：拉取 S3 审查任务列表（按 designTaskId 串联到 S1 任务）。 */
    public List<Map<String, Object>> fetchS3Tasks() {
        String url = join(s4Config.getIntegration().getS3Url(), "/api/v1/s3/review/task");
        log.info("[S3 审查任务列表] GET {}", url);
        try {
            HttpEntity<Void> entity = buildEntity();
            ResponseEntity<Map> resp = restTemplate.exchange(url, HttpMethod.GET, entity, Map.class);
            Map<String, Object> body = resp.getBody();
            if (body == null) return new ArrayList<>();
            Object data = body.get("data");
            if (data instanceof List<?> list) {
                List<Map<String, Object>> tasks = new ArrayList<>();
                for (Object o : list) {
                    if (o instanceof Map<?, ?> m) {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> task = (Map<String, Object>) m;
                        tasks.add(task);
                    }
                }
                return tasks;
            }
            return new ArrayList<>();
        } catch (Exception e) {
            log.warn("[S3] 审查任务列表拉取失败: err={}", e.getMessage());
            return new ArrayList<>();
        }
    }

    /** [FR-10] 拉取 S3 审查结果（真实 S3: /api/v1/s3/review/task/{id}/results，返回 violations 数组）。 */
    public Map<String, Object> fetchReview(String designTaskId) {
        String url = join(s4Config.getIntegration().getS3Url(), "/api/v1/s3/review/task/" + designTaskId + "/results");
        return get(url, "S3 审查结果");
    }

    /** 任务主线：按来源设计任务编号(designTaskId = S1 taskNo)查 S3 审查任务与结果。
     * @return {task:{...}, results:[...], statistics:{...}}，未找到返回 null
     */
    public Map<String, Object> fetchReviewByDesign(String designTaskId) {
        if (designTaskId == null || designTaskId.isBlank()) {
            return null;
        }
        String url = join(s4Config.getIntegration().getS3Url(),
                "/api/v1/s3/review/task/by-design/" + designTaskId);
        log.info("[S3 审查(by-design)] GET {}", url);
        try {
            HttpEntity<Void> entity = buildEntity();
            ResponseEntity<Map> resp = restTemplate.exchange(url, HttpMethod.GET, entity, Map.class);
            Map<String, Object> body = resp.getBody();
            if (body != null && body.get("data") instanceof Map<?, ?> dm) {
                @SuppressWarnings("unchecked")
                Map<String, Object> inner = (Map<String, Object>) dm;
                return inner;
            }
            return null;
        } catch (Exception e) {
            log.warn("[S3] 按设计任务查审查失败: designTaskId={} err={}", designTaskId, e.getMessage());
            return null;
        }
    }

    /** [FR-10] 拉取 S3 审查任务详情（taskName / coverageRate / 计数），用于前端来源标注。
     * <p>S3 响应形如 {code,message,data:{task:{...},results:[...]}}，此处抽取内层 data（含 task）。</p>
     */
    public Map<String, Object> fetchReviewTaskMeta(String reviewTaskId) {
        String url = join(s4Config.getIntegration().getS3Url(), "/api/v1/s3/review/task/" + reviewTaskId);
        log.info("[S3 审查任务详情] GET {}", url);
        try {
            HttpEntity<Void> entity = buildEntity();
            ResponseEntity<Map> resp = restTemplate.exchange(url, HttpMethod.GET, entity, Map.class);
            Map<String, Object> body = resp.getBody();
            if (body != null && body.get("data") instanceof Map<?, ?> dm) {
                @SuppressWarnings("unchecked")
                Map<String, Object> inner = (Map<String, Object>) dm;
                return inner; // {task:{...}, results:[...]}
            }
            return body;
        } catch (Exception e) {
            log.warn("[S3] 审查任务详情拉取失败: reviewTaskId={} err={}", reviewTaskId, e.getMessage());
            return null;
        }
    }

    /** GET 调用 S1 内部接口（只读），携带 X-API-Key（S1 内部接口要求）。
     * <p>S1 契约 {code, message, data: {...}}，抽取内层 data 返回。</p>
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> getWithKey(String url, String desc) {
        log.info("[{}] GET {}", desc, url);
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            String apiKey = s4Config.getIntegration().getS1ApiKey();
            if (apiKey != null && !apiKey.isBlank()) {
                headers.set("X-API-Key", apiKey);
            }
            HttpEntity<Void> entity = new HttpEntity<>(headers);
            ResponseEntity<Map> resp = restTemplate.exchange(url, HttpMethod.GET, entity, Map.class);
            Map<String, Object> body = resp.getBody();
            if (body == null) {
                return null;
            }
            Object data = body.get("data");
            if (data instanceof Map<?, ?> dm) {
                Map<String, Object> inner = (Map<String, Object>) dm;
                if (body.containsKey("data")
                        && (body.containsKey("code") || body.containsKey("status") || body.containsKey("message"))) {
                    return inner;
                }
            }
            return body;
        } catch (Exception e) {
            log.warn("[{}] 调用失败: {}", desc, e.getMessage());
            return null;
        }
    }

    /**
     * [FR-10] 四档分级审查闸门 — 消费 S3 分级违规数据（critical/error/warning/pending）。
     *
     * <p>分级响应策略（替代二元 approved 拦截）：
     * <ul>
     *   <li>BLOCKED                — 存在 critical/error 违规，拦截 BOM 生成</li>
     *   <li>ALLOWED_WITH_WARNINGS  — 仅 warning/pending，放行但携带整改标记</li>
     *   <li>ALLOWED                — 无违规，或 S3 不可达降级放行（degraded=true）</li>
     * </ul>
     *
     * @return {decision, result, counts{critical,error,warning,pending}, blockers[], violations[], degraded}
     */
    public Map<String, Object> checkGate(String designTaskId) {
        Map<String, Object> result = new LinkedHashMap<>();
        Map<String, Object> counts = new LinkedHashMap<>();
        counts.put("critical", 0); counts.put("error", 0);
        counts.put("warning", 0); counts.put("pending", 0);
        result.put("counts", counts);
        result.put("blockers", new ArrayList<>());
        result.put("violations", new ArrayList<>());

        try {
            Map<String, Object> review = fetchReviewForGate(designTaskId);
            result.put("result", review.get("result"));

            // 真实 S3 契约：violations 数组嵌套在 data 字段，分级字段为 riskLevel（非 severity）
            Object violationsObj = review.get("data");
            if (violationsObj == null) {
                violationsObj = review.get("violations");
            }
            List<Map<String, Object>> violations = new ArrayList<>();
            if (violationsObj instanceof List<?> list) {
                for (Object o : list) {
                    if (o instanceof Map<?, ?> m) {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> v = (Map<String, Object>) m;
                        violations.add(v);
                    }
                }
            }
            result.put("violations", violations);

            List<Map<String, Object>> blockers = new ArrayList<>();
            for (Map<String, Object> v : violations) {
                String severity = String.valueOf(v.getOrDefault("riskLevel", v.get("severity"))).toLowerCase();
                if ("null".equals(severity) || severity.isEmpty()) {
                    severity = "pending";
                }
                if (counts.containsKey(severity)) {
                    counts.put(severity, toInt(counts.get(severity)) + 1);
                }
                if ("critical".equals(severity) || "error".equals(severity)) {
                    blockers.add(v);
                }
            }
            result.put("blockers", blockers);

            String decision;
            if (!blockers.isEmpty()) {
                decision = "blocked";
            } else if (toInt(counts.get("warning")) > 0 || toInt(counts.get("pending")) > 0) {
                decision = "allowed_with_warnings";
            } else {
                decision = "allowed";
            }
            result.put("decision", decision);
            result.put("degraded", false);
            return result;

        } catch (Exception e) {
            // S3 不可达 → 降级放行 + 告警（联调期保证主链路可用）
            log.warn("[S3] 审查服务不可达，降级放行: designTaskId={} err={}", designTaskId, e.getMessage());
            result.put("decision", "allowed");
            result.put("result", "unknown");
            result.put("degraded", true);
            return result;
        }
    }

    /**
     * 审查闸门数据源（任务主线优先）：
     * ① 若 designTaskId 可解析出 S1 任务 taskNo，则按 designTaskId 查 S3（真实链路）；
     * ② 否则回退按数字 ID 查 /results（遗留兼容）。
     */
    private Map<String, Object> fetchReviewForGate(String designTaskId) {
        // ① 真实链路：S1 任务 → taskNo → S3 by-design
        try {
            Map<String, Object> taskPayload = fetchTaskResult(designTaskId);
            if (taskPayload != null && taskPayload.get("taskNo") != null) {
                Map<String, Object> byDesign = fetchReviewByDesign(String.valueOf(taskPayload.get("taskNo")));
                if (byDesign != null && byDesign.get("results") != null) {
                    Map<String, Object> review = new LinkedHashMap<>();
                    review.put("data", byDesign.get("results"));
                    review.put("result", "reviewed");
                    return review;
                }
            }
        } catch (Exception e) {
            log.warn("[S3] 按任务链路查审查失败，回退数字ID: designTaskId={} err={}", designTaskId, e.getMessage());
        }
        // ② 回退：按数字 ID
        return fetchReview(designTaskId);
    }

    /**
     * @deprecated 二元判定已被 {@link #checkGate(String)} 四档分级闸门取代，保留兼容。
     */
    @Deprecated
    public boolean isApproved(String designTaskId) {
        return !"blocked".equals(checkGate(designTaskId).get("decision"));
    }

    // ────────────────────────────────────────

    @SuppressWarnings("unchecked")
    private Map<String, Object> get(String url, String desc) {
        log.info("[{}] GET {}", desc, url);
        HttpEntity<Void> entity = buildEntity();
        ResponseEntity<Map> resp = restTemplate.exchange(url, HttpMethod.GET, entity, Map.class);
        Map<String, Object> body = resp.getBody();
        if (body == null) {
            body = new HashMap<>();
        }
        Object data = body.get("data");
        // S1 契约：{status, designTaskId, data:{...}}；S3 契约：{status, result, ...}
        if (data instanceof Map<?, ?> dm) {
            @SuppressWarnings("unchecked")
            Map<String, Object> inner = (Map<String, Object>) dm;
            if (body.containsKey("data") && (body.containsKey("status") || body.containsKey("designTaskId"))) {
                return inner;
            }
        }
        return body;
    }

    /** 构造请求实体（real 模式带 JWT Bearer Token）。 */
    private HttpEntity<Void> buildEntity() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        String token = s4Config.getIntegration().getAuthToken();
        if (token != null && !token.isBlank()) {
            headers.setBearerAuth(token);
        }
        return new HttpEntity<>(headers);
    }

    private String join(String base, String path) {
        String b = base == null ? "" : base.replaceAll("/+$", "");
        return b + path;
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
}
