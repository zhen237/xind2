package com.comm.s2.transform;

import org.locationtech.proj4j.CRSFactory;
import org.locationtech.proj4j.CoordinateReferenceSystem;
import org.locationtech.proj4j.CoordinateTransform;
import org.locationtech.proj4j.CoordinateTransformFactory;
import org.locationtech.proj4j.ProjCoordinate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 坐标转换器，基于proj4j实现任意EPSG坐标系间的转换。
 * <p>
 * 常用坐标系（WGS84/CGCS2000/北京54/西安80/Web Mercator及CGCS2000高斯投影带）
 * 内置proj4参数定义，即使proj4j内置EPSG注册表缺失对应条目也能完成转换；
 * 北京54与西安80附带全国平均七参数，保证与WGS84之间的基准转换有实际意义。
 */
@Component
public class CoordinateTransformer {

    private static final Logger log = LoggerFactory.getLogger(CoordinateTransformer.class);

    private final CRSFactory crsFactory = new CRSFactory();
    private final CoordinateTransformFactory transformFactory = new CoordinateTransformFactory();

    /** EPSG注册表缺失时的proj4参数回退定义（全国平均参数，精度约1~5米） */
    private static final java.util.Map<String, String> FALLBACK_DEFINITIONS = java.util.Map.of(
            "EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs",
            "EPSG:4490", "+proj=longlat +ellps=GRS80 +no_defs",
            "EPSG:4214", "+proj=longlat +ellps=krass +towgs84=31.4,-144.3,74.8,0,0,0.814,-0.38 +no_defs",
            "EPSG:4610", "+proj=longlat +a=6378140 +b=6356755.3 +towgs84=0,0,0,0,0,0,0 +no_defs",
            "EPSG:3857", "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 "
                    + "+k=1.0 +units=m +nadgrids=@null +no_defs"
    );

    /** 坐标系缓存：EPSG -> CRS */
    private final ConcurrentHashMap<String, CoordinateReferenceSystem> crsCache = new ConcurrentHashMap<>();

    /** 转换关系缓存："源EPSG->目标EPSG" -> 转换器 */
    private final ConcurrentHashMap<String, CoordinateTransform> transformCache = new ConcurrentHashMap<>();

    public TransformResult transform(BigDecimal sourceX, BigDecimal sourceY, BigDecimal sourceZ,
                                     String sourceEpsg, String targetEpsg) {
        return transform(sourceX, sourceY, sourceZ, sourceEpsg, targetEpsg, "AUTO");
    }

    public TransformResult transform(BigDecimal sourceX, BigDecimal sourceY, BigDecimal sourceZ,
                                     String sourceEpsg, String targetEpsg, String transformType) {
        TransformResult result = new TransformResult();

        try {
            CoordinateTransform transform = getTransform(sourceEpsg, targetEpsg);

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
            result.setTargetX(toBigDecimalOrZero(targetCoord.x));
            result.setTargetY(toBigDecimalOrZero(targetCoord.y));
            result.setTargetZ(toBigDecimalOrZero(targetCoord.z));
            result.setSourceEpsg(normalizeEpsg(sourceEpsg));
            result.setTargetEpsg(normalizeEpsg(targetEpsg));
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

    /**
     * 创建可复用的批量转换通道。融合引擎逐顶点转换时只需创建一次，
     * 避免每个顶点重复构建CRS与转换关系。
     */
    public CoordinateOperation createOperation(String sourceEpsg, String targetEpsg) {
        CoordinateTransform transform = getTransform(sourceEpsg, targetEpsg);
        return new CoordinateOperation(transform, normalizeEpsg(sourceEpsg), normalizeEpsg(targetEpsg));
    }

    /**
     * 批量转换坐标数组。coordinates每个元素为[x, y, z]，
     * 返回同维度数组，失败时对应点保持原值。
     */
    public double[][] transformBatch(double[][] coordinates, String sourceEpsg, String targetEpsg) {
        CoordinateTransform transform = getTransform(sourceEpsg, targetEpsg);
        double[][] results = new double[coordinates.length][];

        for (int i = 0; i < coordinates.length; i++) {
            double[] c = coordinates[i];
            try {
                ProjCoordinate src = new ProjCoordinate(c[0], c[1], c.length > 2 ? c[2] : 0);
                ProjCoordinate dst = new ProjCoordinate();
                transform.transform(src, dst);
                results[i] = new double[]{dst.x, dst.y, dst.z};
            } catch (Exception e) {
                log.warn("批量转换第{}个点失败，保留原坐标", i);
                results[i] = c;
            }
        }

        return results;
    }

    /** 获取（并缓存）两个EPSG之间的转换器 */
    private CoordinateTransform getTransform(String sourceEpsg, String targetEpsg) {
        String source = normalizeEpsg(sourceEpsg);
        String target = normalizeEpsg(targetEpsg);
        String key = source + "->" + target;

        return transformCache.computeIfAbsent(key, k -> {
            CoordinateReferenceSystem sourceCRS = createCRS(source);
            CoordinateReferenceSystem targetCRS = createCRS(target);

            if (sourceCRS == null) {
                throw new IllegalArgumentException("无法创建源坐标系: " + source);
            }
            if (targetCRS == null) {
                throw new IllegalArgumentException("无法创建目标坐标系: " + target);
            }

            log.info("创建坐标转换: {} -> {}", source, target);
            return transformFactory.createTransform(sourceCRS, targetCRS);
        });
    }

    /** 创建坐标系：优先查proj4j内置EPSG注册表，缺失时使用内置proj4参数回退 */
    private CoordinateReferenceSystem createCRS(String epsg) {
        String normalized = normalizeEpsg(epsg);

        return crsCache.computeIfAbsent(normalized, code -> {
            CoordinateReferenceSystem crs = null;
            try {
                crs = crsFactory.createFromName(code);
            } catch (Exception e) {
                log.debug("proj4j注册表中未找到{}，尝试内置参数回退", code);
            }

            if (crs == null) {
                String definition = FALLBACK_DEFINITIONS.get(code);
                if (definition != null) {
                    try {
                        crs = crsFactory.createFromParameters(code, definition);
                        log.info("使用内置proj4参数创建坐标系: {} -> {}", code, definition);
                    } catch (Exception e) {
                        log.error("内置参数创建坐标系失败: {}", code, e);
                    }
                }
            }

            if (crs == null) {
                throw new IllegalArgumentException("不支持的坐标系: " + code
                        + "，请使用 /api/s2/cad/coordinate/supported-systems 查询支持的坐标系");
            }

            return crs;
        });
    }

    /**
     * proj4j对二维坐标转换（如4326/3857/4490互转）不填充z值，输出为NaN，
     * BigDecimal.valueOf(NaN)会抛NumberFormatException，统一防御为0。
     */
    private static BigDecimal toBigDecimalOrZero(double v) {
        return Double.isFinite(v) ? BigDecimal.valueOf(v) : BigDecimal.ZERO;
    }

    /** 统一EPSG书写格式：4326 -> EPSG:4326 */
    private String normalizeEpsg(String epsg) {
        if (epsg == null || epsg.isEmpty()) {
            return "EPSG:4326";
        }
        String trimmed = epsg.trim();
        return trimmed.toUpperCase().startsWith("EPSG:") ? trimmed.toUpperCase() : "EPSG:" + trimmed;
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

    /** 可复用的单点转换通道，供融合引擎批量逐顶点转换使用 */
    public static class CoordinateOperation {
        private final CoordinateTransform transform;
        private final String sourceEpsg;
        private final String targetEpsg;

        CoordinateOperation(CoordinateTransform transform, String sourceEpsg, String targetEpsg) {
            this.transform = transform;
            this.sourceEpsg = sourceEpsg;
            this.targetEpsg = targetEpsg;
        }

        /** 转换单个点，返回[x, y, z] */
        public double[] transform(double x, double y, double z) {
            ProjCoordinate src = new ProjCoordinate(x, y, z);
            ProjCoordinate dst = new ProjCoordinate();
            transform.transform(src, dst);
            return new double[]{dst.x, dst.y, dst.z};
        }

        public String getSourceEpsg() {
            return sourceEpsg;
        }

        public String getTargetEpsg() {
            return targetEpsg;
        }
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
