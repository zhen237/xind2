package com.commplatform.s4.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * [S4-S1-迁移 2026-09-22] 工程量报表 Excel 导出 — Apache POI 实现。
 *
 * <p>工作簿 4 sheet：</p>
 * <ol>
 *   <li>BOM 物料清单（站点ID / 安装方式 / 物料名称 / 规格 / 数量 / 单位）</li>
 *   <li>设备清单（所属站点 / 设备名称 / 设备类型 / 方位角 / 下倾角）</li>
 *   <li>管线明细（管线编号 / 起点 / 终点 / 长度 / 敷设方式 / 光纤类型）</li>
 *   <li>造价估算汇总（材料费 / 施工费 / 管理费 / 利润 / 税金 / 总成本 / 每米成本）<b>标注"概算/示意"</b></li>
 * </ol>
 *
 * <p>所有表头均固定列，缺失字段留空，不允许伪称数据。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class VolumeReportExporter {

    private static final MediaType XLSX_MEDIA_TYPE =
            MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

    private static final SimpleDateFormat FILENAME_DATE = new SimpleDateFormat("yyyyMMdd_HHmmss");

    private final CostEstimationService costEstimationService;

    /**
     * 生成工程量报表 Excel 字节流响应。
     *
     * @param designTaskId   用于生成文件名（仅安全字符直接拼入，避免注入）
     * @param bomItems       bom_item 表行列表，每项含 siteId / installMethod / materialName / spec / qty / unit
     * @param design         BomService.normalizeDesignData 输出（已含 devices / pipelines）
     * @return xlsx 字节流响应
     */
    public ResponseEntity<byte[]> export(String designTaskId,
                                         List<Map<String, Object>> bomItems,
                                         Map<String, Object> design) {
        // 拉取真实管线 + 计算造价
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> pipelines = (List<Map<String, Object>>) design.getOrDefault("pipelines", Collections.emptyList());
        Map<String, Object> estimation = costEstimationService.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> estimationRows = (List<Map<String, Object>>) estimation.get("rows");
        @SuppressWarnings("unchecked")
        Map<String, Object> summary = (Map<String, Object>) estimation.get("summary");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> devices = (List<Map<String, Object>>) design.getOrDefault("devices", Collections.emptyList());

        byte[] bytes;
        try (XSSFWorkbook wb = new XSSFWorkbook()) {
            writeBomSheet(wb, bomItems);
            writeDeviceSheet(wb, devices);
            writePipelineSheet(wb, estimationRows);
            writeCostSummarySheet(wb, summary, estimation, design);

            try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                wb.write(out);
                bytes = out.toByteArray();
            }
        } catch (IOException e) {
            throw new RuntimeException("Excel 导出失败: " + e.getMessage(), e);
        }

        String safeId = (designTaskId == null) ? "report" : designTaskId.replaceAll("[^A-Za-z0-9_-]", "");
        if (safeId.isBlank()) safeId = "report";
        String filename = "VolumeReport_" + safeId + "_" + FILENAME_DATE.format(new Date()) + ".xlsx";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(XLSX_MEDIA_TYPE);
        headers.setContentDisposition(ContentDisposition.attachment()
                .filename(filename, StandardCharsets.UTF_8)
                .build());
        headers.setContentLength(bytes.length);

        log.info("[volume-report] exported: designTaskId={} size={}B bomItems={} devices={} pipelines={}",
                designTaskId, bytes.length,
                bomItems != null ? bomItems.size() : 0,
                devices != null ? devices.size() : 0,
                pipelines != null ? pipelines.size() : 0);
        return new ResponseEntity<>(bytes, headers, HttpStatus.OK);
    }

    private void writeBomSheet(XSSFWorkbook wb, List<Map<String, Object>> bomItems) {
        Sheet sheet = wb.createSheet("BOM物料清单");
        String[] headers = {"站点ID", "安装方式", "物料名称", "规格", "数量", "单位"};
        CellStyle headerStyle = headerStyle(wb);
        CellStyle cellStyle = bodyStyle(wb);

        Row h = sheet.createRow(0);
        for (int i = 0; i < headers.length; i++) {
            Cell c = h.createCell(i);
            c.setCellValue(headers[i]);
            c.setCellStyle(headerStyle);
        }

        int rowIdx = 1;
        List<Map<String, Object>> safeBomItems = bomItems != null ? bomItems : Collections.emptyList();
        for (Map<String, Object> item : safeBomItems) {
                Row row = sheet.createRow(rowIdx++);
                put(row, 0, str(item.get("siteId")), cellStyle);
                put(row, 1, str(item.get("installMethod")), cellStyle);
                put(row, 2, str(item.get("materialName")), cellStyle);
                put(row, 3, str(item.get("spec")), cellStyle);
                put(row, 4, str(item.get("qty")), cellStyle);
                put(row, 5, str(item.get("unit")), cellStyle);
        }
        autosize(sheet, headers.length);
    }

    private void writeDeviceSheet(XSSFWorkbook wb, List<Map<String, Object>> devices) {
        Sheet sheet = wb.createSheet("设备清单");
        String[] headers = {"所属站点", "设备名称", "设备类型", "方位角(°)", "下倾角(°)"};
        CellStyle headerStyle = headerStyle(wb);
        CellStyle cellStyle = bodyStyle(wb);

        Row h = sheet.createRow(0);
        for (int i = 0; i < headers.length; i++) {
            Cell c = h.createCell(i);
            c.setCellValue(headers[i]);
            c.setCellStyle(headerStyle);
        }
        int rowIdx = 1;
        if (devices == null) devices = Collections.emptyList();
        for (Map<String, Object> d : devices) {
            Row row = sheet.createRow(rowIdx++);
            put(row, 0, str(d.get("parentDevice")), cellStyle);
            put(row, 1, str(d.getOrDefault("deviceName", d.get("name"))), cellStyle);
            put(row, 2, str(d.getOrDefault("deviceType", d.get("type"))), cellStyle);
            put(row, 3, str(d.get("azimuth")), cellStyle);
            put(row, 4, str(d.get("downtilt")), cellStyle);
        }
        autosize(sheet, headers.length);
    }

    private void writePipelineSheet(XSSFWorkbook wb, List<Map<String, Object>> estimationRows) {
        Sheet sheet = wb.createSheet("管线明细");
        String[] headers = {"管线编号", "起点", "终点", "长度(米)", "敷设方式", "光纤类型", "材料费(元)", "施工费(元)", "辅材(元)"};
        CellStyle headerStyle = headerStyle(wb);
        CellStyle cellStyle = bodyStyle(wb);

        Row h = sheet.createRow(0);
        for (int i = 0; i < headers.length; i++) {
            Cell c = h.createCell(i);
            c.setCellValue(headers[i]);
            c.setCellStyle(headerStyle);
        }
        int rowIdx = 1;
        List<Map<String, Object>> safeRows = estimationRows != null ? estimationRows : Collections.emptyList();
        for (Map<String, Object> r : safeRows) {
            Row row = sheet.createRow(rowIdx++);
            put(row, 0, str(r.get("pipelineId")), cellStyle);
            put(row, 1, str(r.get("startSite")), cellStyle);
            put(row, 2, str(r.get("endSite")), cellStyle);
            put(row, 3, str(r.get("lengthM")), cellStyle);
            put(row, 4, str(r.get("pipelineType")), cellStyle);
            put(row, 5, str(r.get("fiberType")), cellStyle);
            put(row, 6, str(r.get("materialCost")), cellStyle);
            put(row, 7, str(r.get("constructionCost")), cellStyle);
            put(row, 8, str(r.get("auxiliaryCost")), cellStyle);
        }
        autosize(sheet, headers.length);
    }

    private void writeCostSummarySheet(XSSFWorkbook wb, Map<String, Object> summary,
                                       Map<String, Object> estimation, Map<String, Object> design) {
        Sheet sheet = wb.createSheet("造价估算汇总");
        CellStyle headerStyle = headerStyle(wb);
        CellStyle labelStyle = labelStyle(wb);
        CellStyle valueStyle = bodyStyle(wb);
        CellStyle warnStyle = warningStyle(wb);

        Row title = sheet.createRow(0);
        Cell t = title.createCell(0);
        t.setCellValue("工程量造价估算（" + str(estimation.get("warning")) + "）");
        t.setCellStyle(headerStyle);
        sheet.addMergedRegion(new CellRangeAddress(0, 0, 0, 2));

        String[][] rows = new String[][]{
                {"项目", "值（元）", "备注"},
                {"材料费合计",     str(summary.get("materialCost")),     "光纤单价 × 管线长度"},
                {"施工费合计",     str(summary.get("constructionCost")), "敷设方式单价 × 管线长度"},
                {"辅材合计",       str(summary.get("auxiliaryCost")),    "土方/接头盒/人孔"},
                {"直接费小计",     str(summary.get("directSubtotal")),   "材料 + 施工 + 辅材"},
                {"管理费",         str(summary.get("managementFee")),    str(summary.get("managementFeePct")) + "% × 直接费"},
                {"利润",           str(summary.get("profit")),           str(summary.get("profitPct")) + "% × (直接费+管理费)"},
                {"税金",           str(summary.get("tax")),              str(summary.get("taxPct")) + "% × (直接费+管理费+利润)"},
                {"总成本",         str(summary.get("totalCost")),        "材料 + 施工 + 辅材 + 管理费 + 利润 + 税金"},
                {"管线总长度(米)", str(summary.get("totalLengthM")),     "全部管线累加"},
                {"每米成本",       str(summary.get("costPerMeter")),     "总成本 / 总长度"},
        };

        for (int i = 0; i < rows.length; i++) {
            Row row = sheet.createRow(i + 1);
            for (int j = 0; j < rows[i].length; j++) {
                Cell c = row.createCell(j);
                c.setCellValue(rows[i][j]);
                c.setCellStyle(i == 0 ? headerStyle : (j == 0 ? labelStyle : (i == rows.length - 1 ? warnStyle : valueStyle)));
            }
        }

        Row note = sheet.createRow(rows.length + 2);
        Cell n = note.createCell(0);
        n.setCellValue("⚠ 本造价为「概算 / 示意」级别，源自挑战杯演示场景参数。不得作为行业基准单价，工程预算请用本地工程造价口径校准。");
        n.setCellStyle(warnStyle);
        sheet.addMergedRegion(new CellRangeAddress(rows.length + 2, rows.length + 2, 0, 4));

        autosize(sheet, 3);
    }

    // ─── 样式辅助 ────────────────────────────────────────────────────────────
    private CellStyle headerStyle(XSSFWorkbook wb) {
        CellStyle s = wb.createCellStyle();
        Font f = wb.createFont(); f.setBold(true); f.setColor(IndexedColors.WHITE.getIndex());
        s.setFont(f);
        s.setFillForegroundColor(IndexedColors.GREY_50_PERCENT.getIndex());
        s.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        s.setAlignment(HorizontalAlignment.CENTER);
        return s;
    }

    private CellStyle labelStyle(XSSFWorkbook wb) {
        CellStyle s = wb.createCellStyle();
        Font f = wb.createFont(); f.setBold(true);
        s.setFont(f);
        s.setFillForegroundColor(IndexedColors.LIGHT_CORNFLOWER_BLUE.getIndex());
        s.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        return s;
    }

    private CellStyle bodyStyle(XSSFWorkbook wb) {
        return wb.createCellStyle();
    }

    private CellStyle warningStyle(XSSFWorkbook wb) {
        CellStyle s = wb.createCellStyle();
        Font f = wb.createFont();
        f.setBold(true);
        f.setColor(IndexedColors.DARK_YELLOW.getIndex());
        s.setFont(f);
        s.setFillForegroundColor(IndexedColors.LIGHT_YELLOW.getIndex());
        s.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        return s;
    }

    private void put(Row row, int idx, String s, CellStyle style) {
        Cell c = row.createCell(idx);
        c.setCellValue(s);
        c.setCellStyle(style);
    }

    private String str(Object o) {
        if (o == null) return "";
        return String.valueOf(o);
    }

    private void autosize(Sheet sheet, int cols) {
        for (int i = 0; i < cols; i++) {
            try { sheet.autoSizeColumn(i); } catch (Exception ignored) { }
        }
    }
}