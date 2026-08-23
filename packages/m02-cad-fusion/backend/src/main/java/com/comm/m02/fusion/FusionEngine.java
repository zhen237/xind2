package com.comm.m02.fusion;

import com.comm.m02.entity.GisFeature;
import com.comm.m02.parser.CadEntity;
import com.comm.m02.parser.CadEntityExtractor;
import com.comm.m02.parser.DxfParser;
import com.comm.m02.parser.DwgParser;
import com.comm.m02.transform.CadToGisMapper;
import com.comm.m02.transform.CoordinateTransformer;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.*;
import java.util.stream.Collectors;

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

            DxfParser.ParseResult parseResult = parseFile(config.getSourceFilePath(), config.getFileType());
            if (!parseResult.isSuccess()) {
                result.setSuccess(false);
                result.setMessage("文件解析失败: " + parseResult.getMessage());
                return result;
            }

            log.info("文件解析完成，实体数: {}", parseResult.getEntities().size());

            List<CadEntityExtractor.ExtractionResult> extractionResults = 
                    entityExtractor.extractAll(parseResult.getEntities());
            log.info("实体提取完成，要素数: {}", extractionResults.size());

            List<CadToGisMapper.GisMappingResult> mappingResults = 
                    cadToGisMapper.mapAll(extractionResults);
            log.info("CAD-GIS映射完成，映射数: {}", mappingResults.size());

            List<GisFeature> gisFeatures = new ArrayList<>();
            for (CadToGisMapper.GisMappingResult mappingResult : mappingResults) {
                GisFeature gisFeature = convertToGisFeature(mappingResult, config);
                if (gisFeature != null) {
                    gisFeatures.add(gisFeature);
                }
            }

            result.setGisFeatures(gisFeatures);
            result.setFeatureCount(gisFeatures.size());
            result.setSuccess(true);
            result.setMessage("融合完成，共生成 " + gisFeatures.size() + " 个GIS要素");

            log.info("融合任务完成: 生成要素数={}", gisFeatures.size());

        } catch (Exception e) {
            log.error("融合任务执行失败", e);
            result.setSuccess(false);
            result.setMessage("融合失败: " + e.getMessage());
        }

        return result;
    }

    private DxfParser.ParseResult parseFile(String filePath, String fileType) {
        if (fileType == null || fileType.isEmpty()) {
            fileType = detectFileType(filePath);
        }

        switch (fileType.toLowerCase()) {
            case "dxf":
                return dxfParser.parse(filePath);
            case "dwg":
                return dwgParser.parse(filePath);
            default:
                log.warn("未知的文件类型: {}, 尝试按DXF解析", fileType);
                return dxfParser.parse(filePath);
        }
    }

    private String detectFileType(String filePath) {
        if (filePath == null) return "unknown";
        
        int lastDotIndex = filePath.lastIndexOf(".");
        if (lastDotIndex == -1) return "unknown";
        
        return filePath.substring(lastDotIndex + 1).toLowerCase();
    }

    private GisFeature convertToGisFeature(CadToGisMapper.GisMappingResult mappingResult, 
                                            FusionConfig config) {
        try {
            GisFeature gisFeature = new GisFeature();
            
            gisFeature.setFeatureId(UUID.randomUUID().toString());
            gisFeature.setFeatureType(mappingResult.getTargetFeatureClass());
            gisFeature.setGeometryType(mappingResult.getTargetGeometryType());
            gisFeature.setSourceLayer(mappingResult.getSourceLayerName());
            gisFeature.setTargetLayer(mappingResult.getTargetFeatureClass());

            List<double[]> coords = mappingResult.getCoordinates();
            if (coords != null && !coords.isEmpty()) {
                double[] centerCoord = calculateCenterCoordinate(coords);
                
                if (!"EPSG:4326".equals(config.getSourceEpsg())) {
                    CoordinateTransformer.TransformResult transformResult = 
                            coordinateTransformer.transform(
                                    BigDecimal.valueOf(centerCoord[0]),
                                    BigDecimal.valueOf(centerCoord[1]),
                                    BigDecimal.valueOf(centerCoord[2]),
                                    config.getSourceEpsg(),
                                    config.getTargetEpsg()
                            );
                    
                    if (transformResult.isSuccess()) {
                        gisFeature.setCoordinateX(transformResult.getTargetX());
                        gisFeature.setCoordinateY(transformResult.getTargetY());
                        gisFeature.setCoordinateZ(transformResult.getTargetZ());
                    } else {
                        gisFeature.setCoordinateX(BigDecimal.valueOf(centerCoord[0]));
                        gisFeature.setCoordinateY(BigDecimal.valueOf(centerCoord[1]));
                        gisFeature.setCoordinateZ(BigDecimal.valueOf(centerCoord[2]));
                    }
                } else {
                    gisFeature.setCoordinateX(BigDecimal.valueOf(centerCoord[0]));
                    gisFeature.setCoordinateY(BigDecimal.valueOf(centerCoord[1]));
                    gisFeature.setCoordinateZ(BigDecimal.valueOf(centerCoord[2]));
                }
            }

            Map<String, Object> props = new HashMap<>(mappingResult.getProperties());
            props.put("sourceEpsg", config.getSourceEpsg());
            props.put("targetEpsg", config.getTargetEpsg());
            props.put("transformationType", config.getTransformationType());
            
            gisFeature.setPropertiesJson(objectMapper.writeValueAsString(props));

            return gisFeature;

        } catch (Exception e) {
            log.warn("转换GIS要素失败: sourceId={}, error={}", 
                    mappingResult.getSourceEntityId(), e.getMessage());
            return null;
        }
    }

    private double[] calculateCenterCoordinate(List<double[]> coordinates) {
        if (coordinates.isEmpty()) {
            return new double[]{0, 0, 0};
        }

        double sumX = 0, sumY = 0, sumZ = 0;
        for (double[] coord : coordinates) {
            sumX += coord[0];
            sumY += coord[1];
            sumZ += coord.length > 2 ? coord[2] : 0;
        }

        int count = coordinates.size();
        return new double[]{sumX / count, sumY / count, sumZ / count};
    }

    public String generateGeoJson(FusionResult fusionResult) {
        try {
            Map<String, Object> geoJson = new HashMap<>();
            geoJson.put("type", "FeatureCollection");

            List<Map<String, Object>> features = new ArrayList<>();
            for (GisFeature gisFeature : fusionResult.getGisFeatures()) {
                Map<String, Object> feature = new HashMap<>();
                feature.put("type", "Feature");

                Map<String, Object> geometry = new HashMap<>();
                geometry.put("type", gisFeature.getGeometryType());
                
                List<double[]> coords = Arrays.asList(new double[][]{
                        {gisFeature.getCoordinateX().doubleValue(), 
                         gisFeature.getCoordinateY().doubleValue(), 
                         gisFeature.getCoordinateZ() != null ? gisFeature.getCoordinateZ().doubleValue() : 0}
                });
                geometry.put("coordinates", coords);
                feature.put("geometry", geometry);

                Map<String, Object> properties = objectMapper.readValue(
                        gisFeature.getPropertiesJson(), Map.class);
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

    @lombok.Data
    public static class FusionConfig {
        private String sourceFilePath;
        private String fileType;
        private String sourceEpsg;
        private String targetEpsg;
        private String transformationType;
    }

    @lombok.Data
    public static class FusionResult {
        private boolean success;
        private String message;
        private List<GisFeature> gisFeatures;
        private int featureCount;
    }
}
