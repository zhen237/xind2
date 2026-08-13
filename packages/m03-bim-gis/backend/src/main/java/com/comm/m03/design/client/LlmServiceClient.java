package com.comm.m03.design.client;

import com.comm.m03.design.entity.LlmParseRequest;
import com.comm.m03.design.entity.LlmParseResponse;
import com.comm.m03.design.entity.LlmReportRequest;
import com.comm.m03.design.entity.LlmReportResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * m03-llm-service 客户端（落地路线 §3.1：M03 后端 → HTTP 调 LLM 微服务）
 *
 * 密钥边界：LLM API Key 只存在于同机 llm-service 的环境变量中，本客户端仅做内部
 * HTTP 调用（localhost:9002）。前端/插件经 JWT 网关调用本后端的 /api/m03/llm/**，
 * 永不直接持有 LLM Key（吸取安全审查密钥教训）。
 * LLM 服务不可达/超时/5xx 时返回 null，由 Controller 降级为 503 提示。
 */
@Component
public class LlmServiceClient {

    private static final Logger log = LoggerFactory.getLogger(LlmServiceClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public LlmServiceClient(
            @Value("${llm.service.url:http://localhost:9002}") String baseUrl,
            @Value("${llm.service.timeout-ms:60000}") int timeoutMs) {
        this.baseUrl = baseUrl;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(timeoutMs);
        factory.setReadTimeout(timeoutMs);
        this.restTemplate = new RestTemplate(factory);
    }

    public LlmParseResponse parseDesignParams(LlmParseRequest request) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(buildParsePayload(request), headers);
            LlmParseResponse response = restTemplate.postForObject(
                    baseUrl + "/parse-design-params", entity, LlmParseResponse.class);
            log.info("LLM 解析设计参数成功: url={}", baseUrl);
            return response;
        } catch (HttpStatusCodeException e) {
            log.warn("LLM 服务返回错误状态码 {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            return null;
        } catch (Exception e) {
            log.warn("LLM 服务调用失败: {}", e.getMessage());
            return null;
        }
    }

    public LlmReportResponse generateReport(LlmReportRequest request) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(buildReportPayload(request), headers);
            LlmReportResponse response = restTemplate.postForObject(
                    baseUrl + "/generate-report", entity, LlmReportResponse.class);
            log.info("LLM 生成报告成功: url={}", baseUrl);
            return response;
        } catch (HttpStatusCodeException e) {
            log.warn("LLM 服务返回错误状态码 {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            return null;
        } catch (Exception e) {
            log.warn("LLM 服务调用失败: {}", e.getMessage());
            return null;
        }
    }

    public boolean isHealthy() {
        try {
            HttpStatusCode status = restTemplate.getForEntity(baseUrl + "/health", Map.class).getStatusCode();
            return status.is2xxSuccessful();
        } catch (Exception e) {
            log.debug("LLM 服务健康检查失败: {}", e.getMessage());
            return false;
        }
    }

    private Map<String, Object> buildParsePayload(LlmParseRequest request) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("text", request.getText());
        if (request.getContext() != null) {
            payload.put("context", request.getContext());
        }
        return payload;
    }

    private Map<String, Object> buildReportPayload(LlmReportRequest request) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("scheme", request.getScheme());
        if (request.getContext() != null) {
            payload.put("context", request.getContext());
        }
        return payload;
    }
}
