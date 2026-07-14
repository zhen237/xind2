package com.comm.m03.design.client;

import com.comm.m03.design.entity.GenerateRequest;
import com.comm.m03.design.entity.TopologyGenerateResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Python 拓扑规划引擎客户端（规格 §3.1：M03 后端 → HTTP 调拓扑引擎）
 *
 * 主路径：M03 负责参数校验与编排，生成算法下沉到 Python 拓扑引擎，
 * 避免 Java / QGIS / Python 三方重复实现同一套 hex/RSRP/设备拓扑逻辑。
 * 拓扑引擎不可达时返回 null，由 DesignService 回退本地算法。
 */
@Component
public class TopologyEngineClient {

    private static final Logger log = LoggerFactory.getLogger(TopologyEngineClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public TopologyEngineClient(
            @Value("${topology.engine.url:http://localhost:9001}") String baseUrl,
            @Value("${topology.engine.timeout-ms:5000}") int timeoutMs) {
        this.baseUrl = baseUrl;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(timeoutMs);
        factory.setReadTimeout(timeoutMs);
        this.restTemplate = new RestTemplate(factory);
    }

    /**
     * 调用 Python 拓扑引擎 /generate 生成设计方案
     * @return 引擎响应；引擎不可达/超时/5xx 时返回 null（触发本地回退）
     */
    public TopologyGenerateResponse generate(GenerateRequest request) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(buildPayload(request), headers);

            TopologyGenerateResponse response = restTemplate.postForObject(
                    baseUrl + "/generate", entity, TopologyGenerateResponse.class);
            log.info("拓扑引擎生成成功: url={}, projectId={}", baseUrl, request.getProjectId());
            return response;
        } catch (HttpStatusCodeException e) {
            log.warn("拓扑引擎返回错误状态码 {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            return null;
        } catch (Exception e) {
            log.warn("拓扑引擎调用失败, 将回退本地算法: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 健康检查
     */
    public boolean isHealthy() {
        try {
            HttpStatus status = restTemplate.getForEntity(baseUrl + "/health", Map.class).getStatusCode();
            return status.is2xxSuccessful();
        } catch (Exception e) {
            log.debug("拓扑引擎健康检查失败: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 构造与 Python GenerateRequest 对齐的 snake_case 请求体
     */
    private Map<String, Object> buildPayload(GenerateRequest request) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("project_id", request.getProjectId());
        payload.put("scheme_name", request.getSchemeName());
        if (request.getTemplateType() != null) {
            payload.put("template_type", request.getTemplateType());
        }
        payload.put("center_longitude", request.getCenterLongitude().doubleValue());
        payload.put("center_latitude", request.getCenterLatitude().doubleValue());
        payload.put("coverage_radius", request.getCoverageRadius().doubleValue());
        payload.put("frequency_band", request.getFrequencyBand());
        if (request.getTowerHeight() != null) {
            payload.put("tower_height", request.getTowerHeight().doubleValue());
        }
        if (request.getGridSize() != null) {
            payload.put("grid_size", request.getGridSize());
        }
        if (request.getAntennaHeight() != null) {
            payload.put("antenna_height", request.getAntennaHeight());
        }
        if (request.getSectorCount() != null) {
            payload.put("sector_count", request.getSectorCount());
        }
        if (request.getScenario() != null) {
            payload.put("scenario", request.getScenario());
        }
        return payload;
    }
}
