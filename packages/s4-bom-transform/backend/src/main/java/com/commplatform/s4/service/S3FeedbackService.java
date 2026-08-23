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
 * S3 反馈回路服务 — BOM 完成后回灌施工侧信息给 S3 审查模块。
 *
 * <p>闭合 S3 对比分析差距#7：S4 不再单向消费审查结果，而是把施工可行性结论、
 * 已纳入工序的整改核验项、物料替代建议反馈给 S3，形成「审查→施工→反馈→复审」闭环。
 *
 * <p>推送为旁路通知：失败仅记日志，不阻断 BOM 主流程（S3 可稍后补偿拉取）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class S3FeedbackService {

    private final S4Config s4Config;
    private final RestTemplate restTemplate;

    /**
     * BOM 完成后反馈 S3。
     *
     * @param taskId          S4 BOM 任务 ID
     * @param designTaskId    关联设计任务 ID
     * @param gateDecision    闸门判定（allowed / allowed_with_warnings）
     * @param violationCounts 违规分级统计
     * @param rectificationCount 已纳入工序的整改核验项数
     * @param stats           物料统计
     */
    public void feedbackConstructability(String taskId, String designTaskId, String gateDecision,
                                         Map<String, Object> violationCounts, int rectificationCount,
                                         Map<String, Object> stats) {
        String url = join(s4Config.getIntegration().getS3Url(), "/api/s3/review/feedback");
        try {
            Map<String, Object> body = new HashMap<>();
            body.put("designTaskId", designTaskId);
            body.put("bomTaskId", taskId);
            body.put("constructability",
                    "allowed_with_warnings".equals(gateDecision) ? "with_warnings" : "ok");
            body.put("gateDecision", gateDecision == null ? "" : gateDecision);
            body.put("violationCounts", violationCounts == null ? Map.of() : violationCounts);
            body.put("rectificationStepCount", rectificationCount);
            body.put("materialSubstitutions", java.util.List.of()); // 预留：物料替代建议回灌
            body.put("bomStats", stats == null ? Map.of() : stats);

            log.info("[S3-feedback] BOM constructability feedback: taskId={} designTaskId={} url={}",
                    taskId, designTaskId, url);
            restTemplate.postForEntity(url, buildEntity(body), Map.class);
        } catch (Exception e) {
            // 旁路反馈失败不阻断主流程
            log.warn("[S3-feedback] 反馈失败（旁路，不阻断 BOM 主流程）: taskId={} err={}", taskId, e.getMessage());
        }
    }

    // ────────────────────────────────────────

    private HttpEntity<Map<String, Object>> buildEntity(Map<String, Object> body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        String token = s4Config.getIntegration().getAuthToken();
        if (token != null && !token.isBlank()) {
            headers.setBearerAuth(token);
        }
        return new HttpEntity<>(body, headers);
    }

    private String join(String base, String path) {
        String b = base == null ? "" : base.replaceAll("/+$", "");
        return b + path;
    }
}
