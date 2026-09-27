package com.commplatform.s4.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * [S4-S1-迁移 2026-09-22] CostEstimationService 单元测试。
 *
 * <p>v1.1（2026-09-27）：对齐 QGIS calculate_pipeline_cost 分项口径后的校准断言——
 * 直埋/管道/架空三分支分项（光缆/土方/回填/标石/人孔/电杆/拉线/接头盒）、
 * 费率 15% / 5% / 9%（均以直接费为基数，非级联）。</p>
 */
@DisplayName("CostEstimationService 造价估算（QGIS 口径）")
class CostEstimationServiceTest {

    private CostEstimationService svc;

    @BeforeEach
    void setUp() {
        svc = new CostEstimationService();
    }

    @Test
    @DisplayName("直埋 100m + G.652D：光缆1200 + 土方4615 + 回填2769 + 标石2个160 + 接头盒1个200")
    void normalDirectBuried() {
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
        // 光缆 12/m × 100 = 1200；标石 int(100/100)+1=2 × 80 = 160；接头盒 max(1,0)=1 × 200 = 200
        assertEquals(1560.0, ((Number) row.get("materialCost")).doubleValue(), 0.01);
        // 土方 100×(110/1000+0.6)×(1.2+0.1)=92.3m³ → 开挖 92.3×50=4615 + 回填 92.3×30=2769
        assertEquals(7384.0, ((Number) row.get("constructionCost")).doubleValue(), 0.01);
        // 附属物 = 标石160 + 接头盒200 = 360（已含在材料费内）
        assertEquals(360.0, ((Number) row.get("accessoryCost")).doubleValue(), 0.01);
        assertEquals(8944.0, ((Number) row.get("directCost")).doubleValue(), 0.01);
        assertEquals("概算/示意", row.get("priceTag"));
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) row.get("costDetail");
        assertEquals(1200.0, ((Number) detail.get("光缆费(元)")).doubleValue(), 0.01);
        assertEquals(2, ((Number) detail.get("标石数量(个)")).intValue());
        assertEquals(1, ((Number) detail.get("接头盒数量(个)")).intValue());
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        assertEquals(100.0, ((Number) sum.get("totalLengthM")).doubleValue(), 0.01);
        assertEquals("概算 / 示意", sum.get("priceTag"));
        assertEquals("元", sum.get("currencyUnit"));
    }

    @Test
    @DisplayName("管道分支：管道材料费 + 城市土方(60/40) + 人孔100m间距 + 接头盒")
    void ductBranch() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-D", "pipelineType", "管道",
                        "fiberType", "G.652D", "lengthM", 50.0)
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        Map<String, Object> row = rows.get(0);
        // 光缆600 + 管道45×50=2250 + 接头盒1×200 = 3050
        assertEquals(3050.0, ((Number) row.get("materialCost")).doubleValue(), 0.01);
        // 土方 50×0.6×(1.5+0.2)=51m³ → 51×60=3060 + 51×40=2040 + 人孔1×3000 = 8100
        assertEquals(8100.0, ((Number) row.get("constructionCost")).doubleValue(), 0.01);
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) row.get("costDetail");
        assertEquals(1, ((Number) detail.get("人孔数量(个)")).intValue());
        assertEquals(2250.0, ((Number) detail.get("管道费(元)")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("架空分支：电杆50m杆距 + 拉线每公里0.3条 + 接头盒")
    void aerialBranch() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-A", "pipelineType", "架空",
                        "fiberType", "G.652D", "lengthM", 200.0)
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        Map<String, Object> row = rows.get(0);
        // 光缆 12×200=2400 + 电杆 int(200/50)+1=5×1500=7500 + 拉线 int(200/1000×0.3)=0×500=0 + 接头盒1×200
        assertEquals(10100.0, ((Number) row.get("materialCost")).doubleValue(), 0.01);
        assertEquals(0.0, ((Number) row.get("constructionCost")).doubleValue(), 0.01);
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) row.get("costDetail");
        assertEquals(5, ((Number) detail.get("电杆数量(根)")).intValue());
        assertEquals(0, ((Number) detail.get("拉线数量(条)")).intValue());
    }

    @Test
    @DisplayName("未知敷设方式回退到管道分支（分项口径）")
    void unknownPipelineTypeFallback() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-X", "lengthM", 50.0,
                        "pipelineType", "宇宙传输", "fiberType", "G.652D")
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        Map<String, Object> row = rows.get(0);
        // 未知类型回退"管道"→ 走管道分项：施工 = 土方3060+回填2040+人孔3000 = 8100
        assertTrue(String.valueOf(row.get("pipelineType")).startsWith("管道"));
        assertEquals(8100.0, ((Number) row.get("constructionCost")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("未知光纤类型回退到 G.652D（光缆费按 12 元/m）")
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
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) row.get("costDetail");
        assertEquals(600.0, ((Number) detail.get("光缆费(元)")).doubleValue(), 0.01);
    }

    @Test
    @DisplayName("自定义埋深/管径参与土方体积计算（数据通路 depthM/diameterMm）")
    void customDepthDiameter() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-Z", "lengthM", 100.0,
                        "pipelineType", "直埋", "fiberType", "G.652D",
                        "depthM", 1.0, "diameterMm", 90.0)
        );
        Map<String, Object> r = svc.estimate(pipelines);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        // 土方 = 100 × (0.090+0.6) × (1.0+0.1) = 75.9 m³ → 开挖 3795 + 回填 2277 = 6072
        assertEquals(6072.0, ((Number) rows.get(0).get("constructionCost")).doubleValue(), 0.01);
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
    @DisplayName("费率对齐 QGIS：管理费15%/利润5%/税金9%，均以直接费为基数（非级联）")
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
        assertEquals(15.0, ((Number) sum.get("managementFeePct")).doubleValue(), 0.01);
        assertEquals(5.0,  ((Number) sum.get("profitPct")).doubleValue(), 0.01);
        assertEquals(9.0,  ((Number) sum.get("taxPct")).doubleValue(), 0.01);
        assertEquals(round2(direct * 0.15), mgmt, 0.01);
        assertEquals(round2(direct * 0.05), profit, 0.01);
        assertEquals(round2(direct * 0.09), tax, 0.01);
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
    @DisplayName("光缆单价整体覆盖：15 元/m × 100m → 光缆费 1500（对应 QGIS 每米价格 SpinBox）")
    void fiberPriceOverride() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("pipelineId", "PL-001", "startSite", "S-A", "endSite", "S-B",
                        "pipelineType", "直埋", "fiberType", "G.652D", "lengthM", 100.0)
        );
        Map<String, Object> r = svc.estimate(pipelines, 15.0);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) r.get("rows");
        Map<String, Object> row = rows.get(0);
        // 覆盖价 15/m × 100m = 1500（默认 G.652D 是 12/m × 100 = 1200）
        assertEquals(15.0, ((Number) row.get("unitPriceFiber")).doubleValue(), 0.01);
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) row.get("costDetail");
        assertEquals(1500.0, ((Number) detail.get("光缆费(元)")).doubleValue(), 0.01);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.get("summary");
        assertEquals(15.0, ((Number) sum.get("fiberPriceOverride")).doubleValue(), 0.01);
        assertTrue(String.valueOf(sum.get("priceOverrideNote")).contains("15"));
        // 施工费分项不受覆盖影响（土方 4615 + 回填 2769 = 7384）
        assertEquals(7384.0, ((Number) row.get("constructionCost")).doubleValue(), 0.01);
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
            assertEquals(12.0, ((Number) rows.get(0).get("unitPriceFiber")).doubleValue(), 0.01,
                    "覆盖值 " + bad + " 应被忽略");
            @SuppressWarnings("unchecked")
            Map<String, Object> d = (Map<String, Object>) rows.get(0).get("costDetail");
            assertEquals(1200.0, ((Number) d.get("光缆费(元)")).doubleValue(), 0.01,
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
