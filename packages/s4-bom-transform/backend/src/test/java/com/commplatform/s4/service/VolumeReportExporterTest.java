package com.commplatform.s4.service;

import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;

import java.io.ByteArrayInputStream;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * [S4-S1-迁移 2026-09-22] VolumeReportExporter 单测。
 * <p>验证 4 sheet 都存在且包含"概算/示意"标注。</p>
 */
@DisplayName("VolumeReportExporter 工程量报表 Excel")
class VolumeReportExporterTest {

    private final CostEstimationService costSvc = new CostEstimationService();
    private final VolumeReportExporter exporter = new VolumeReportExporter(costSvc);

    @Test
    @DisplayName("生成 4 sheet 工作簿：物料/设备/管线/造价")
    void fourSheetsPresent() throws Exception {
        Map<String, Object> design = new LinkedHashMap<>();
        design.put("devices", List.of(
                Map.of("deviceName", "AAU", "deviceType", "aau", "qty", 3, "azimuth", 30.0, "downtilt", 6.0, "parentDevice", "S-1")
        ));
        design.put("pipelines", List.of(
                Map.of("pipelineId", "P-001", "startSite", "S-1", "endSite", "S-2",
                        "pipelineType", "直埋", "fiberType", "G.652D", "lengthM", 120.0)
        ));
        design.put("projectName", "测试工程");

        List<Map<String, Object>> bomItems = List.of(
                Map.of("siteId", "S-1", "installMethod", "塔上",
                        "materialName", "RRU", "spec", "RRU-01", "qty", 3, "unit", "台")
        );

        ResponseEntity<byte[]> resp = exporter.export("T-1", bomItems, design);
        assertNotNull(resp);
        assertTrue(resp.getBody().length > 0);

        try (XSSFWorkbook wb = new XSSFWorkbook(new ByteArrayInputStream(resp.getBody()))) {
            assertEquals(4, wb.getNumberOfSheets());
            assertEquals("BOM物料清单", wb.getSheetName(0));
            assertEquals("设备清单",   wb.getSheetName(1));
            assertEquals("管线明细",   wb.getSheetName(2));
            assertEquals("造价估算汇总", wb.getSheetName(3));

            // 造价 sheet 必须含"概算/示意"
            String costText = wb.getSheet("造价估算汇总").getRow(0).getCell(0).getStringCellValue();
            assertTrue(costText.contains("概算"));
            assertTrue(costText.contains("示意"));
        }
    }

    @Test
    @DisplayName("空 pipelines 仍能生成报表（造价为 0）")
    void emptyPipelines() throws Exception {
        Map<String, Object> design = new LinkedHashMap<>();
        design.put("devices", Collections.emptyList());
        design.put("pipelines", Collections.emptyList());
        ResponseEntity<byte[]> resp = exporter.export("T-2", Collections.emptyList(), design);
        assertNotNull(resp);
        try (XSSFWorkbook wb = new XSSFWorkbook(new ByteArrayInputStream(resp.getBody()))) {
            assertEquals(4, wb.getNumberOfSheets());
        }
    }

    @Test
    @DisplayName("null pipelines / devices 不抛异常")
    void nulls() throws Exception {
        Map<String, Object> design = new LinkedHashMap<>();
        // 不放 pipelines 字段
        design.put("devices", null);
        ResponseEntity<byte[]> resp = exporter.export("T-3", null, design);
        assertNotNull(resp);
        assertTrue(resp.getBody().length > 0);
    }
}