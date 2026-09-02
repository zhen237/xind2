package com.comm.s2.engine;

import com.comm.s2.common.BusinessException;
import com.comm.s2.entity.GisFeature;
import com.comm.s2.fusion.FusionEngine;
import com.comm.s2.utils.FileUtils;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 方案A 融合引擎（Python 模式）：
 * 与 {@link FusionEngine} 保持相同 {@link FusionEngine.FusionConfig} /
 * {@link FusionEngine.FusionResult} 签名，内部通过 {@link PythonEngineClient}
 * 调用 Python 解析引擎完成「解析 → 分类 → 坐标转换 → CAD+GIS 融合」全链路。
 * <p>
 * 融合语义（与 Python cad_engine/fusion.py 一致）：
 * GIS 既有数据优先 → 同名同位置(&lt;5m)去重 → 属性冲突标记 → 统计冲突清单。
 * GIS 基准数据从配置目录（s2.engine.gis-dir，按图层文件 ftype.geojson）读取，
 * 缺失图层按空基准处理（CAD 要素全部新增）。
 */
@Component
public class PythonFusionEngine {

    private static final Logger log = LoggerFactory.getLogger(PythonFusionEngine.class);

    @Autowired
    private PythonEngineClient pythonEngineClient;

    @Value("${s2.engine.gis-dir:uploads/s2/gis}")
    private String gisDir;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 执行融合任务（Python 引擎）。
     *
     * @param config 融合配置（与 Java 引擎同构）
     * @return 融合结果（GisFeature 列表 + 统计）
     */
    public FusionEngine.FusionResult fuse(FusionEngine.FusionConfig config) {
        FusionEngine.FusionResult result = new FusionEngine.FusionResult();
        List<GisFeature> allFeatures = new ArrayList<>();

        try {
            // 0. 健康检查（可选失败提示）
            if (!pythonEngineClient.health()) {
                throw new BusinessException(503, "Python 解析引擎不可达，请确认已启动 "
                        + "(engine 目录执行: python -m cad_engine.server)");
            }

            // 1. 读取 CAD 文件并调用 parse
            String sourceFilePath = config.getSourceFilePath();
            if (sourceFilePath == null || !FileUtils.fileExists(sourceFilePath)) {
                throw new BusinessException(400, "CAD 文件不存在: " + sourceFilePath);
            }
            String fileName = java.nio.file.Paths.get(sourceFilePath).getFileName().toString();
            byte[] dxfBytes = FileUtils.readFileAsBytes(sourceFilePath);
            String sourceEpsg = config.getSourceEpsg() != null ? config.getSourceEpsg() : "cgcs2000_gk111";
            String targetEpsg = config.getTargetEpsg() != null ? config.getTargetEpsg() : "EPSG:4326";

            JsonNode parseResp = pythonEngineClient.parse(dxfBytes, fileName, sourceEpsg, targetEpsg);
            JsonNode layers = parseResp.path("layers");
            JsonNode classifyStats = parseResp.path("classify_stats");
            log.info("Python 解析完成: classify={}", classifyStats);

            // 2. 逐图层融合：CAD 要素（该图层）+ GIS 基准（gis-dir/{ftype}.geojson）
            double dedupTolM = config.getDedupTolM() != null ? config.getDedupTolM() : 5.0;
            int entityCount = 0;
            Iterator<Map.Entry<String, JsonNode>> layerIter = layers.fields();
            while (layerIter.hasNext()) {
                Map.Entry<String, JsonNode> entry = layerIter.next();
                String ftype = entry.getKey();
                JsonNode layerInfo = entry.getValue();
                JsonNode cadLayer = layerInfo.path("geojson");
                if (!cadLayer.isObject() || cadLayer.path("features").size() == 0) {
                    continue;
                }
                entityCount += cadLayer.path("features").size();

                // CAD 要素补充 ftype 标记（Python 侧 properties 无此字段）
                ObjectNode cadFc = (ObjectNode) cadLayer.deepCopy();
                ArrayNode cadFeatures = (ArrayNode) cadFc.path("features");
                for (JsonNode feat : cadFeatures) {
                    ((ObjectNode) feat.path("properties")).put("ftype", ftype);
                }

                // GIS 基准（按图层文件，可缺省）
                ObjectNode gisFc = objectMapper.createObjectNode()
                        .put("type", "FeatureCollection")
                        .set("features", objectMapper.createArrayNode());
                String gisFile = gisDir + "/" + ftype + ".geojson";
                if (FileUtils.fileExists(gisFile)) {
                    JsonNode gisRoot = objectMapper.readTree(FileUtils.readFileAsString(gisFile));
                    if (gisRoot.path("features").isArray()) {
                        gisFc.set("features", gisRoot.path("features"));
                    }
                    log.info("图层[{}] 使用 GIS 基准: {}（{} 要素）", ftype, gisFile,
                            gisFc.path("features").size());
                }

                // 调用 Python fuse
                JsonNode merged = pythonEngineClient.fuse(cadFc, gisFc, dedupTolM);
                allFeatures.addAll(parseMergedFeatures(merged, ftype));
            }

            result.setGisFeatures(allFeatures);
            result.setFeatureCount(allFeatures.size());
            result.setEntityCount(entityCount);
            result.setTransformedCount(allFeatures.size());
            result.setSuccess(true);
            result.setMessage("融合完成（Python引擎）：解析实体 " + entityCount
                    + " 个，生成GIS要素 " + allFeatures.size() + " 个（"
                    + sourceEpsg + " → " + targetEpsg + "）");
            log.info("Python 融合任务完成: 要素数={}", allFeatures.size());

        } catch (BusinessException e) {
            log.warn("Python 融合失败: {}", e.getMessage());
            result.setSuccess(false);
            result.setMessage(e.getMessage());
        } catch (Exception e) {
            log.error("Python 融合任务执行失败", e);
            result.setSuccess(false);
            result.setMessage("融合失败: " + e.getMessage());
        }
        return result;
    }

    /** 解析 Python 融合结果的 features 为 GisFeature 列表 */
    private List<GisFeature> parseMergedFeatures(JsonNode mergedFc, String ftype) {
        List<GisFeature> features = new ArrayList<>();
        if (mergedFc == null || !mergedFc.path("features").isArray()) {
            return features;
        }
        for (JsonNode feature : mergedFc.path("features")) {
            JsonNode props = feature.path("properties");
            GisFeature gisFeature = new GisFeature();
            // 要素 ID 优先取 CAD 句柄 / GIS 标识，缺省生成
            String handle = props.path("cad_handle").asText("");
            String gisId = props.path("gis_id").asText("");
            gisFeature.setFeatureId(!handle.isBlank() ? handle
                    : (!gisId.isBlank() ? gisId : UUID.randomUUID().toString()));
            gisFeature.setFeatureType(ftype);
            gisFeature.setTargetLayer(ftype);

            JsonNode geometry = feature.path("geometry");
            gisFeature.setGeometryType(geometry.path("type").asText("Point"));
            gisFeature.setGeometryJson(geometry.toString());

            // 中心点：取几何首点
            double[] center = firstCoordinate(geometry);
            gisFeature.setCoordinateX(BigDecimal.valueOf(center[0]));
            gisFeature.setCoordinateY(BigDecimal.valueOf(center[1]));
            gisFeature.setCoordinateZ(BigDecimal.ZERO);

            ObjectNode enriched = ((ObjectNode) props).deepCopy();
            enriched.put("ftype", ftype);
            enriched.put("vertexCount", countVertices(geometry));
            gisFeature.setPropertiesJson(enriched.toString());
            gisFeature.setSourceLayer(enriched.path("cad_layer").asText(""));

            features.add(gisFeature);
        }
        return features;
    }

    /** 取几何首坐标（Point / LineString / Polygon 统一处理） */
    private double[] firstCoordinate(JsonNode geometry) {
        JsonNode coords = geometry.path("coordinates");
        if (coords.isArray() && coords.size() > 0) {
            JsonNode first = coords.get(0);
            if (first.isArray()) {
                JsonNode leaf = first.get(0);
                if (leaf.isArray()) {
                    // Polygon: 环 → 点
                    return new double[]{leaf.get(0).asDouble(), leaf.get(1).asDouble()};
                }
                return new double[]{first.get(0).asDouble(), first.get(1).asDouble()};
            }
            return new double[]{coords.get(0).asDouble(), coords.get(1).asDouble()};
        }
        return new double[]{0, 0};
    }

    /** 统计几何顶点数 */
    private int countVertices(JsonNode geometry) {
        int[] counter = {0};
        countVerticesRecursive(geometry.path("coordinates"), counter);
        return counter[0];
    }

    private void countVerticesRecursive(JsonNode node, int[] counter) {
        if (node == null || node.isMissingNode()) {
            return;
        }
        if (node.isArray() && node.size() > 0 && node.get(0).isNumber()) {
            counter[0]++;
            return;
        }
        if (node.isArray()) {
            for (JsonNode child : node) {
                countVerticesRecursive(child, counter);
            }
        }
    }
}
