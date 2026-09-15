package com.comm.m03.design.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 纯单元测试：从任务本地 GeoJSON 推导设计中心（无需 Spring 容器、无需数据库）。
 *
 * 背景（真实事故 2026-09-15）：任务 paramsJson 缺 centerLongitude/centerLatitude 时，
 * 旧逻辑静默回退到北京默认中心(116.4074/39.9042)，伪造出 61 个北京落点。
 * 本测试锁定 deriveCenterAndRadiusFromGeoJson 必须从真实 Point 数据推导中心，
 * 且绝不能得到北京默认值。
 */
class LocalDataCenterDerivationTest {

    /** 生产任务本地数据中的 6 个真实站点坐标（摩洛哥）。 */
    private static final double[][] MOROCCO_SITES = {
            {-8.5359125, 33.2134738},
            {-8.5265861, 33.2134738},
            {-8.5386048, 33.2202306},
            {-8.5292784, 33.2202306},
            {-8.5359125, 33.2269873},
            {-8.5265861, 33.2269873},
    };

    private static final BigDecimal BEIJING_DEFAULT_LON = BigDecimal.valueOf(116.4074);
    private static final BigDecimal BEIJING_DEFAULT_LAT = BigDecimal.valueOf(39.9042);

    private static String buildMoroccoFeatureCollection() {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"type\":\"FeatureCollection\",\"features\":[");
        for (int i = 0; i < MOROCCO_SITES.length; i++) {
            if (i > 0) {
                sb.append(",");
            }
            sb.append("{\"type\":\"Feature\",\"properties\":{},\"geometry\":{")
                    .append("\"type\":\"Point\",\"coordinates\":[")
                    .append(MOROCCO_SITES[i][0]).append(",").append(MOROCCO_SITES[i][1])
                    .append("]}}");
        }
        sb.append("]}");
        return sb.toString();
    }

    @Test
    @DisplayName("6 个摩洛哥站点：推导中心落在摩洛哥范围，而非北京默认值")
    void derivesCenterInMoroccoNotBeijing() {
        BigDecimal[] derived = DesignService.deriveCenterAndRadiusFromGeoJson(buildMoroccoFeatureCollection());

        assertNotNull(derived, "有效 Point 要素必须推导出中心");
        BigDecimal lon = derived[0];
        BigDecimal lat = derived[1];

        assertTrue(lon.compareTo(BigDecimal.valueOf(-8.55)) > 0
                        && lon.compareTo(BigDecimal.valueOf(-8.51)) < 0,
                "中心经度应落在摩洛哥范围 (-8.55, -8.51)，实际=" + lon);
        assertTrue(lat.compareTo(BigDecimal.valueOf(33.20)) > 0
                        && lat.compareTo(BigDecimal.valueOf(33.24)) < 0,
                "中心纬度应落在摩洛哥范围 (33.20, 33.24)，实际=" + lat);

        // 明确断言：绝不等于旧的北京默认中心
        assertTrue(lon.compareTo(BEIJING_DEFAULT_LON) != 0,
                "中心经度绝不能等于北京默认 116.4074，实际=" + lon);
        assertTrue(lat.compareTo(BEIJING_DEFAULT_LAT) != 0,
                "中心纬度绝不能等于北京默认 39.9042，实际=" + lat);
    }

    @Test
    @DisplayName("紧凑站点簇：覆盖半径 > 0 且 < 5000 米")
    void derivesReasonableCoverageRadius() {
        BigDecimal[] derived = DesignService.deriveCenterAndRadiusFromGeoJson(buildMoroccoFeatureCollection());

        assertNotNull(derived, "有效 Point 要素必须推导出覆盖半径");
        BigDecimal radius = derived[2];
        assertTrue(radius.compareTo(BigDecimal.ZERO) > 0, "覆盖半径必须 > 0，实际=" + radius);
        assertTrue(radius.compareTo(BigDecimal.valueOf(5000)) < 0,
                "紧凑簇覆盖半径应 < 5000 米，实际=" + radius);
    }

    @Test
    @DisplayName("无 Point 要素：返回 null")
    void returnsNullForNoPointFeatures() {
        BigDecimal[] derived = DesignService.deriveCenterAndRadiusFromGeoJson(
                "{\"type\":\"FeatureCollection\",\"features\":[]}");
        assertNull(derived, "空 FeatureCollection 必须返回 null");
    }

    @Test
    @DisplayName("非法 JSON：返回 null 且不抛异常")
    void returnsNullForMalformedJsonWithoutThrowing() {
        BigDecimal[] derived = DesignService.deriveCenterAndRadiusFromGeoJson("not json");
        assertNull(derived, "非法 JSON 必须返回 null 而非抛异常");
    }
}
