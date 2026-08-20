package com.commplatform.s4.service;

import com.commplatform.s4.config.S4Config;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
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
     * [FR-10] 审查闸门 — 设计是否已审查通过。
     *
     * @return true=允许生成；false=未通过（应拦截）
     */
    public boolean isApproved(String designTaskId) {
        try {
            Map<String, Object> review = fetchReview(designTaskId);
            Object result = review.get("result");
            if ("approved".equalsIgnoreCase(String.valueOf(result))) {
                return true;
            }
            log.warn("[S3] 审查未通过，拦截 BOM 生成: designTaskId={} result={}", designTaskId, result);
            return false;
        } catch (Exception e) {
            // 审查服务不可达 → 降级放行 + 告警（联调期保证主链路可用）
            log.warn("[S3] 审查服务不可达，降级放行: designTaskId={} err={}", designTaskId, e.getMessage());
            return true;
        }
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
