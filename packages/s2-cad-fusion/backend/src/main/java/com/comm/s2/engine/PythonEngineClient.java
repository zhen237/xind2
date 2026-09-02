package com.comm.s2.engine;

import com.comm.s2.common.BusinessException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.io.IOException;

/**
 * 方案A：Java 后端 → Python 解析引擎（HTTP 进程间调用）的客户端。
 * <p>
 * 对应 Python 侧 cad_engine/server.py（默认 8092 端口）：
 * <pre>
 *   GET  /api/engine/health    健康检查
 *   POST /api/engine/parse     解析 DXF（multipart 上传）→ 每类要素 GeoJSON
 *   POST /api/engine/transform GeoJSON 坐标系转换
 *   POST /api/engine/fuse      CAD+GIS 融合
 * </pre>
 * 引擎地址在 application.yml 中配置（s2.engine.base-url）。
 * 所有调用返回 JsonNode 原始结构，由上层（PythonFusionEngine）解释。
 */
@Component
public class PythonEngineClient {

    private static final Logger log = LoggerFactory.getLogger(PythonEngineClient.class);

    private final ObjectMapper objectMapper = new ObjectMapper();
    private RestTemplate restTemplate;

    @Value("${s2.engine.base-url:http://localhost:8092}")
    private String baseUrl;

    @Value("${s2.engine.connect-timeout-ms:3000}")
    private int connectTimeoutMs;

    @Value("${s2.engine.read-timeout-ms:300000}")
    private int readTimeoutMs;

    @jakarta.annotation.PostConstruct
    public void init() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        this.restTemplate = new RestTemplate(factory);
    }

    /** 健康检查：引擎是否可达 */
    public boolean health() {
        try {
            ResponseEntity<JsonNode> resp = restTemplate.getForEntity(baseUrl + "/api/engine/health",
                    JsonNode.class);
            return resp.getStatusCode().is2xxSuccessful();
        } catch (RestClientException e) {
            log.warn("Python 引擎健康检查失败: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 解析 DXF：multipart 上传文件，返回包含每类要素 GeoJSON 的响应。
     * 响应结构：{ doc_info, classify_stats, layers: { ftype: { feature_count, geojson } } }
     *
     * @param dxfBytes   DXF 文件字节
     * @param fileName   文件名（含扩展名，决定类型）
     * @param source     源坐标系（如 cgcs2000_gk111）
     * @param target     目标坐标系（如 EPSG:4326）
     */
    public JsonNode parse(byte[] dxfBytes, String fileName, String source, String target) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(dxfBytes) {
            @Override
            public String getFilename() {
                return fileName;
            }
        });
        body.add("source", source == null ? "cgcs2000_gk111" : source);
        body.add("target", target == null ? "EPSG:4326" : target);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);

        return post("/api/engine/parse", request);
    }

    /**
     * 坐标系转换：GeoJSON FeatureCollection → 目标坐标系。
     *
     * @param geojson    待转换的 FeatureCollection
     * @param source     源坐标系
     * @param target     目标坐标系
     * @param sevenParam 七参数（可选，JSON 对象）
     * @param fourParam  四参数（可选，JSON 对象）
     */
    public JsonNode transform(JsonNode geojson, String source, String target,
                              JsonNode sevenParam, JsonNode fourParam) {
        ObjectNode body = objectMapper.createObjectNode();
        body.set("geojson", geojson);
        body.put("source", source == null ? "cgcs2000_gk111" : source);
        body.put("target", target == null ? "EPSG:4326" : target);
        if (sevenParam != null) {
            body.set("seven_param", sevenParam);
        }
        if (fourParam != null) {
            body.set("four_param", fourParam);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<String> request = new HttpEntity<>(body.toString(), headers);

        return post("/api/engine/transform", request);
    }

    /**
     * CAD + GIS 融合：执行去重/冲突标记规则，返回融合后的 FeatureCollection。
     *
     * @param cadFc     CAD 要素 FeatureCollection
     * @param gisFc     GIS 基准 FeatureCollection（可为空）
     * @param dedupTolM 同名同位置去重容差（米）
     */
    public JsonNode fuse(JsonNode cadFc, JsonNode gisFc, double dedupTolM) {
        ObjectNode body = objectMapper.createObjectNode();
        body.set("cad", cadFc);
        body.set("gis", gisFc == null || gisFc.isNull()
                ? objectMapper.createObjectNode()
                        .put("type", "FeatureCollection")
                        .set("features", objectMapper.createArrayNode())
                : gisFc);
        body.put("dedup_tol_m", dedupTolM);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<String> request = new HttpEntity<>(body.toString(), headers);

        return post("/api/engine/fuse", request);
    }

    /** 通用 POST：发送请求并解析 JSON 响应，非 2xx 或不可达时抛出业务异常 */
    private JsonNode post(String path, HttpEntity<?> request) {
        String url = baseUrl + path;
        try {
            ResponseEntity<String> resp = restTemplate.exchange(url, HttpMethod.POST, request, String.class);
            if (!resp.getStatusCode().is2xxSuccessful()) {
                throw new BusinessException(502,
                        "Python 引擎调用失败(" + resp.getStatusCode().value() + "): " + url
                                + (resp.getBody() == null ? "" : " - " + truncate(resp.getBody())));
            }
            if (resp.getBody() == null || resp.getBody().isBlank()) {
                throw new BusinessException(502, "Python 引擎返回空响应: " + url);
            }
            return objectMapper.readTree(resp.getBody());
        } catch (RestClientException e) {
            log.error("Python 引擎不可达: url={}, err={}", url, e.getMessage());
            throw new BusinessException(503, "Python 解析引擎不可达: " + e.getMessage() + " (url=" + url + ")");
        } catch (IOException e) {
            log.error("Python 引擎响应解析失败: url={}", url, e);
            throw new BusinessException(502, "Python 引擎响应解析失败: " + e.getMessage());
        }
    }

    private String truncate(String s) {
        return s.length() <= 300 ? s : s.substring(0, 300) + "...";
    }
}
