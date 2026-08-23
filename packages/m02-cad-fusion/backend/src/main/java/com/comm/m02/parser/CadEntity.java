package com.comm.m02.parser;

import lombok.Data;
import java.math.BigDecimal;
import java.util.*;

@Data
public class CadEntity {

    private String entityId;
    private String entityType;
    private String layerName;
    private String blockName;
    private BigDecimal minX;
    private BigDecimal minY;
    private BigDecimal minZ;
    private BigDecimal maxX;
    private BigDecimal maxY;
    private BigDecimal maxZ;
    private Map<String, Object> attributes;
    private List<CadVertex> vertices;
    private List<CadEntity> childEntities;

    public CadEntity() {
        this.attributes = new HashMap<>();
        this.vertices = new ArrayList<>();
        this.childEntities = new ArrayList<>();
    }

    @Data
    public static class CadVertex {
        private BigDecimal x;
        private BigDecimal y;
        private BigDecimal z;

        public CadVertex(BigDecimal x, BigDecimal y, BigDecimal z) {
            this.x = x;
            this.y = y;
            this.z = z;
        }

        public CadVertex(double x, double y, double z) {
            this.x = BigDecimal.valueOf(x);
            this.y = BigDecimal.valueOf(y);
            this.z = BigDecimal.valueOf(z);
        }

        public CadVertex(double x, double y) {
            this(x, y, 0);
        }
    }

    public void addVertex(CadVertex vertex) {
        vertices.add(vertex);
        updateBounds(vertex);
    }

    public void addVertex(double x, double y, double z) {
        addVertex(new CadVertex(x, y, z));
    }

    private void updateBounds(CadVertex vertex) {
        if (minX == null || vertex.getX().compareTo(minX) < 0) minX = vertex.getX();
        if (minY == null || vertex.getY().compareTo(minY) < 0) minY = vertex.getY();
        if (minZ == null || vertex.getZ().compareTo(minZ) < 0) minZ = vertex.getZ();
        if (maxX == null || vertex.getX().compareTo(maxX) > 0) maxX = vertex.getX();
        if (maxY == null || vertex.getY().compareTo(maxY) > 0) maxY = vertex.getY();
        if (maxZ == null || vertex.getZ().compareTo(maxZ) > 0) maxZ = vertex.getZ();
    }

    public BigDecimal getCenterX() {
        if (minX == null || maxX == null) return BigDecimal.ZERO;
        return minX.add(maxX).divide(BigDecimal.valueOf(2), 6, java.math.RoundingMode.HALF_UP);
    }

    public BigDecimal getCenterY() {
        if (minY == null || maxY == null) return BigDecimal.ZERO;
        return minY.add(maxY).divide(BigDecimal.valueOf(2), 6, java.math.RoundingMode.HALF_UP);
    }

    public String getGeometryType() {
        if (vertices.isEmpty()) return "POINT";
        if (vertices.size() == 1) return "POINT";
        if (vertices.size() == 2) return "LINESTRING";
        if (vertices.size() > 2 && entityType.equals("LWPOLYLINE")) return "POLYGON";
        return "LINESTRING";
    }
}
