package com.comm.s2.transform;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 坐标转换器单元测试：Web Mercator已知值校验、
 * 中国坐标系回退定义、不支持的坐标系报错。
 */
class CoordinateTransformerTest {

    private CoordinateTransformer transformer;

    @BeforeEach
    void setUp() {
        transformer = new CoordinateTransformer();
    }

    @Test
    void shouldTransformWgs84ToWebMercator() {
        // 北京天安门：116.3913E, 39.9075N
        CoordinateTransformer.TransformResult result = transformer.transform(
                new BigDecimal("116.3913"), new BigDecimal("39.9075"),
                BigDecimal.ZERO, "EPSG:4326", "EPSG:3857");

        assertTrue(result.isSuccess());
        // Web Mercator已知值（R=6378137 球体公式）：x≈12956620.25, y≈4852509.52
        assertEquals(12956620.25, result.getTargetX().doubleValue(), 1.0);
        assertEquals(4852509.52, result.getTargetY().doubleValue(), 1.0);
    }

    @Test
    void shouldTransformWebMercatorBackToWgs84() {
        // 逆变换应回到原经纬度
        CoordinateTransformer.TransformResult result = transformer.transform(
                new BigDecimal("12956620.25"), new BigDecimal("4852509.52"),
                BigDecimal.ZERO, "EPSG:3857", "EPSG:4326");

        assertTrue(result.isSuccess());
        assertEquals(116.3913, result.getTargetX().doubleValue(), 1e-4);
        assertEquals(39.9075, result.getTargetY().doubleValue(), 1e-4);
    }

    @Test
    void shouldTransformBetweenWgs84AndCgcs2000() {
        // WGS84与CGCS2000椭球差异极小（厘米级），经纬度应基本保持不变
        CoordinateTransformer.TransformResult result = transformer.transform(
                new BigDecimal("116.3913"), new BigDecimal("39.9075"),
                BigDecimal.ZERO, "EPSG:4326", "EPSG:4490");

        assertTrue(result.isSuccess());
        assertEquals(116.3913, result.getTargetX().doubleValue(), 1e-6);
        assertEquals(39.9075, result.getTargetY().doubleValue(), 1e-6);
    }

    @Test
    void shouldTransformBeijing54ToWgs84() {
        // 北京54含towgs84七参数，转换应有实际偏移（数十米量级）
        CoordinateTransformer.TransformResult result = transformer.transform(
                new BigDecimal("116.0"), new BigDecimal("39.0"),
                BigDecimal.ZERO, "EPSG:4214", "EPSG:4326");

        assertTrue(result.isSuccess());
        // 全国平均参数精度有限，允许角秒级偏差
        assertEquals(116.0, result.getTargetX().doubleValue(), 0.01);
        assertEquals(39.0, result.getTargetY().doubleValue(), 0.01);
    }

    @Test
    void shouldNormalizeEpsgCode() {
        // "4326"应等价于"EPSG:4326"
        CoordinateTransformer.TransformResult result = transformer.transform(
                new BigDecimal("116.0"), new BigDecimal("39.0"),
                BigDecimal.ZERO, "4326", "4490");

        assertTrue(result.isSuccess());
        assertEquals("EPSG:4326", result.getSourceEpsg());
        assertEquals("EPSG:4490", result.getTargetEpsg());
    }

    @Test
    void shouldFailOnUnsupportedEpsg() {
        CoordinateTransformer.TransformResult result = transformer.transform(
                new BigDecimal("116.0"), new BigDecimal("39.0"),
                BigDecimal.ZERO, "EPSG:9999", "EPSG:4326");

        assertFalse(result.isSuccess());
        assertNotNull(result.getMessage());
    }

    @Test
    void shouldReuseOperationForBatchTransform() {
        CoordinateTransformer.CoordinateOperation operation =
                transformer.createOperation("EPSG:4326", "EPSG:3857");

        assertEquals("EPSG:4326", operation.getSourceEpsg());
        assertEquals("EPSG:3857", operation.getTargetEpsg());

        double[] p1 = operation.transform(116.3913, 39.9075, 0);
        double[] p2 = operation.transform(116.3913, 39.9075, 0);

        assertEquals(p1[0], p2[0], 1e-9);
        assertEquals(12956620.25, p1[0], 1.0);
    }
}
