package com.comm.s2.fusion;

import com.comm.s2.entity.GisFeature;
import com.comm.s2.parser.CadEntity;
import com.comm.s2.parser.CadEntityExtractor;
import com.comm.s2.parser.DxfParser;
import com.comm.s2.parser.DwgParser;
import com.comm.s2.transform.CadToGisMapper;
import com.comm.s2.transform.CoordinateTransformer;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.*;

/**
 * CAD-GIS融合引擎。
 * <p>
 * 完整融合流水线：CAD文件解析 → 实体提取 → CAD-GIS语义映射 →
 * 逐顶点坐标转换（源EPSG → 目标EPSG）→ GeoJSON要素生成。
 * <p>
 * 每个GIS要素保留完整几何（全部顶点坐标，存储于geometry_json），
 * 中心点坐标单独存入coordinate_x/y/z列以便检索与地图定位。
 */
@Component
public class FusionEngine {

    private static final Logger log = LoggerFactory.getLogger(FusionEngine.class);

    private final DxfParser dxfParser;
    private final DwgParser dwgParser;
    private final CadEntityExtractor entityExtractor;
    private final CoordinateTransformer coordinateTransformer;
    private final CadToGisMapper cadToGisMapper;
    private final ObjectMapper objectMapper;

    public FusionEngine(DxfParser dxfParser,
                        DwgParser dwgParser,
                        CadEntityExtractor entityExtractor,
                        CoordinateTransformer coordinateTransformer,
                        CadToGisMapper cadToGisMapper) {
        this.dxfParser = dxfParser;
        this.dwgParser = dwgParser;
        this.entityExtractor = entityExtractor;
        this.coordinateTransformer = coordinateTransformer;
        this.cadToGisMapper = cadToGisMapper;
        this.objectMapper = new ObjectMapper();
    }

    public FusionResult fuse(FusionConfig config) {
        FusionResult result = new FusionResult();

        try {
            log.info("开始执行融合任务: sourceFile={}, sourceEpsg={}, targetEpsg={}",
                    config.getSourceFilePath(), config.getSourceEpsg(), config.getTargetEpsg());

            // 1. 解析CAD文件
            DxfParser.ParseResult parseResult = parseFile(config.getSourceFilePath(), config.getFileType());
            if (!parseResult.isSuccess()) {
                result.setSuccess(false);
                result.setMessage("文件解析失败: " + parseResult.getMessage());
                return result;
            }
            if (parseResult.getEntities().isEmpty()) {
                result.setSuccess(false);
                result.setMessage("文件解析成功但未提取到任何实体，请确认DXF文件包含ENTITIES段");
                return result;
            }
            log.info("文件解析完成，实体数: {}", parseResult.getEntities().size());

            // 2. 实体提取与CAD-GIS语义映射
            List<CadEntityExtractor.ExtractionResult> extractionResults =
                    entityExtractor.extractAll(parseResult.getEntities());
            List<CadToGisMapper.GisMappingResult> mappingResults =
                    cadToGisMapper.mapAll(extractionResults);
            log.info("CAD-GIS映射完成，映射数: {}", mappingResults.size());

            // 3. 创建坐标转换通道（一次创建，逐顶点复用）
            String sourceEpsg = config.getSourceEpsg() != null ? config.getSourceEpsg() : "EPSG:4326";
            String targetEpsg = config.getTargetEpsg() != null ? config.getTargetEpsg() : "EPSG:4326";
            boolean needTransform = !normalize(sourceEpsg).equals(normalize(targetEpsg));
            CoordinateTransformer.CoordinateOperation operation = null;
            if (needTransform) {
                // 不支持的坐标系在此抛出异常，整体任务失败并提示原因
                operation = coordinateTransformer.createOperation(sourceEpsg, targetEpsg);
                log.info("坐标转换通道就绪: {} -> {}", sourceEpsg, targetEpsg);
            }

            // 4. 逐要素转换坐标并生成GIS要素
            List<GisFeature> gisFeatures = new ArrayList<>();
            int transformedCount = 0;
            for (CadToGisMapper.GisMappingResult mappingResult : mappingResults) {
                GisFeature gisFeature = convertToGisFeature(mappingResult, config,
                        operation, needTransform);
                if (gisFeature != null) {
                    gisFeatures.add(gisFeature);
                    if (needTransform) {
                        transformedCount++;
                    }
                }
            }

            result.setGisFeatures(gisFeatures);
            result.setFeatureCount(gisFeatures.size());
            result.setSuccess(true);
            result.setEntityCount(parseResult.getEntities().size());
            result.setTransformedCount(transformedCount);
            result.setMessage("融合完成：解析实体 " + parseResult.getEntities().size()
                    + " 个，生成GIS要素 " + gisFeatures.size() + " 个"
                    + (needTransform ? "，坐标转换 " + transformedCount + " 个要素（" + sourceEpsg
                        + " → " + targetEpsg + "）" : ""));

            log.info("融合任务完成: 生成要素数={}", gisFeatures.size());

        } catch (Exception e) {
            log.error("融合任务执行失败", e);
            result.setSuccess(false);
            result.setMessage("融合失败: " + e.getMessage());
        }

        return result;
    }

    /** 根据文件类型选择解析器，未指明时按扩展名判断 */
    private DxfParser.ParseResult parseFile(String filePath, String fileType) {
        if (fileType == null || fileType.isEmpty()) {
            fileType = detectFileType(filePath);
        }

        switch (fileType.toLowerCase(Locale.ROOT)) {
            case "dwg":
                return dwgParser.parse(filePath);
            case "dxf":
                return dxfParser.parse(filePath);
            default:
                log.warn("未知的文件类型: {}, 尝试按DXF解析", fileType);
                return dxfParser.parse(filePath);
        }
    }

    private String detectFileType(String filePath) {
        if (filePath == null) return "unknown";
        int lastDotIndex = filePath.lastIndexOf('.');
        if (lastDotIndex == -1) return "unknown";
        return filePath.substring(lastDotIndex + 1).toLowerCase(Locale.ROOT);
    }

    /**
     * 将映射结果转换为GIS要素：
     * 全部顶点做坐标转换，生成完整GeoJSON几何；中心点写入坐标列。
     */
    private GisFeature convertToGisFeature(CadToGisMapper.GisMappingResult mappingResult,
                                            FusionConfig config,
                                            CoordinateTransformer.CoordinateOperation operation,
                                            boolean needTransform) {
        try {
            List<double[]> coordinates = mappingResult.getCoordinates();
            if (coordinates == null || coordinates.isEmpty()) {
                return null;
            }

            // 逐顶点坐标转换
            List<double[]> finalCoords = new ArrayList<>(coordinates.size());
            if (needTransform && operation != null) {
                for (double[] c : coordinates) {
                    double[] t = operation.transform(c[0], c[1], c.length > 2 ? c[2] : 0);
                    finalCoords.add(t);
                }
            } else {
                finalCoords.addAll(coordinates);
            }

            // GeoJSON几何（完整顶点）
            String geometryType = mappingResult.getTargetGeometryType();
            String geometryJson = buildGeometryJson(geometryType, finalCoords);

            GisFeature gisFeature = new GisFeature();
            gisFeature.setFeatureId(UUID.randomUUID().toString());
            gisFeature.setFeatureType(mappingResult.getTargetFeatureClass());
            gisFeature.setGeometryType(geometryType);
            gisFeature.setSourceLayer(mappingResult.getSourceLayerName());
            gisFeature.setTargetLayer(mappingResult.getTargetFeatureClass());
            gisFeature.setGeometryJson(geometryJson);

            // 中心点坐标（便于数据库检索与地图定位）
            double[] center = calculateCenterCoordinate(finalCoords);
            gisFeature.setCoordinateX(BigDecimal.valueOf(center[0]));
            gisFeature.setCoordinateY(BigDecimal.valueOf(center[1]));
            gisFeature.setCoordinateZ(BigDecimal.valueOf(center[2]));

            Map<String, Object> props = new LinkedHashMap<>(mappingResult.getProperties());
            props.put("sourceEpsg", config.getSourceEpsg());
            props.put("targetEpsg", config.getTargetEpsg());
            props.put("transformationType", config.getTransformationType());
            props.put("vertexCount", finalCoords.size());

            gisFeature.setPropertiesJson(objectMapper.writeValueAsString(props));

            return gisFeature;

        } catch (Exception e) {
            log.warn("转换GIS要素失败: sourceId={}, error={}",
                    mappingResult.getSourceEntityId(), e.getMessage());
            return null;
        }
    }

    /** 按GeoJSON规范构建几何JSON：Point -> [x,y]；LineString -> 顶点序列；Polygon -> 单环 */
    private String buildGeometryJson(String geometryType, List<double[]> coordinates) throws Exception {
        Map<String, Object> geometry = new LinkedHashMap<>();
        geometry.put("type", geometryType);

        switch (geometryType) {
            case "Point":
                double[] p = coordinates.get(0);
                geometry.put("coordinates", Arrays.asList(round(p[0]), round(p[1])));
                break;
            case "Polygon":
                geometry.put("coordinates", List.of(toPositionList(coordinates)));
                break;
            case "LineString":
            default:
                geometry.put("coordinates", toPositionList(coordinates));
                break;
        }

        return objectMapper.writeValueAsString(geometry);
    }

    private List<List<Double>> toPositionList(List<double[]> coordinates) {
        List<List<Double>> positions = new ArrayList<>(coordinates.size());
        for (double[] c : coordinates) {
            positions.add(Arrays.asList(round(c[0]), round(c[1])));
        }
        return positions;
    }

    /** 保留6位小数，消除浮点噪声 */
    private double round(double value) {
        return Math.round(value * 1_000_000.0) / 1_000_000.0;
    }

    private double[] calculateCenterCoordinate(List<double[]> coordinates) {
        double sumX = 0, sumY = 0, sumZ = 0;
        for (double[] coord : coordinates) {
            sumX += coord[0];
            sumY += coord[1];
            sumZ += coord.length > 2 ? coord[2] : 0;
        }
        int count = coordinates.size();
        return new double[]{sumX / count, sumY / count, sumZ / count};
    }

    /** 生成融合结果的GeoJSON FeatureCollection（含完整几何） */
    public String generateGeoJson(FusionResult fusionResult) {
        try {
            Map<String, Object> geoJson = new LinkedHashMap<>();
            geoJson.put("type", "FeatureCollection");

            List<Map<String, Object>> features = new ArrayList<>();
            for (GisFeature gisFeature : fusionResult.getGisFeatures()) {
                Map<String, Object> feature = new LinkedHashMap<>();
                feature.put("type", "Feature");
                feature.put("id", gisFeature.getFeatureId());

                // 完整几何来自geometry_json；为空时回退到中心点
                if (gisFeature.getGeometryJson() != null) {
                    feature.put("geometry", objectMapper.readValue(gisFeature.getGeometryJson(), Map.class));
                } else {
                    Map<String, Object> geometry = new LinkedHashMap<>();
                    geometry.put("type", "Point");
                    geometry.put("coordinates", Arrays.asList(
                            gisFeature.getCoordinateX().doubleValue(),
                            gisFeature.getCoordinateY().doubleValue()));
                    feature.put("geometry", geometry);
                }

                Map<String, Object> properties = new LinkedHashMap<>();
                if (gisFeature.getPropertiesJson() != null) {
                    properties = objectMapper.readValue(gisFeature.getPropertiesJson(), Map.class);
                }
                properties.putIfAbsent("featureType", gisFeature.getFeatureType());
                properties.putIfAbsent("sourceLayer", gisFeature.getSourceLayer());
                feature.put("properties", properties);

                features.add(feature);
            }

            geoJson.put("features", features);
            geoJson.put("totalFeatures", fusionResult.getFeatureCount());

            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(geoJson);

        } catch (Exception e) {
            log.error("生成GeoJson失败", e);
            return "{}";
        }
    }

    private String normalize(String epsg) {
        String trimmed = epsg == null ? "EPSG:4326" : epsg.trim();
        String upper = trimmed.toUpperCase(Locale.ROOT);
        return upper.startsWith("EPSG:") ? upper : "EPSG:" + upper;
    }

    @lombok.Data
    public static class FusionConfig {
        private String sourceFilePath;
        private String fileType;
        private String sourceEpsg;
        private String targetEpsg;
        private String transformationType;
        /** 同名同位置去重容差（米），默认 5.0 */
        private Double dedupTolM;
    }

    @lombok.Data
    public static class FusionResult {
        private boolean success;
        private String message;
        private List<GisFeature> gisFeatures;
        private int featureCount;
        /** 解析出的CAD实体总数 */
        private int entityCount;
        /** 完成坐标转换的要素数 */
        private int transformedCount;
    }
}
