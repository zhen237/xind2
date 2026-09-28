package com.comm.m03.design.client;

import com.comm.m03.design.entity.GenerateRequest;
import com.comm.m03.design.entity.TopologyGenerateResponse;
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
 * Python 拓扑规划引擎客户端（规格 §3.1：M03 后端 → HTTP 调拓扑引擎）
 *
 * 主路径：M03 负责参数校验与编排，生成算法下沉到 Python 拓扑引擎，
 * 避免 Java / QGIS / Python 三方重复实现同一套 hex/RSRP/设备拓扑逻辑。
 *
 * <p>失败契约（区分两类，避免静默回退掩盖真实 bug）：</p>
 * <ul>
 *   <li>引擎返回 4xx/5xx：请求体或引擎逻辑本身有问题，抛 {@link TopologyEngineException}，
 *       <b>禁止</b>回退本地算法。</li>
 *   <li>引擎不可达/超时/反序列化失败：返回 {@code null}，允许由 DesignService 回退本地算法
 *       并标记"降级"。</li>
 * </ul>
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
     * 调用 Python 拓扑引擎 /generate 生成设计方案。
     *
     * @param request 生成请求
     * @return 引擎响应；引擎不可达/超时/反序列化失败时返回 null（允许调用方回退本地算法并标记降级）
     * @throws TopologyEngineException 引擎返回 4xx/5xx（请求体或引擎逻辑本身有问题，禁止静默回退）
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
            // 引擎明确报错(4xx/5xx)：请求体或引擎逻辑本身有问题，
            // 继续回退等于用本地伪造成果掩盖真实 bug，故抛出而非返回 null。
            throw new TopologyEngineException(
                    "拓扑引擎返回 HTTP " + e.getStatusCode().value() + "：" + e.getResponseBodyAsString(), e);
        } catch (Exception e) {
            // 连接失败/超时/反序列化：引擎不可达，允许回退（由调用方标记降级，不再静默）。
            log.warn("拓扑引擎调用失败, 将回退本地算法: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 健康检查
     */
    public boolean isHealthy() {
        try {
            HttpStatusCode status = restTemplate.getForEntity(baseUrl + "/health", Map.class).getStatusCode();
            return status.is2xxSuccessful();
        } catch (Exception e) {
            log.debug("拓扑引擎健康检查失败: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 构造与 Python GenerateRequest 对齐的 snake_case 请求体。
     *
     * <p>仅有 project_id 可无条件下发（其必然有值）；其余字段一律判空后 put，
     * 避免下发 {@code "frequency_band": null} 之类显式 null 覆盖引擎 Pydantic 默认值
     * （曾导致引擎 {@code freq_map.get(frequency_band.lower())} 抛
     * {@code AttributeError: 'NoneType' object has no attribute 'lower'} → HTTP 500）。</p>
     */
    // 包级私有以便单元测试
    Map<String, Object> buildPayload(GenerateRequest request) {
        Map<String, Object> payload = new LinkedHashMap<>();
        // project_id 必然有值，可无条件下发；其余字段一律判空。
        payload.put("project_id", request.getProjectId());
        if (request.getSchemeName() != null && !request.getSchemeName().isBlank()) {
            payload.put("scheme_name", request.getSchemeName());
        }
        if (request.getTemplateType() != null) {
            payload.put("template_type", request.getTemplateType());
        }
        if (request.getCenterLongitude() != null) {
            payload.put("center_longitude", request.getCenterLongitude().doubleValue());
        }
        if (request.getCenterLatitude() != null) {
            payload.put("center_latitude", request.getCenterLatitude().doubleValue());
        }
        if (request.getCoverageRadius() != null) {
            payload.put("coverage_radius", request.getCoverageRadius().doubleValue());
        }
        // frequency_band：非 null 才下发；显式 null 会覆盖引擎默认值并触发引擎侧 500。
        if (request.getFrequencyBand() != null) {
            payload.put("frequency_band", request.getFrequencyBand());
        }
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
