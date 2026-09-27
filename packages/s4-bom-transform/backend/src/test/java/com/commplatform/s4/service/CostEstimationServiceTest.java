package com.commplatform.s4.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * [S4-S1-迁移 2026-09-22] CostEstimationService 单元测试。
 *
 * <p>验证：</p>
 * <ul>
 *   <li>正常管线造价按敷设方式/光纤类型查单价</li>
 *   <li>未知敷设方式/光纤类型回退到默认</li>
 *   <li>空管线返回空 rows + 0 合计</li>
 *   <li>管理费/利润/税金比例符合 cost_configs.json</li>
 *   <li>每米成本计算 = totalCost / totalLength</li>
 *   <li>warning / priceTag 始终标注"概算/示意"</li>
 * </ul>
 */
@DisplayName("CostEstimationService 造价估算")
class CostEstimationServiceTest {

    private CostEstimationService svc;

    @BeforeEach
    void setUp() {
        svc = new CostEstimationService();
    }

    @Test
    @DisplayName("正常管线：直埋+G.652D，100m")
    void normalPipeline() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-001", "startSite", "S-A",
                        "endSite", "S-B", "pipelineType", "直埋",
                        "fiberType", "G.652D", "lengthM", 100.0)
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        assertEquals(1, rows.size());
        Map<String, Object> row = rows.get(0);
        // 直埋施工 45/m × 100 = 4500；光纤 12/m × 100 = 1200；土方 0.30 × 100 × 50 = 1500；接头盒 + 人孔 各 1 个
        assertEquals(1200.0, ((Number) row.get("materialCost")).doubleValue(), 0.01);
        assertEquals(4500.0, ((Number) row.get("constructionCost")).doubleValue(), 0.01);
        assertEquals("概算/示意", row.get("priceTag"));
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        assertEquals(100.0, ((Number) sum.get("totalLengthM")).doubleValue(), 0.01);
        assertEquals("概算 / 示意", sum.get("priceTag"));
        assertEquals("元", sum.get("currencyUnit"));
        assertEquals(5.0, ((Number) sum.get("managementFeePct")).doubleValue(), 0.01);
        assertEquals(7.0, ((Number) sum.get("profitPct")).doubleValue(), 0.01);
        assertEquals(9.0, ((Number) sum.get("taxPct")).doubleValue(), 0.01);
        assertNotNull(r.get("warning"));
        assertTrue(String.valueOf(r.get("warning")).contains("概算"));
    }

    @Test
    @DisplayName("未知敷设方式回退到 default")
    void unknownPipelineTypeFallback() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-X", "lengthM", 50.0,
                        "pipelineType", "宇宙传输", "fiberType", "G.652D")
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        Map<String, Object> row = rows.get(0);
        // 未知类型回退"管道"（80 元/m）
        assertTrue(String.valueOf(row.get("pipelineType")).startsWith("管道"));
        assertEquals(80.0 * 50.0, ((Number) row.get("constructionCost")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("未知光纤类型回退到 default")
    void unknownFiberTypeFallback() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-Y", "lengthM", 50.0,
                        "pipelineType", "直埋", "fiberType", "光纤_未来")
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        Map<String, Object> row = rows.get(0);
        assertTrue(String.valueOf(row.get("fiberType")).startsWith("G.652D"));
        assertEquals(12.0 * 50.0, ((Number) row.get("materialCost")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("空管线 → 空 rows + 0 合计")
    void emptyPipelines() {
        Map<String, Object> r = svc.estimate(Collections.emptyList());
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        assertTrue(rows.isEmpty());
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        assertEquals(0.0, ((Number) sum.get("totalCost")).doubleValue(), 0.01);
        assertEquals(0.0, ((Number) sum.get("costPerMeter")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("null 入参 → 空 rows")
    void nullInput() {
        Map<String, Object> r = svc.estimate(null);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        assertTrue(rows.isEmpty());
    }

    @Test
    @DisplayName("每米成本 = 总成本 / 总长度")
    void costPerMeter() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "A", "lengthM", 100.0, "pipelineType", "直埋", "fiberType", "G.652D"),
                Map.of("pipelineId", "B", "lengthM", 200.0, "pipelineType", "管道", "fiberType", "G.652D")
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        double totalCost = ((Number) sum.get("totalCost")).doubleValue();
        double totalLen = ((Number) sum.get("totalLengthM")).doubleValue();
        double costPerM = ((Number) sum.get("costPerMeter")).doubleValue();
        assertEquals(totalLen, 300.0, 0.01);
        assertEquals(round2(totalCost / totalLen), costPerM, 0.01);
    }

    @Test
    @DisplayName("管理费/利润/税金按比例放大")
    void ratios() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "A", "lengthM", 100.0, "pipelineType", "直埋", "fiberType", "G.652D")
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        double direct = ((Number) sum.get("directSubtotal")).doubleValue();
        double mgmt = ((Number) sum.get("managementFee")).doubleValue();
        double profit = ((Number) sum.get("profit")).doubleValue();
        double tax = ((Number) sum.get("tax")).doubleValue();
        double total = ((Number) sum.get("totalCost")).doubleValue();
        // 直接费 100%
        assertEquals(round2(direct * 0.05), mgmt, 0.01);
        assertEquals(round2((direct + mgmt) * 0.07), profit, 0.01);
        assertEquals(round2((direct + mgmt + profit) * 0.09), tax, 0.01);
        assertEquals(round2(direct + mgmt + profit + tax), total, 0.01);
    }

    @Test
    @DisplayName("长度 0 → 直接费 0 且每米成本 0")
    void zeroLength() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "A", "lengthM", 0.0, "pipelineType", "直埋", "fiberType", "G.652D")
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        assertEquals(0.0, ((Number) sum.get("totalCost")).doubleValue(), 0.01);
        assertEquals(0.0, ((Number) sum.get("costPerMeter")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("warning 永远包含\"概算 / 示意\"关键词")
    void warningContainsTag() {
        Map<String, Object> r = svc.estimate(Collections.emptyList());
        String w = String.valueOf(r.get("warning"));
        assertTrue(w.contains("概算"));
        assertTrue(w.contains("示意"));
    }

    @Test
    @DisplayName("光缆单价整体覆盖：15 元/m × 100m → 材料费 1500（对应 QGIS 每米价格 SpinBox）")
    void fiberPriceOverride() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-001", "startSite", "S-A", "endSite", "S-B",
                        "pipelineType", "直埋", "fiberType", "G.652D", "lengthM", 100.0)
        );
        Map<String, Object> r = svc.estimate(pipelines, 15.0);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        // 覆盖价 15/m × 100m = 1500（默认 G.652D 是 12/m × 100 = 1200）
        assertEquals(1500.0, ((Number) rows.get(0).get("materialCost")).doubleValue(), 0.01);
        assertEquals(15.0, ((Number) rows.get(0).get("unitPriceFiber")).doubleValue(), 0.01);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        assertEquals(15.0, ((Number) sum.get("fiberPriceOverride")).doubleValue(), 0.01);
        assertTrue(String.valueOf(sum.get("priceOverrideNote")).contains("15"));
        // 施工费不受覆盖影响（45/m × 100 = 4500）
        assertEquals(4500.0, ((Number) rows.get(0).get("constructionCost")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("非法覆盖值（null / 0 / 负数）→ 忽略，仍按 cost_configs.json 取价")
    void fiberPriceOverrideInvalidIgnored() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "A", "pipelineType", "直埋", "fiberType", "G.652D", "lengthM", 100.0)
        );
        for (Double bad : new Double[]{null, 0.0, -3.0}) {
            Map<String, Object> r = svc.estimate(pipelines, bad);
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
            assertEquals(1200.0, ((Number) rows.get(0).get("materialCost")).doubleValue(), 0.01,
                    "覆盖值 " + bad + " 应被忽略");
            @SuppressWarnings("unchecked")
            Map<String, Object> sum = (Map<String, Object>) r.get("summary");
            assertFalse(sum.containsKey("fiberPriceOverride"), "覆盖值 " + bad + " 不应写回 summary");
        }
    }

    private double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}