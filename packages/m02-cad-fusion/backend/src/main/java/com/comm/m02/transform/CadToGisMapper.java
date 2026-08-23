package com.comm.m02.transform;

import com.comm.m02.parser.CadEntity;
import com.comm.m02.parser.CadEntityExtractor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.*;
import java.util.stream.Collectors;

@Component
public class CadToGisMapper {

    private static final Logger log = LoggerFactory.getLogger(CadToGisMapper.class);

    private static final Map<String, String> ENTITY_TYPE_TO_GEOMETRY = Map.of(
            "LINE", "LineString",
            "LWPOLYLINE", "Polygon",
            "POLYLINE", "LineString",
            "CIRCLE", "Polygon",
            "ARC", "LineString",
            "POINT", "Point",
            "TEXT", "Point",
            "MTEXT", "Point",
            "BLOCK", "GeometryCollection",
            "INSERT", "Point"
    );

    private static final Map<String, String> LAYER_TO_FEATURE_CLASS = Map.of(
            "BUILDING", "building",
            "ROAD", "road",
            "PIPELINE", "pipeline",
            "TREE", "vegetation",
            "WATER", "water",
            "BOUNDARY", "boundary",
            "EQUIPMENT", "equipment",
            "CABLE", "cable",
            "TOWER", "tower"
    );

    public GisMappingResult map(CadEntityExtractor.ExtractionResult extractionResult) {
        GisMappingResult result = new GisMappingResult();

        result.setSourceEntityId(extractionResult.getEntityId());
        result.setSourceEntityType(extractionResult.getEntityType());
        result.setSourceLayerName(extractionResult.getLayerName());

        String geometryType = mapGeometryType(extractionResult.getEntityType());
        result.setTargetGeometryType(geometryType);

        String featureClass = mapFeatureClass(extractionResult.getLayerName());
        result.setTargetFeatureClass(featureClass);

        List<double[]> coordinates = convertCoordinates(extractionResult.getVertices());
        result.setCoordinates(coordinates);

        Map<String, Object> properties = mapProperties(extractionResult);
        result.setProperties(properties);

        result.setMapped(true);
        
        return result;
    }

    public List<GisMappingResult> mapAll(List<CadEntityExtractor.ExtractionResult> extractionResults) {
        List<GisMappingResult> results = new ArrayList<>();
        int mappedCount = 0;
        int skippedCount = 0;

        for (CadEntityExtractor.ExtractionResult extractionResult : extractionResults) {
            try {
                GisMappingResult mappingResult = map(extractionResult);
                results.add(mappingResult);
                mappedCount++;
            } catch (Exception e) {
                log.warn("映射实体失败: id={}, error={}", extractionResult.getEntityId(), e.getMessage());
                skippedCount++;
            }
        }

        log.info("CAD到GIS映射完成: 成功={}, 跳过={}", mappedCount, skippedCount);
        return results;
    }

    private String mapGeometryType(String cadEntityType) {
        return ENTITY_TYPE_TO_GEOMETRY.getOrDefault(cadEntityType.toUpperCase(), "Point");
    }

    private String mapFeatureClass(String layerName) {
        if (layerName == null) return "unknown";
        
        String upperLayerName = layerName.toUpperCase();
        for (Map.Entry<String, String> entry : LAYER_TO_FEATURE_CLASS.entrySet()) {
            if (upperLayerName.contains(entry.getKey())) {
                return entry.getValue();
            }
        }
        return "other";
    }

    private List<double[]> convertCoordinates(List<CadEntity.CadVertex> vertices) {
        List<double[]> coordinates = new ArrayList<>();
        
        if (vertices == null || vertices.isEmpty()) {
            return coordinates;
        }

        for (CadEntity.CadVertex vertex : vertices) {
            double[] coord = {
                    vertex.getX().doubleValue(),
                    vertex.getY().doubleValue(),
                    vertex.getZ() != null ? vertex.getZ().doubleValue() : 0
            };
            coordinates.add(coord);
        }

        return coordinates;
    }

    private Map<String, Object> mapProperties(CadEntityExtractor.ExtractionResult extractionResult) {
        Map<String, Object> properties = new HashMap<>();

        properties.put("sourceEntityId", extractionResult.getEntityId());
        properties.put("sourceEntityType", extractionResult.getEntityType());
        properties.put("sourceLayer", extractionResult.getLayerName());
        properties.put("sourceGeometryType", extractionResult.getGeometryType());

        properties.put("extentMinX", extractionResult.getMinX());
        properties.put("extentMinY", extractionResult.getMinY());
        properties.put("extentMaxX", extractionResult.getMaxX());
        properties.put("extentMaxY", extractionResult.getMaxY());
        properties.put("centerX", extractionResult.getCenterX());
        properties.put("centerY", extractionResult.getCenterY());

        if (extractionResult.getAttributes() != null) {
            for (Map.Entry<String, Object> attr : extractionResult.getAttributes().entrySet()) {
                String key = attr.getKey();
                if (!key.startsWith("code_")) {
                    properties.put("cad_" + key, attr.getValue());
                }
            }
        }

        return properties;
    }

    public GeoJsonFeature toGeoJsonFeature(GisMappingResult mappingResult) {
        GeoJsonFeature feature = new GeoJsonFeature();
        feature.setType("Feature");
        feature.setProperties(mappingResult.getProperties());

        GeoJsonGeometry geometry = new GeoJsonGeometry();
        geometry.setType(mappingResult.getTargetGeometryType());

        Object coordinates = convertToGeoJsonCoordinates(
                mappingResult.getTargetGeometryType(),
                mappingResult.getCoordinates()
        );
        geometry.setCoordinates(coordinates);
        feature.setGeometry(geometry);

        return feature;
    }

    private Object convertToGeoJsonCoordinates(String geometryType, List<double[]> coordinates) {
        switch (geometryType) {
            case "Point":
                return coordinates.isEmpty() ? new double[]{0, 0} : coordinates.get(0);
            case "LineString":
                return coordinates;
            case "Polygon":
                return List.of(coordinates);
            default:
                return coordinates;
        }
    }

    @lombok.Data
    public static class GisMappingResult {
        private String sourceEntityId;
        private String sourceEntityType;
        private String sourceLayerName;
        private String targetGeometryType;
        private String targetFeatureClass;
        private List<double[]> coordinates;
        private Map<String, Object> properties;
        private boolean mapped;
    }

    @lombok.Data
    public static class GeoJsonFeature {
        private String type;
        private GeoJsonGeometry geometry;
        private Map<String, Object> properties;
    }

    @lombok.Data
    public static class GeoJsonGeometry {
        private String type;
        private Object coordinates;
    }
}
