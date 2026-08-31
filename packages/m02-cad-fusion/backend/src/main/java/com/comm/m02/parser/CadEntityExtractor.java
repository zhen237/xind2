package com.comm.m02.parser;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;

@Component
public class CadEntityExtractor {

    private static final Logger log = LoggerFactory.getLogger(CadEntityExtractor.class);

    public ExtractionResult extract(CadEntity entity) {
        ExtractionResult result = new ExtractionResult();
        
        result.setEntityId(entity.getEntityId());
        result.setEntityType(entity.getEntityType());
        result.setLayerName(entity.getLayerName());
        result.setGeometryType(entity.getGeometryType());
        
        if (entity.getVertices() != null && !entity.getVertices().isEmpty()) {
            result.setVertices(entity.getVertices());
            calculateBounds(entity, result);
        }
        
        result.setAttributes(entity.getAttributes());

        // 文本标注（TEXT/MTEXT）提升为label属性，融合后在GIS中可作为要素名展示
        if (entity.getText() != null && !entity.getText().isEmpty()) {
            result.getAttributes().put("label", entity.getText());
        }

        return result;
    }

    public List<ExtractionResult> extractAll(List<CadEntity> entities) {
        List<ExtractionResult> results = new ArrayList<>();
        Map<String, List<CadEntity>> groupedByLayer = new HashMap<>();
        
        for (CadEntity entity : entities) {
            String layer = entity.getLayerName() != null ? entity.getLayerName() : "DEFAULT";
            groupedByLayer.computeIfAbsent(layer, k -> new ArrayList<>()).add(entity);
        }
        
        for (Map.Entry<String, List<CadEntity>> entry : groupedByLayer.entrySet()) {
            String layerName = entry.getKey();
            List<CadEntity> layerEntities = entry.getValue();
            
            log.info("处理图层: {}, 实体数: {}", layerName, layerEntities.size());
            
            for (CadEntity entity : layerEntities) {
                ExtractionResult extractionResult = extract(entity);
                extractionResult.setLayerName(layerName);
                results.add(extractionResult);
            }
        }
        
        return results;
    }

    private void calculateBounds(CadEntity entity, ExtractionResult result) {
        List<CadEntity.CadVertex> vertices = entity.getVertices();
        if (vertices.isEmpty()) return;
        
        double minX = Double.MAX_VALUE, minY = Double.MAX_VALUE, minZ = Double.MAX_VALUE;
        double maxX = -Double.MAX_VALUE, maxY = -Double.MAX_VALUE, maxZ = -Double.MAX_VALUE;
        
        for (CadEntity.CadVertex vertex : vertices) {
            double x = vertex.getX().doubleValue();
            double y = vertex.getY().doubleValue();
            double z = vertex.getZ().doubleValue();
            
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            minZ = Math.min(minZ, z);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
            maxZ = Math.max(maxZ, z);
        }
        
        result.setMinX(minX);
        result.setMinY(minY);
        result.setMinZ(minZ);
        result.setMaxX(maxX);
        result.setMaxY(maxY);
        result.setMaxZ(maxZ);
        result.setCenterX((minX + maxX) / 2);
        result.setCenterY((minY + maxY) / 2);
        result.setCenterZ((minZ + maxZ) / 2);
    }

    @lombok.Data
    public static class ExtractionResult {
        private String entityId;
        private String entityType;
        private String layerName;
        private String geometryType;
        private List<CadEntity.CadVertex> vertices;
        private Map<String, Object> attributes;
        private double minX, minY, minZ;
        private double maxX, maxY, maxZ;
        private double centerX, centerY, centerZ;
    }
}
