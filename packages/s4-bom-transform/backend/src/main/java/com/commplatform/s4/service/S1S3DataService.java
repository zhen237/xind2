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

    /** [FR-10] 拉取 S1 设计任务详情（含设备清单）。 */
    public Map<String, Object> fetchDesign(String designTaskId) {
        String url = join(s4Config.getIntegration().getS1Url(), "/api/s1/design/tasks/" + designTaskId);
        return get(url, "S1 设计详情");
    }

    /** [FR-10] 拉取 S3 审查结果。 */
    public Map<String, Object> fetchReview(String designTaskId) {
        String url = join(s4Config.getIntegration().getS3Url(), "/api/s3/review/result/" + designTaskId);
        return get(url, "S3 审查结果");
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
            Map<String, Object> review = fetchReview(designTaskId);
            result.put("result", review.get("result"));

            Object violationsObj = review.get("violations");
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
                String severity = String.valueOf(v.get("severity")).toLowerCase();
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
}
