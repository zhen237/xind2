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
 * <p>v1.1（2026-09-27）：对齐 QGIS {@code calculate_pipeline_cost}（design_engine/pipeline.py:634）
 * 的<b>按敷设方式分项实算</b>口径——直埋（光缆+土方+回填+标石+接头盒）、管道（管道+光缆+土方+回填+人孔+接头盒）、
 * 架空（光缆+电杆+拉线+接头盒）；费率对齐 QGIS：施工管理费 15% / 利润 5% / 税金 9%，三项均以直接费为基数。</p>
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
     * 计算单个管线造价行 + 全量合计（单价全取 cost_configs.json）。
     *
     * @param pipelineRows BomService.extractPipelines 产出的 List<Map> 行，
     *                     每行至少含 pipelineType / fiberType / lengthM
     * @return { rows, summary, warning, currencyUnit }
     */
    public Map<String, Object> estimate(List<Map<String, Object>> pipelineRows) {
        return estimate(pipelineRows, null);
    }

    /**
     * 带光缆单价整体覆盖的造价计算 — 对应 QGIS 插件「每米价格」SpinBox（design_dock.py:1726，默认 15 元/m）
     * 整体覆盖光缆基准单价的口径。
     *
     * @param fiberPriceOverride 光缆整体覆盖单价（元/m）；null 或 &le;0 时不覆盖，仍走 cost_configs.json 按光纤类型取价
     */
    public Map<String, Object> estimate(List<Map<String, Object>> pipelineRows, Double fiberPriceOverride) {
        if (pipelineRows == null) pipelineRows = Collections.emptyList();
        ensureLoaded();
        boolean overrideEnabled = fiberPriceOverride != null && fiberPriceOverride > 0;

        Map<String, Object> fiberPrices = getChild("fiber_unit_prices_yuan_per_m");
        Map<String, Object> constructionPrices = getChild("construction_unit_prices_yuan_per_m");
        Map<String, Object> typeConfigs = getChild("type_cost_configs");
        Map<String, Object> ratios = getChild("ratio_settings");
        String fallbackPipelineType = (String) getChildOr("fallback_when_unknown_pipeline_type", "管道");
        String fallbackFiberType    = (String) getChildOr("fallback_when_unknown_fiber_type", "G.652D");

        double mgmtFeePct = toDouble(ratios.getOrDefault("management_fee_pct_of_direct", 15.0));
        double profitPct  = toDouble(ratios.getOrDefault("profit_pct_of_direct", 5.0));
        double taxPct     = toDouble(ratios.getOrDefault("tax_pct_of_direct", 9.0));

        List<Map<String, Object>> rows = new ArrayList<>();
        double sumMaterial = 0.0;
        double sumConstruction = 0.0;
        double sumAuxiliary = 0.0;
        double sumLength = 0.0;

        // 已知敷设方式 = 分项配置 ∪ 综合单价表（桥架等无分项配置的类型走综合价分支，不误回退管道）
        Set<String> knownTypes = new LinkedHashSet<>(typeConfigs.keySet());
        knownTypes.addAll(constructionPrices.keySet());
        knownTypes.remove("default");

        int idx = 0;
        for (Map<String, Object> pl : pipelineRows) {
            String pt   = String.valueOf(pl.getOrDefault("pipelineType", "")).trim();
            String fib  = String.valueOf(pl.getOrDefault("fiberType", "")).trim();
            Double len  = toDouble(pl.get("lengthM"));
            if (len == null || len <= 0) len = 0.0;

            // 未知类型回退 → 单价仍取得到
            String ptKey  = resolveKnown(pt, fallbackPipelineType, knownTypes, "default");
            String fibKey = resolveKnown(fib, fallbackFiberType, fiberPrices.keySet(), "default");

            double fiberYuanPerM = overrideEnabled ? fiberPriceOverride
                    : toDouble(fiberPrices.getOrDefault(fibKey, fiberPrices.getOrDefault("default", 12.0)));

            // —— 按 QGIS calculate_pipeline_cost 口径分项实算 ——
            // 材料桶：光缆 / 管道 / 标石 / 接头盒 / 电杆 / 拉线（对应 QGIS material_cost）
            // 施工桶：土方开挖 / 回填 / 人孔（对应 QGIS construction_cost）
            // 附属物小计：标石+接头盒+电杆+拉线+人孔（已含在材料/施工桶内，仅供报表展示）
            double material = 0.0, construction = 0.0, accessory = 0.0;
            Map<String, Object> detail = new LinkedHashMap<>();

            if (len > 0) {
                double cableCost = round2(fiberYuanPerM * len);
                material += cableCost;
                detail.put("光缆费(元)", cableCost);

                Map<String, Object> tc = typeConfigs.get(ptKey) instanceof Map<?, ?> cfg
                        ? asStringObjectMap(cfg) : Collections.emptyMap();

                switch (ptKey) {
                    case "直埋" -> {
                        double depth = orDefault(toDouble(pl.get("depthM")), toDouble(tc.get("default_depth_m")), 1.2);
                        double diam  = orDefault(toDouble(pl.get("diameterMm")), toDouble(tc.get("default_diameter_mm")), 110.0);
                        double vol = len * (diam / 1000.0 + toDouble(tc.getOrDefault("trench_extra_width_m", 0.6)))
                                * (depth + toDouble(tc.getOrDefault("trench_extra_depth_m", 0.1)));
                        double dig = round2(vol * toDouble(tc.getOrDefault("trench_dig_yuan_per_m3", 50.0)));
                        double backfill = round2(vol * toDouble(tc.getOrDefault("backfill_yuan_per_m3", 30.0)));
                        construction += dig + backfill;
                        detail.put("土方开挖费(元)", dig);
                        detail.put("回填费(元)", backfill);
                        int stones = (int) (len / toDouble(tc.getOrDefault("marker_stone_interval_m", 100.0))) + 1;
                        double stoneCost = round2(stones * toDouble(tc.getOrDefault("marker_stone_yuan_per_unit", 80.0)));
                        material += stoneCost; accessory += stoneCost;
                        detail.put("标石数量(个)", stones);
                        detail.put("标石费(元)", stoneCost);
                        int joints = Math.max(1, (int) (len / toDouble(tc.getOrDefault("joint_box_interval_m", 2000.0))));
                        double jointCost = round2(joints * toDouble(tc.getOrDefault("joint_box_yuan_per_unit", 200.0)));
                        material += jointCost; accessory += jointCost;
                        detail.put("接头盒数量(个)", joints);
                        detail.put("接头盒费(元)", jointCost);
                    }
                    case "管道" -> {
                        double ductCost = round2(len * toDouble(tc.getOrDefault("duct_material_yuan_per_m", 45.0)));
                        material += ductCost;
                        detail.put("管道费(元)", ductCost);
                        double depth = orDefault(toDouble(pl.get("depthM")), toDouble(tc.get("default_depth_m")), 1.5);
                        double vol = len * toDouble(tc.getOrDefault("trench_width_m", 0.6))
                                * (depth + toDouble(tc.getOrDefault("trench_extra_depth_m", 0.2)));
                        double dig = round2(vol * toDouble(tc.getOrDefault("trench_dig_yuan_per_m3", 60.0)));
                        double backfill = round2(vol * toDouble(tc.getOrDefault("backfill_yuan_per_m3", 40.0)));
                        construction += dig + backfill;
                        detail.put("土方开挖费(元)", dig);
                        detail.put("回填费(元)", backfill);
                        int manholes = Math.max(1, (int) (len / toDouble(tc.getOrDefault("manhole_interval_m", 100.0))));
                        double manholeCost = round2(manholes * toDouble(tc.getOrDefault("manhole_yuan_per_unit", 3000.0)));
                        construction += manholeCost; accessory += manholeCost;
                        detail.put("人孔数量(个)", manholes);
                        detail.put("人孔费(元)", manholeCost);
                        int joints = Math.max(1, (int) (len / toDouble(tc.getOrDefault("joint_box_interval_m", 2000.0))));
                        double jointCost = round2(joints * toDouble(tc.getOrDefault("joint_box_yuan_per_unit", 200.0)));
                        material += jointCost; accessory += jointCost;
                        detail.put("接头盒数量(个)", joints);
                        detail.put("接头盒费(元)", jointCost);
                    }
                    case "架空" -> {
                        int poles = (int) (len / toDouble(tc.getOrDefault("pole_interval_m", 50.0))) + 1;
                        double poleCost = round2(poles * toDouble(tc.getOrDefault("pole_yuan_per_unit", 1500.0)));
                        material += poleCost; accessory += poleCost;
                        detail.put("电杆数量(根)", poles);
                        detail.put("电杆费(元)", poleCost);
                        int guys = (int) (len / 1000.0 * toDouble(tc.getOrDefault("guy_wire_ratio_per_km", 0.3)));
                        double guyCost = round2(guys * toDouble(tc.getOrDefault("guy_wire_yuan_per_unit", 500.0)));
                        material += guyCost; accessory += guyCost;
                        detail.put("拉线数量(条)", guys);
                        detail.put("拉线费(元)", guyCost);
                        int joints = Math.max(1, (int) (len / toDouble(tc.getOrDefault("joint_box_interval_m", 2000.0))));
                        double jointCost = round2(joints * toDouble(tc.getOrDefault("joint_box_yuan_per_unit", 200.0)));
                        material += jointCost; accessory += jointCost;
                        detail.put("接头盒数量(个)", joints);
                        detail.put("接头盒费(元)", jointCost);
                    }
                    default -> {
                        // 无分项配置的类型（如"桥架"）：保持综合单价口径 + 接头盒
                        double compCost = round2(toDouble(constructionPrices.getOrDefault(ptKey,
                                constructionPrices.getOrDefault("default", 50.0))) * len);
                        construction += compCost;
                        detail.put("施工综合费(元)", compCost);
                        int joints = Math.max(1, (int) (len / 2000.0));
                        double jointCost = round2(joints * 200.0);
                        material += jointCost; accessory += jointCost;
                        detail.put("接头盒数量(个)", joints);
                        detail.put("接头盒费(元)", jointCost);
                    }
                }
            }

            material     = round2(material);
            construction = round2(construction);
            accessory    = round2(accessory);
            double directCost = round2(material + construction);

            Map<String, Object> row = new LinkedHashMap<>();
            row.put("idx", ++idx);
            row.put("pipelineId",  String.valueOf(pl.getOrDefault("pipelineId", "PL-" + idx)));
            row.put("startSite",   pl.getOrDefault("startSite", ""));
            row.put("endSite",     pl.getOrDefault("endSite", ""));
            row.put("pipelineType", ptKey + (ptKey.equals(pt) ? "" : "（原:" + (pt.isBlank() ? "空" : pt) + "→回退）"));
            row.put("fiberType",    fibKey + (fibKey.equals(fib) ? "" : "（原:" + (fib.isBlank() ? "空" : fib) + "→回退）"));
            row.put("lengthM",      len);
            row.put("materialCost",     material);
            row.put("constructionCost", construction);
            // 附属物小计（标石/接头盒/电杆/拉线/人孔），已含在材料费/施工费内，仅供报表展示
            row.put("auxiliaryCost",    accessory);
            row.put("accessoryCost",    accessory);
            row.put("directCost",       directCost);
            row.put("unitPriceFiber",   fiberYuanPerM);
            row.put("costDetail",       detail);
            row.put("priceTag",  "概算/示意");
            rows.add(row);

            sumMaterial     += material;
            sumConstruction += construction;
            sumAuxiliary    += accessory;
            sumLength       += len;
        }

        // 汇总（v1.1 对齐 QGIS：管理费/利润/税金均以直接费为基数，非级联）
        double directSubtotal = round2(sumMaterial + sumConstruction);
        double managementFee  = round2(directSubtotal * mgmtFeePct / 100.0);
        double profit         = round2(directSubtotal * profitPct / 100.0);
        double tax            = round2(directSubtotal * taxPct / 100.0);
        double totalCost      = round2(directSubtotal + managementFee + profit + tax);
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
        if (overrideEnabled) {
            summary.put("fiberPriceOverride", fiberPriceOverride);
            summary.put("priceOverrideNote", "光缆单价已按请求参数整体覆盖为 " + fiberPriceOverride + " 元/m（概算/示意）");
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("rows", rows);
        result.put("summary", summary);
        result.put("warning", "本造价为「概算 / 示意」级别，源自平台演示场景参数。不得作为行业基准单价；工程预算请用本地造价口径校准。");
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

    private double orDefault(Double v, Double d, double fallback) {
        if (v != null && v > 0) return v;
        if (d != null && d > 0) return d;
        return fallback;
    }

    private double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asStringObjectMap(Object o) {
        return o instanceof Map<?, ?> m ? (Map<String, Object>) m : Collections.emptyMap();
    }

    /**
     * 已知 key 解析：值非空、非"未知"、且在 known 集合内 → 原样返回；
     * 否则回退到 fallbackKey（"管道"/"G.652D"）。
     */
    private String resolveKnown(String raw, String fallbackKey, java.util.Set<String> knownKeys, String defaultKey) {
        if (raw == null || raw.isBlank() || "未知".equals(raw)) return fallbackKey;
        if (knownKeys.contains(raw)) return raw;
        // 业务键未知 → 回退（保证 UI 看到"管道"而不是"宇宙传输"）
        return fallbackKey;
    }
}
