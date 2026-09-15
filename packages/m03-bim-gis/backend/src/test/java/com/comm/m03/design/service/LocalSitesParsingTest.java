package com.comm.m03.design.service;

import com.comm.m03.design.entity.SiteData;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 纯单元测试：从任务本地 GeoJSON 解析站点（无需 Spring 容器、无需数据库）。
 *
 * 背景（真实事故）：S1(m03) 任务加载了 QGIS 导出的 6 个摩洛哥 BTS 站点，
 * 「执行」却生成 61 个六边形网格点，永远无法复现用户的 6 个手工站点。
 * 本测试锁定 parseSitesFromLocalGeoJson 必须原样解析出这 6 个站点（不得生成网格），
 * 并锁定所有站点经度均为负（即位于摩洛哥，而非中国/北京），作为回归护栏。
 */
class LocalSitesParsingTest {

    /** 6 个摩洛哥 BTS 站点：site_id, name, lon, lat；其余属性一致。 */
    private static String buildMoroccoFeatureCollection() {
        Object[][] rows = {
                {"BTS-URBA-006", "URBAN-006", "-8.5359125", "33.2134738"},
                {"BTS-URBA-007", "URBAN-007", "-8.5265861", "33.2134738"},
                {"BTS-URBA-010", "URBAN-010", "-8.5386048", "33.2202306"},
                {"BTS-URBA-011", "URBAN-011", "-8.5292784", "33.2202306"},
                {"BTS-URBA-014", "URBAN-014", "-8.5359125", "33.2269873"},
                {"BTS-URBA-015", "URBAN-015", "-8.5265861", "33.2269873"},
        };
        StringBuilder sb = new StringBuilder();
        sb.append("{\"type\":\"FeatureCollection\",\"features\":[");
        for (int i = 0; i < rows.length; i++) {
            if (i > 0) {
                sb.append(",");
            }
            sb.append("{\"type\":\"Feature\",\"properties\":{")
                    .append("\"site_id\":\"").append(rows[i][0]).append("\",")
                    .append("\"name\":\"").append(rows[i][1]).append("\",")
                    .append("\"tower_height\":35,")
                    .append("\"deviceType\":\"tower\",")
                    .append("\"scenario\":\"URBAN\"},")
                    .append("\"geometry\":{\"type\":\"Point\",\"coordinates\":[")
                    .append(rows[i][2]).append(",").append(rows[i][3]).append("]}}");
        }
        sb.append("]}");
        return sb.toString();
    }

    @Test
    @DisplayName("6 个摩洛哥 Point 站点：原样解析(含属性)，且经度全为负(非中国/北京)")
    void parsesSixMoroccoSitesWithProperties() {
        List<SiteData> sites = DesignService.parseSitesFromLocalGeoJson(buildMoroccoFeatureCollection());

        assertEquals(6, sites.size(), "必须恰好解析出 6 个站点，而非 61 个网格点");

        SiteData first = sites.get(0);
        assertEquals("BTS-URBA-006", first.getSiteId());
        assertEquals("URBAN-006", first.getSiteName());
        // 坐标经 setScale(6, HALF_UP) 舍入，故用 1e-6 容差比较，语义为"与源数据一致"
        assertEquals(-8.5359125, first.getLongitude().doubleValue(), 1e-6, "经度应与源数据一致");
        assertEquals(33.2134738, first.getLatitude().doubleValue(), 1e-6, "纬度应与源数据一致");
        assertEquals(35.0, first.getTowerHeight().doubleValue(), 1e-9, "塔高应为 35");
        assertEquals("tower", first.getSiteType());
        assertEquals("URBAN", first.getScenario());

        // 回归护栏：所有站点经度必须为负 → 位于摩洛哥，绝不可能是北京(116.4)默认落点
        for (SiteData s : sites) {
            assertTrue(s.getLongitude().doubleValue() < 0,
                    "站点经度必须为负(摩洛哥)，实际=" + s.getLongitude() + ", siteId=" + s.getSiteId());
        }
    }

    @Test
    @DisplayName("全部为 Polygon 要素：返回空列表")
    void returnsEmptyWhenAllPolygons() {
        String gj = "{\"type\":\"FeatureCollection\",\"features\":["
                + "{\"type\":\"Feature\",\"properties\":{},\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}},"
                + "{\"type\":\"Feature\",\"properties\":{},\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[2,2],[3,2],[3,3],[2,3],[2,2]]]}}"
                + "]}";
        List<SiteData> sites = DesignService.parseSitesFromLocalGeoJson(gj);
        assertTrue(sites.isEmpty(), "Polygon 要素不应产生站点");
    }

    @Test
    @DisplayName("features 为空数组：返回空列表")
    void returnsEmptyForEmptyFeatures() {
        List<SiteData> sites = DesignService.parseSitesFromLocalGeoJson(
                "{\"type\":\"FeatureCollection\",\"features\":[]}");
        assertTrue(sites.isEmpty());
    }

    @Test
    @DisplayName("非法/空输入：返回空列表且不抛异常")
    void returnsEmptyForInvalidOrBlankInput() {
        assertTrue(DesignService.parseSitesFromLocalGeoJson("not json").isEmpty());
        assertTrue(DesignService.parseSitesFromLocalGeoJson(null).isEmpty());
        assertTrue(DesignService.parseSitesFromLocalGeoJson("").isEmpty());
    }
}
