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
 * S5 施工监管通知服务 — BOM 生成后推送施工指令（闭合 I4 契约）。
 *
 * <p>dataSource 双模式：
 * <ul>
 *   <li>mock — POST dev-proxy（默认 8090）的 /api/s5/verify/tasks，dev-proxy 落库占位</li>
 *   <li>real — POST S5 真实服务地址</li>
 * </ul>
 *
 * <p>推送为旁路通知：失败仅记日志，不阻断 BOM 主流程（S5 可稍后补偿拉取）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class S5NotifyService {

    private final S4Config s4Config;
    private final RestTemplate restTemplate;

    /**
     * [I4] 推送 BOM 施工指令到 S5 施工监管。
     *
     * @param taskId      S4 BOM 任务 ID
     * @param designTaskId 关联设计任务 ID
     * @param projectId    项目 ID
     * @param projectName  项目名称
     * @param stats        物料统计（主设备/辅材/线缆/总条数）
     */
    public void notifyBomGenerated(String taskId, String designTaskId, String projectId,
                                   String projectName, Map<String, Object> stats) {
        String url = join(s4Config.getIntegration().getS5Url(), "/api/s5/verify/tasks");
        try {
            Map<String, Object> body = new HashMap<>();
            body.put("bomTaskId", taskId);
            body.put("designTaskId", designTaskId);
            body.put("projectId", projectId);
            body.put("projectName", projectName == null ? "" : projectName);
            body.put("stats", stats == null ? Map.of() : stats);

            log.info("[S5] notify BOM generated: taskId={} designTaskId={} url={}", taskId, designTaskId, url);
            restTemplate.postForEntity(url, buildEntity(body), Map.class);
        } catch (Exception e) {
            // 旁路通知失败不阻断主流程
            log.warn("[S5] 推送失败（不阻断 BOM 主流程）: taskId={} err={}", taskId, e.getMessage());
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
