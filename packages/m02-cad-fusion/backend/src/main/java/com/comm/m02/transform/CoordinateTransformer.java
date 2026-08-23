package com.comm.m02.transform;

import org.locationtech.proj4j.*;
import org.locationtech.proj4j.datum.Ellipsoid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

@Component
public class CoordinateTransformer {

    private static final Logger log = LoggerFactory.getLogger(CoordinateTransformer.class);

    private final CRSFactory crsFactory;
    private final Map<String, ProjCoordinate> transformCache;

    public CoordinateTransformer() {
        this.crsFactory = CRSFactory.getInstance();
        this.transformCache = new HashMap<>();
    }

    public TransformResult transform(BigDecimal sourceX, BigDecimal sourceY, BigDecimal sourceZ,
                                     String sourceEpsg, String targetEpsg) {
        return transform(sourceX, sourceY, sourceZ, sourceEpsg, targetEpsg, "AUTO");
    }

    public TransformResult transform(BigDecimal sourceX, BigDecimal sourceY, BigDecimal sourceZ,
                                     String sourceEpsg, String targetEpsg, String transformType) {
        TransformResult result = new TransformResult();

        try {
            CoordinateReferenceSystem sourceCRS = createCRS(sourceEpsg);
            CoordinateReferenceSystem targetCRS = createCRS(targetEpsg);

            if (sourceCRS == null) {
                throw new IllegalArgumentException("无法创建源坐标系: " + sourceEpsg);
            }
            if (targetCRS == null) {
                throw new IllegalArgumentException("无法创建目标坐标系: " + targetEpsg);
            }

            CoordinateTransform transform = CRSTransformFinder.getTransformation(sourceCRS, targetCRS);
            
            ProjCoordinate sourceCoord = new ProjCoordinate(
                    sourceX.doubleValue(), 
                    sourceY.doubleValue(), 
                    sourceZ != null ? sourceZ.doubleValue() : 0
            );
            
            ProjCoordinate targetCoord = new ProjCoordinate();
            
            transform.transform(sourceCoord, targetCoord);

            result.setSourceX(sourceX);
            result.setSourceY(sourceY);
            result.setSourceZ(sourceZ);
            result.setTargetX(BigDecimal.valueOf(targetCoord.x));
            result.setTargetY(BigDecimal.valueOf(targetCoord.y));
            result.setTargetZ(BigDecimal.valueOf(targetCoord.z));
            result.setSourceEpsg(sourceEpsg);
            result.setTargetEpsg(targetEpsg);
            result.setTransformType(transformType);
            result.setAccuracy(0.001);
            result.setSuccess(true);

        } catch (Exception e) {
            log.error("坐标转换失败: {} -> {}", sourceEpsg, targetEpsg, e);
            result.setSuccess(false);
            result.setMessage("坐标转换失败: " + e.getMessage());
        }

        return result;
    }

    private CoordinateReferenceSystem createCRS(String epsg) {
        if (epsg == null || epsg.isEmpty()) {
            epsg = "EPSG:4326";
        }
        if (!epsg.startsWith("EPSG:")) {
            epsg = "EPSG:" + epsg;
        }

        try {
            return crsFactory.createFromName(epsg);
        } catch (Exception e) {
            log.debug("通过名称创建CRS失败: {}, 尝试通过代码创建", epsg);
            try {
                int code = Integer.parseInt(epsg.replace("EPSG:", ""));
                return crsFactory.createFromCode(code);
            } catch (Exception ex) {
                log.error("无法创建坐标系: {}", epsg);
                return null;
            }
        }
    }

    public TransformResult wgs84ToCGCS2000(BigDecimal lon, BigDecimal lat, BigDecimal height) {
        return transform(lon, lat, height, "EPSG:4326", "EPSG:4490", "WGS84_TO_CGCS2000");
    }

    public TransformResult cgcs2000ToWgs84(BigDecimal lon, BigDecimal lat, BigDecimal height) {
        return transform(lon, lat, height, "EPSG:4490", "EPSG:4326", "CGCS2000_TO_WGS84");
    }

    public TransformResult beijing1954ToWgs84(BigDecimal x, BigDecimal y, BigDecimal z) {
        return transform(x, y, z, "EPSG:4214", "EPSG:4326", "BEIJING54_TO_WGS84");
    }

    public TransformResult xiAn1980ToWgs84(BigDecimal x, BigDecimal y, BigDecimal z) {
        return transform(x, y, z, "EPSG:4610", "EPSG:4326", "XIAN80_TO_WGS84");
    }

    public TransformResult toWebMercator(BigDecimal lon, BigDecimal lat) {
        return transform(lon, lat, BigDecimal.ZERO, "EPSG:4326", "EPSG:3857", "WGS84_TO_WEB_MERCATOR");
    }

    public TransformResult fromWebMercator(BigDecimal x, BigDecimal y) {
        return transform(x, y, BigDecimal.ZERO, "EPSG:3857", "EPSG:4326", "WEB_MERCATOR_TO_WGS84");
    }

    @lombok.Data
    public static class TransformResult {
        private BigDecimal sourceX;
        private BigDecimal sourceY;
        private BigDecimal sourceZ;
        private BigDecimal targetX;
        private BigDecimal targetY;
        private BigDecimal targetZ;
        private String sourceEpsg;
        private String targetEpsg;
        private String transformType;
        private Double accuracy;
        private boolean success;
        private String message;
    }
}
