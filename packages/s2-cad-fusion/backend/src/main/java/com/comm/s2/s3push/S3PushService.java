package com.comm.s2.s3push;

import com.comm.s2.dto.response.FusionResultResponse;
import com.comm.s2.entity.FusionTask;
import com.comm.s2.mapper.FusionTaskMapper;
import com.comm.s2.service.CadFusionService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * S2 → S3 智能审查联动。
 * <p>
 * 依据团队《S3接口联调契约》：S3 接收设计数据的白名单接口为
 * {@code POST /api/v1/s3/review/s1/receive}（免 token，异步触发审查并返回 reviewTaskId）。
 * 本服务将 S2 融合结果（GeoJSON 要素）映射为契约的 {@code devices[]} 结构推送：
 * <ul>
 *   <li>designTaskId / designTaskName —— 融合任务标识</li>
 *   <li>designType —— 融合产物类型</li>
 *   <li>devices[] —— 每个 GIS 要素映射为一个设备（deviceId/deviceName/deviceType/
 *       coordinates/params 透传融合属性与冲突标记）</li>
 *   <li>extraData —— 完整 GeoJSON + 冲突清单，供 S3 扩展使用</li>
 * </ul>
 * 推送地址在 application.yml 中配置（s2.s3.push-url），未部署时可通过
 * s2.s3.enabled=false 关闭（默认关闭，避免服务启动即报错）。
 */
@Service
public class S3PushService {

    private static final Logger log = LoggerFactory.getLogger(S3PushService.class);

    @Autowired
    private CadFusionService fusionService;

    @Autowired
    private FusionTaskMapper fusionTaskMapper;

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${s2.s3.push-url:http://localhost:8089/api/v1/s3/review/s1/receive}")
    private String pushUrl;

    @Value("${s2.s3.enabled:false}")
    private boolean enabled;

    /**
     * 推送指定融合任务的结果到 S3 审查服务。
     *
     * @param taskId 融合任务 ID
     * @return 推送结果（success / message / pushTime / taskId / conflictCount / reviewTaskId / response）
     */
    public Map<String, Object> pushFusionResult(Long taskId) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("taskId", taskId);
        result.put("pushTime", LocalDateTime.now().toString());
        result.put("enabled", enabled);

        if (!enabled) {
            result.put("success", false);
            result.put("message", "S3推送未启用（application.yml 中 s2.s3.enabled=false）");
            return result;
        }

        try {
            // 1. 校验任务状态
            FusionResultResponse task = fusionService.getFusionTask(taskId);
            if (task == null) {
                result.put("success", false);
                result.put("message", "融合任务不存在: " + taskId);
                return result;
            }
            if (!"COMPLETED".equals(task.getStatus())) {
                result.put("success", false);
                result.put("message", "融合任务未完成，当前状态: " + task.getStatus());
                return result;
            }

            // 2. 取融合结果 GeoJSON，解析要素并映射为 S3 契约 devices[]
            FusionTask taskEntity = fusionTaskMapper.selectById(taskId);
            String geoJson = fusionService.getFusionResultGeoJson(taskId);
            JsonNode root = objectMapper.readTree(geoJson);

            ObjectNode payload = objectMapper.createObjectNode();
            payload.put("designTaskId", "S2-FUSE-" + taskId);
            payload.put("designTaskName", task.getTaskName());
            payload.put("designType", "fused_cad_gis");

            // devices[]：融合要素 → S3 设备字段
            ArrayNode devices = objectMapper.createArrayNode();
            ArrayNode conflicts = objectMapper.createArrayNode();
            JsonNode features = root.path("features");
            if (features.isArray()) {
                for (JsonNode feature : features) {
                    ObjectNode device = toDevice(feature);
                    devices.add(device);

                    // 冲突清单
                    JsonNode props = feature.path("properties");
                    String action = props.path("fusion_action").asText("");
                    String conflict = props.path("fusion_conflict").asText("");
                    if ("conflict".equalsIgnoreCase(conflict)
                            || conflict.contains("审核")
                            || "conflict_review".equalsIgnoreCase(action)) {
                        ObjectNode c = objectMapper.createObjectNode();
                        c.put("featureId", props.path("cad_handle").asText(props.path("gis_id").asText("")));
                        c.put("label", props.path("label").asText(props.path("name").asText("未命名")));
                        c.put("layer", props.path("cad_layer").asText(""));
                        c.put("fusionAction", action);
                        c.put("conflict", conflict);
                        c.put("conflictFields", props.path("conflict_fields").asText(""));
                        conflicts.add(c);
                    }
                }
            }
            payload.set("devices", devices);

            // extraData：完整 GeoJSON + 冲突清单 + 坐标系（供 S3 扩展/复核）
            ObjectNode extraData = objectMapper.createObjectNode();
            extraData.set("geojson", root);
            extraData.set("conflicts", conflicts);
            extraData.put("sourceEpsg", taskEntity != null ? taskEntity.getSourceEpsg() : null);
            extraData.put("targetEpsg", taskEntity != null ? taskEntity.getTargetEpsg() : null);
            extraData.put("module", "s2-cad-fusion");
            payload.set("extraData", extraData);

            result.put("conflictCount", conflicts.size());
            result.put("deviceCount", devices.size());

            // 3. HTTP 推送（S3 契约：免 token）
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<String> entity = new HttpEntity<>(payload.toString(), headers);
            ResponseEntity<String> resp = restTemplate.postForEntity(pushUrl, entity, String.class);

            result.put("success", resp.getStatusCode().is2xxSuccessful());
            result.put("httpStatus", resp.getStatusCode().value());
            result.put("message", "已推送至 S3 审查服务");

            // 解析响应中的 reviewTaskId / status（契约 1.4）
            if (resp.getBody() != null && !resp.getBody().isBlank()) {
                try {
                    JsonNode respJson = objectMapper.readTree(resp.getBody());
                    JsonNode data = respJson.path("data");
                    if (!data.isMissingNode()) {
                        if (data.hasNonNull("reviewTaskId")) {
                            result.put("reviewTaskId", data.get("reviewTaskId").asLong());
                        }
                        if (data.hasNonNull("status")) {
                            result.put("reviewStatus", data.get("status").asText());
                        }
                    }
                } catch (Exception ignored) {
                    // 响应非 JSON 时忽略，保留原文
                }
                result.put("response", resp.getBody().substring(0, Math.min(resp.getBody().length(), 500)));
            }
            log.info("S2→S3 推送成功: taskId={}, status={}, devices={}, conflicts={}",
                    taskId, resp.getStatusCode().value(), devices.size(), conflicts.size());

        } catch (RestClientException e) {
            log.warn("S2→S3 推送失败(网络): taskId={}, url={}, err={}", taskId, pushUrl, e.getMessage());
            result.put("success", false);
            result.put("message", "S3 服务不可达: " + e.getMessage() + " (url=" + pushUrl + ")");
        } catch (Exception e) {
            log.error("S2→S3 推送失败: taskId={}", taskId, e);
            result.put("success", false);
            result.put("message", "推送异常: " + e.getMessage());
        }
        return result;
    }

    /** 融合要素 → S3 契约 devices[] 元素（缺省字段不填，S3 自动 pending） */
    private ObjectNode toDevice(JsonNode feature) {
        JsonNode props = feature.path("properties");
        JsonNode geometry = feature.path("geometry");

        ObjectNode device = objectMapper.createObjectNode();
        device.put("deviceId", firstNonBlank(
                props.path("cad_handle").asText(""),
                props.path("gis_id").asText(""),
                feature.path("id").asText(""),
                "DEV-" + System.nanoTime()));
        device.put("deviceName", firstNonBlank(
                props.path("label").asText(""),
                props.path("name").asText(""),
                "融合要素"));
        device.put("deviceType", mapDeviceType(props.path("ftype").asText(
                props.path("feature_type").asText("equipment"))));

        // coordinates：几何首点 → "[lon,lat,0]"
        JsonNode coord = firstCoordinate(geometry);
        if (coord != null) {
            device.put("coordinates", coord.toString());
        }

        // params：透传融合属性与冲突标记
        ObjectNode params = objectMapper.createObjectNode();
        props.fields().forEachRemaining(e -> {
            String key = e.getKey();
            if ("sourceEpsg".equals(key) || "targetEpsg".equals(key)) {
                return;
            }
            JsonNode v = e.getValue();
            if (v.isTextual()) {
                params.put(key, v.asText());
            } else if (v.isNumber()) {
                params.put(key, v.asDouble());
            } else if (v.isBoolean()) {
                params.put(key, v.asBoolean());
            } else if (v.isArray() || v.isObject()) {
                params.set(key, v);
            }
        });
        device.set("params", params);
        return device;
    }

    /** 融合要素类型 → S3 deviceType（S3 契约允许扩展类型） */
    private String mapDeviceType(String ftype) {
        if (ftype == null || ftype.isBlank()) {
            return "equipment";
        }
        switch (ftype) {
            case "building_outline": return "building";
            case "road_centerline": return "road";
            case "power_line": return "power_cable";
            case "well_point": return "pipe";
            case "contour": return "terrain";
            case "redline": return "boundary";
            default: return "equipment";
        }
    }

    /** 几何首坐标：Point/LineString/Polygon 统一取第一点 */
    private JsonNode firstCoordinate(JsonNode geometry) {
        JsonNode coords = geometry.path("coordinates");
        if (!coords.isArray() || coords.size() == 0) {
            return null;
        }
        JsonNode first = coords.get(0);
        if (first.isArray() && first.size() > 0 && first.get(0).isArray()) {
            // Polygon 环 → 取环内第一点
            JsonNode p = first.get(0);
            return objectMapper.createArrayNode()
                    .add(p.get(0).asDouble()).add(p.get(1).asDouble()).add(0);
        }
        if (first.isArray() && first.size() >= 2) {
            return objectMapper.createArrayNode()
                    .add(first.get(0).asDouble()).add(first.get(1).asDouble()).add(0);
        }
        return null;
    }

    private String firstNonBlank(String... candidates) {
        for (String s : candidates) {
            if (s != null && !s.isBlank()) {
                return s;
            }
        }
        return "";
    }
}
