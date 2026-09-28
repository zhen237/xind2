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

    /**
     * [§九·补 2026-09-22] 设备清单明细口径：每台设备一行，包含所属站点 / 方位角 / 下倾角 3 列
     * （之前按聚合口径被压成 ~15 行汇总，这 3 列全空——与 QGIS 原导出口径不一致）。
     * <p>本测试验证 Excel 「设备清单」sheet 的 5 列（所属站点/设备名称/设备类型/方位角/下倾角）
     * 都被正确写入并保留原始数值。</p>
     */
    @Test
    @DisplayName("设备清单 sheet 写入所属站点/方位角/下倾角（§九·补 逐设备明细口径）")
    void deviceSheetDetailFields() throws Exception {
        Map<String, Object> design = new LinkedHashMap<>();
        // 明细：2 台不同方位的 AAU，各自携带 parentDevice/azimuth/downtilt
        design.put("devices", List.of(
                Map.of("deviceName", "AAU-01", "deviceType", "aau",
                        "modelSpec", "AAU-64T64R", "qty", 1,
                        "parentDevice", "S-1", "azimuth", 30.0, "downtilt", 6.0),
                Map.of("deviceName", "AAU-02", "deviceType", "aau",
                        "modelSpec", "AAU-64T64R", "qty", 1,
                        "parentDevice", "S-1", "azimuth", 150.0, "downtilt", 4.0),
                Map.of("deviceName", "RRU-01", "deviceType", "rru",
                        "modelSpec", "RRU-5254", "qty", 1,
                        "parentDevice", "S-1", "azimuth", 90.0, "downtilt", 0.0)
        ));
        design.put("pipelines", Collections.emptyList());
        design.put("projectName", "设备清单明细测试");

        ResponseEntity<byte[]> resp = exporter.export("T-4", Collections.emptyList(), design);
        assertNotNull(resp);

        try (XSSFWorkbook wb = new XSSFWorkbook(new ByteArrayInputStream(resp.getBody()))) {
            org.apache.poi.ss.usermodel.Sheet sheet = wb.getSheet("设备清单");
            assertNotNull(sheet, "设备清单 sheet 必须存在");
            assertEquals(5, sheet.getRow(0).getPhysicalNumberOfCells(),
                    "表头必须 5 列：所属站点/设备名称/设备类型/方位角(°)/下倾角(°)");

            // 第 1 行数据：AAU-01
            org.apache.poi.ss.usermodel.Row row1 = sheet.getRow(1);
            assertEquals("S-1",       row1.getCell(0).getStringCellValue(), "所属站点列");
            assertEquals("AAU-01",    row1.getCell(1).getStringCellValue(), "设备名称列");
            assertEquals("aau",       row1.getCell(2).getStringCellValue(), "设备类型列");
            assertEquals(30.0,        row1.getCell(3).getNumericCellValue(), 1e-9, "方位角列");
            assertEquals(6.0,         row1.getCell(4).getNumericCellValue(), 1e-9, "下倾角列");

            // 第 2 行数据：AAU-02（不同方位角）
            org.apache.poi.ss.usermodel.Row row2 = sheet.getRow(2);
            assertEquals(150.0,       row2.getCell(3).getNumericCellValue(), 1e-9, "第 2 台方位角应保留原值");
            assertEquals(4.0,         row2.getCell(4).getNumericCellValue(), 1e-9, "第 2 台下倾角应保留原值");

            // 第 3 行数据：RRU-01（不同设备类型）
            org.apache.poi.ss.usermodel.Row row3 = sheet.getRow(3);
            assertEquals("rru",       row3.getCell(2).getStringCellValue(), "第 3 台设备类型");
            assertEquals(0.0,         row3.getCell(4).getNumericCellValue(), 1e-9, "RRU 下倾角 0");
        }
    }
}