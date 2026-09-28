package com.commplatform.s4.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.util.*;

/**
 * [S4-S1-迁移 2026-09-22] 工程量报表造价计算 — 复用 QGIS 插件 PipelineConfig 口径。
 *
 * <p>本服务仅做「概算 / 示意」级别的造价估算。所有单价来源于
 * {@code classpath:cost_configs.json}（对应 QGIS 插件
 * {@code PipelineConfig.fiber_cost_configs / cost_configs}）。</p>
 *
 * <p><b>严禁把本服务产出的金额对外宣传为行业基准单价</b>——必须保留「概算 / 示意」
 * 标注，并在产物里显式声明，工程预算前请以本地工程造价口径校准。</p>
 */
@Slf4j
@Service
public class CostEstimationService {

    private static final String CONFIG_RESOURCE = "cost_configs.json";

    private final ObjectMapper objectMapper = new ObjectMapper();
    private Map<String, Object> config;

    /**
     * 计算单个管线造价行 + 全量合计。
     *
     * @param pipelineRows BomService.extractPipelines 产出的 List<Map> 行，
     *                     每行至少含 pipelineType / fiberType / lengthM
     * @return { rows, summary, warning, currencyUnit }
     */
    public Map<String, Object> estimate(List<Map<String, Object>> pipelineRows) {
        if (pipelineRows == null) pipelineRows = Collections.emptyList();
        ensureLoaded();

        Map<String, Object> fiberPrices = getChild("fiber_unit_prices_yuan_per_m");
        Map<String, Object> constructionPrices = getChild("construction_unit_prices_yuan_per_m");
        Map<String, Object> ratios = getChild("ratio_settings");
        String fallbackPipelineType = (String) getChildOr("fallback_when_unknown_pipeline_type", "管道");
        String fallbackFiberType    = (String) getChildOr("fallback_when_unknown_fiber_type", "G.652D");

        double mgmtFeePct = toDouble(ratios.getOrDefault("management_fee_pct_of_direct", 5.0));
        double profitPct  = toDouble(ratios.getOrDefault("profit_pct_of_subtotal", 7.0));
        double taxPct     = toDouble(ratios.getOrDefault("tax_pct_of_subtotal_with_profit", 9.0));
        double volumePerM = toDouble(ratios.getOrDefault("trench_volume_m3_per_m", 0.30));
        double jointBoxInterval = toDouble(ratios.getOrDefault("joint_box_interval_m", 500.0));
        double manholeInterval  = toDouble(ratios.getOrDefault("manhole_interval_m", 300.0));

        @SuppressWarnings("unchecked")
        Map<String, Object> aux = (Map<String, Object>) config.getOrDefault("auxiliary_unit_prices", Collections.emptyMap());
        double trenchYuanPerM3  = toDouble(aux.getOrDefault("土方开挖_yuan_per_m3", 50.0));
        double jointBoxYuan     = toDouble(aux.getOrDefault("接头盒_yuan_per_unit", 200.0));
        double manholeYuan      = toDouble(aux.getOrDefault("人孔_yuan_per_unit", 3000.0));

        List<Map<String, Object>> rows = new ArrayList<>();
        double sumMaterial = 0.0;
        double sumConstruction = 0.0;
        double sumAuxiliary = 0.0;
        double sumLength = 0.0;

        int idx = 0;
        for (Map<String, Object> pl : pipelineRows) {
            String pt   = String.valueOf(pl.getOrDefault("pipelineType", "")).trim();
            String fib  = String.valueOf(pl.getOrDefault("fiberType", "")).trim();
            Double len  = toDouble(pl.get("lengthM"));
            if (len == null || len <= 0) len = 0.0;

            // 未知类型回退 → 单价仍取得到
            // 判断条件：值是空 / 字面"未知" / 单价表里查不到（视为未知）
            String ptKey  = resolveKnown(pt, fallbackPipelineType,
                    constructionPrices.keySet(), "default");
            String fibKey = resolveKnown(fib, fallbackFiberType,
                    fiberPrices.keySet(), "default");

            double fiberYuanPerM  = toDouble(fiberPrices.getOrDefault(fibKey, fiberPrices.getOrDefault("default", 12.0)));
            double constrYuanPerM = toDouble(constructionPrices.getOrDefault(ptKey, constructionPrices.getOrDefault("default", 50.0)));
            double materialCost   = round2(fiberYuanPerM * len);
            double constructionCost = round2(constrYuanPerM * len);
            // 辅材：土方开挖量 + 接头盒 + 人孔（间距推算）
            double trenchVol = round2(volumePerM * len);
            // len = 0 时不应产生接头盒/人孔附属物（管线本身为 0）
            double jointBoxCount = (jointBoxInterval > 0 && len > 0) ? Math.max(1, Math.round(len / jointBoxInterval)) : 0;
            double manholeCount  = (manholeInterval  > 0 && len > 0) ? Math.max(1, Math.round(len / manholeInterval))  : 0;
            double auxiliaryCost = round2(trenchVol * trenchYuanPerM3
                    + jointBoxCount * jointBoxYuan
                    + manholeCount  * manholeYuan);

            double directCost = round2(materialCost + constructionCost + auxiliaryCost);

            Map<String, Object> row = new LinkedHashMap<>();
            row.put("idx", ++idx);
            row.put("pipelineId",  String.valueOf(pl.getOrDefault("pipelineId", "PL-" + idx)));
            row.put("startSite",   pl.getOrDefault("startSite", ""));
            row.put("endSite",     pl.getOrDefault("endSite", ""));
            row.put("pipelineType", ptKey + (ptKey.equals(pt) ? "" : "（原:" + (pt.isBlank() ? "空" : pt) + "→回退）"));
            row.put("fiberType",    fibKey + (fibKey.equals(fib) ? "" : "（原:" + (fib.isBlank() ? "空" : fib) + "→回退）"));
            row.put("lengthM",      len);
            row.put("materialCost",    materialCost);
            row.put("constructionCost", constructionCost);
            row.put("trenchVolumeM3",  trenchVol);
            row.put("jointBoxCount",   (int) jointBoxCount);
            row.put("manholeCount",    (int) manholeCount);
            row.put("auxiliaryCost",   auxiliaryCost);
            row.put("directCost",       directCost);
            row.put("unitPriceFiber",    fiberYuanPerM);
            row.put("unitPriceConstr",   constrYuanPerM);
            row.put("priceTag",  "概算/示意");
            rows.add(row);

            sumMaterial     += materialCost;
            sumConstruction += constructionCost;
            sumAuxiliary    += auxiliaryCost;
            sumLength       += len;
        }

        // 汇总（管理费按直接费比例，利润按直接+管理费，税金按再前二者）
        double directSubtotal = round2(sumMaterial + sumConstruction + sumAuxiliary);
        double managementFee  = round2(directSubtotal * mgmtFeePct / 100.0);
        double profitBase     = round2(directSubtotal + managementFee);
        double profit         = round2(profitBase * profitPct / 100.0);
        double taxableBase    = round2(profitBase + profit);
        double tax            = round2(taxableBase * taxPct / 100.0);
        double totalCost      = round2(taxableBase + tax);
        double costPerMeter   = sumLength > 0 ? round2(totalCost / sumLength) : 0.0;

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("materialCost",      round2(sumMaterial));
        summary.put("constructionCost",  sumConstruction);
        summary.put("auxiliaryCost",     sumAuxiliary);
        summary.put("directSubtotal",    directSubtotal);
        summary.put("managementFeePct",  mgmtFeePct);
        summary.put("managementFee",     managementFee);
        summary.put("profitPct",         profitPct);
        summary.put("profit",            profit);
        summary.put("taxPct",            taxPct);
        summary.put("tax",               tax);
        summary.put("totalCost",         totalCost);
        summary.put("totalLengthM",      round2(sumLength));
        summary.put("costPerMeter",      costPerMeter);
        summary.put("currencyUnit",      "元");
        summary.put("priceTag",          "概算 / 示意");

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("rows", rows);
        result.put("summary", summary);
        result.put("warning", "本造价为「概算 / 示意」级别，源自挑战杯演示场景参数。不得作为行业基准单价；工程预算请用本地造价口径校准。");
        result.put("currencyUnit", "元");
        return result;
    }

    private void ensureLoaded() {
        if (config != null) return;
        try (InputStream in = new ClassPathResource(CONFIG_RESOURCE).getInputStream()) {
            config = objectMapper.readValue(in, new TypeReference<Map<String, Object>>() {});
            log.info("[cost-estimation] cost_configs.json loaded: version={}",
                    ((Map<?, ?>) config.getOrDefault("_meta", Collections.emptyMap())).get("version"));
        } catch (IOException e) {
            log.error("[cost-estimation] load cost_configs.json failed, fallback to empty config", e);
            config = Collections.emptyMap();
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> getChild(String key) {
        ensureLoaded();
        Object v = config.get(key);
        return v instanceof Map<?, ?> ? (Map<String, Object>) v : Collections.emptyMap();
    }

    private Object getChildOr(String key, Object defaultVal) {
        ensureLoaded();
        return config.getOrDefault(key, defaultVal);
    }

    private double toDouble(Object o) {
        if (o instanceof Number n) return n.doubleValue();
        if (o instanceof String s) {
            try { return Double.parseDouble(s.trim()); } catch (NumberFormatException ignored) { return 0.0; }
        }
        return 0.0;
    }

    private double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }

    /**
     * 已知 key 解析：值非空、非"未知"、且在 known 集合内 → 原样返回；
     * 否则回退到 fallbackKey（"管道"/"G.652D"）。
     */
    private String resolveKnown(String raw, String fallbackKey, java.util.Set<String> knownKeys, String defaultKey) {
        if (raw == null || raw.isBlank() || "未知".equals(raw)) return fallbackKey;
        // 单价表里有 "default" 哨兵 key，识别真实业务键时排除
        if (knownKeys.contains(raw)) return raw;
        // 业务键未知，但单价可由 default 兜底：仍回退（保证 UI 看到"管道"而不是"宇宙传输"）
        return fallbackKey;
    }
}