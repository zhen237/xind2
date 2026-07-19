package com.comm.m03.design.service;

import com.comm.common.BusinessException;
import com.comm.m03.design.entity.SiteData;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.StringReader;
import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 实测站点 CSV 解析器纯单测(无 Spring / 无 DB 依赖)。
 * 验证: 必填列解析、缺列抛错、空输入返回空列表、isValid 阈值判定。
 */
class MeasuredCsvParserTest {

    private static final String HEADER = "site_id,site_name,longitude,latitude,tower_height,site_type,scenario,rsrp";

    @Test
    void parsesRequiredColumnsAndComputesValidity() throws IOException {
        String csv = HEADER + "\n" +
                "SITE-M001,实测基站1,111.000,35.000,30,macro,urban,-85.3\n" +
                "SITE-M002,实测基站2,111.100,35.100,25,micro,suburban,-130.0\n";

        List<SiteData> sites = DesignService.parseMeasuredCsv(new StringReader(csv));

        assertEquals(2, sites.size());

        SiteData a = sites.get(0);
        assertEquals("SITE-M001", a.getSiteId());
        assertEquals(new BigDecimal("111.000"), a.getLongitude());
        assertEquals(new BigDecimal("35.000"), a.getLatitude());
        assertEquals(new BigDecimal("-85.3"), a.getRsrp());
        assertTrue(a.getIsValid(), "RSRP=-85.3 应判为有效");

        SiteData b = sites.get(1);
        assertEquals(new BigDecimal("-130.0"), b.getRsrp());
        assertEquals(false, b.getIsValid(), "RSRP=-130.0 低于阈值 -120 应判为无效");
    }

    @Test
    void missingRequiredColumnThrows() {
        String csv = "site_id,longitude,rsrp\nSITE-M001,111.0,-85.3\n"; // 缺 latitude
        BusinessException ex = assertThrows(BusinessException.class,
                () -> DesignService.parseMeasuredCsv(new StringReader(csv)));
        assertTrue(ex.getMessage().contains("latitude"), "缺列应明确提示缺失列名");
    }

    @Test
    void emptyInputReturnsEmptyList() throws IOException {
        List<SiteData> sites = DesignService.parseMeasuredCsv(new StringReader(""));
        assertTrue(sites.isEmpty());
    }

    @Test
    void appliesSensibleDefaultsWhenOptionalColumnsAbsent() throws IOException {
        // 仅提供必填三列，其余应回落默认值
        String csv = "longitude,latitude,rsrp\n111.0,35.0,-90.0\n";
        List<SiteData> sites = DesignService.parseMeasuredCsv(new StringReader(csv));
        assertEquals(1, sites.size());
        assertEquals("SITE-M0001", sites.get(0).getSiteId(), "缺 site_id 应自动编号");
        assertEquals("macro", sites.get(0).getSiteType(), "缺 site_type 应回落 macro");
        assertEquals("urban", sites.get(0).getScenario(), "缺 scenario 应回落 urban");
    }
}
