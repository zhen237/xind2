package com.comm.m03.s3.client;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

/**
 * S3 智能审查模块调用客户端。
 *
 * 对接契约：
 * - POST /api/v1/s3/review/s1/receive  接收 S1 设计数据，立即返回 reviewTaskId（白名单免 token）
 * - GET  /api/v1/s3/review/task/{id}  查询审查任务状态与统计
 *
 * 调用失败时返回 null 并记 warn，不阻塞 S1 设计任务主流程（与拓扑引擎失败回退策略一致）。
 */
@Component
public class S3ReviewClient {

    private static final Logger log = LoggerFactory.getLogger(S3ReviewClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;
    private final boolean enabled;

    public S3ReviewClient(
            @Value("${s3.review.url:http://localhost:8089}") String baseUrl,
            @Value("${s3.review.timeout-ms:10000}") int timeoutMs,
            @Value("${s3.review.enabled:true}") boolean enabled) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.enabled = enabled;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(timeoutMs);
        factory.setReadTimeout(timeoutMs);
        this.restTemplate = new RestTemplate(factory);
    }

    public boolean isEnabled() {
        return enabled;
    }

    /**
     * 推送设计数据到 S3，返回审查任务 ID；失败返回 null。
     */
    public S3ReviewReceiveResponse submitReview(S3ReviewReceiveRequest request) {
        if (!enabled) {
            log.debug("S3 审查推送已关闭，跳过: designTaskId={}", request.getDesignTaskId());
            return null;
        }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<S3ReviewReceiveRequest> entity = new HttpEntity<>(request, headers);

            S3ReviewReceiveResponse response = restTemplate.postForObject(
                    baseUrl + "/api/v1/s3/review/s1/receive", entity, S3ReviewReceiveResponse.class);
            log.info("S3 审查推送成功: designTaskId={}, reviewTaskId={}, status={}",
                    request.getDesignTaskId(),
                    response != null ? response.getReviewTaskId() : null,
                    response != null ? response.getStatus() : null);
            return response;
        } catch (HttpStatusCodeException e) {
            log.warn("S3 审查推送返回错误: designTaskId={}, status={}, body={}",
                    request.getDesignTaskId(), e.getStatusCode(), e.getResponseBodyAsString());
            return null;
        } catch (Exception e) {
            log.warn("S3 审查推送失败: designTaskId={}, err={}", request.getDesignTaskId(), e.getMessage());
            return null;
        }
    }

    /**
     * 轮询 S3 审查任务状态；失败返回 null。
     */
    public S3ReviewTaskResponse getTaskStatus(Long reviewTaskId) {
        if (!enabled || reviewTaskId == null) {
            return null;
        }
        try {
            return restTemplate.getForObject(
                    baseUrl + "/api/v1/s3/review/task/{id}",
                    S3ReviewTaskResponse.class,
                    reviewTaskId);
        } catch (Exception e) {
            log.warn("S3 审查状态查询失败: reviewTaskId={}, err={}", reviewTaskId, e.getMessage());
            return null;
        }
    }
}
