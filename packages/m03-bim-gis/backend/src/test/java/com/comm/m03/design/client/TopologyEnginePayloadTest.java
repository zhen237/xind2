package com.comm.m03.design.client;

import com.comm.m03.design.entity.GenerateRequest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 纯单元测试：{@link TopologyEngineClient#buildPayload(GenerateRequest)} 的 snake_case 请求体构造。
 *
 * <p>背景（真实事故）：paramsJson 里 key 写错成 {@code band}（实体字段是 {@code frequencyBand}）
 * → {@code frequency_band} 为 null → 引擎 Pydantic 显式 null 覆盖默认值 →
 * {@code freq_map.get(frequency_band.lower(), 2000)} 抛
 * {@code AttributeError: 'NoneType' object has no attribute 'lower'} → HTTP 500。</p>
 *
 * <p>本测试锁定：buildPayload 仅在字段非空时才下发对应 key，
 * 杜绝显式 null 覆盖引擎默认值。</p>
 */
class TopologyEnginePayloadTest {

    /** 基础请求：仅填必填项，其余保持 null。 */
    private static GenerateRequest baseRequest() {
        GenerateRequest req = new GenerateRequest();
        req.setProjectId(1001L);
        req.setSchemeName("摩洛哥-6站点方案");
        req.setCenterLongitude(new BigDecimal("-8.5359125"));
        req.setCenterLatitude(new BigDecimal("33.2134738"));
        req.setCoverageRadius(new BigDecimal("1000"));
        req.setFrequencyBand("fdd-lte-1800");
        return req;
    }

    private static TopologyEngineClient newClient() {
        // 构造器只需 baseUrl/timeout，本测试不发起网络请求
        return new TopologyEngineClient("http://localhost:9001", 5000);
    }

    @Test
    @DisplayName("frequencyBand 为 null：payload 不含 frequency_band 键（不得下发显式 null）")
    void omitsFrequencyBandWhenNull() {
        GenerateRequest req = baseRequest();
        req.setFrequencyBand(null);

        Map<String, Object> payload = newClient().buildPayload(req);

        assertFalse(payload.containsKey("frequency_band"),
                "frequencyBand 为 null 时不得下发 frequency_band，否则会覆盖引擎默认值并触发 500");
        assertTrue(payload.containsKey("project_id"), "project_id 必然有值，应始终下发");
    }

    @Test
    @DisplayName("frequencyBand 有值：payload 含 frequency_band 且值相等")
    void includesFrequencyBandWhenPresent() {
        GenerateRequest req = baseRequest();
        req.setFrequencyBand("fdd-lte-1800");

        Map<String, Object> payload = newClient().buildPayload(req);

        assertTrue(payload.containsKey("frequency_band"), "有值时须下发 frequency_band");
        assertEquals("fdd-lte-1800", payload.get("frequency_band"));
    }

    @Test
    @DisplayName("centerLongitude 为 null：不含 center_longitude；仍只放 center_latitude")
    void omitsCenterLongitudeWhenNull() {
        GenerateRequest req = baseRequest();
        req.setCenterLongitude(null);
        req.setCenterLatitude(new BigDecimal("33.2134738"));

        Map<String, Object> payload = newClient().buildPayload(req);

        assertFalse(payload.containsKey("center_longitude"), "centerLongitude 为 null 时不得下发");
        assertTrue(payload.containsKey("center_latitude"), "centerLatitude 有值时应下发");
        assertEquals(33.2134738, payload.get("center_latitude"));
    }

    @Test
    @DisplayName("schemeName 为 null 或空白：不含 scheme_name；有值则含")
    void omitsSchemeNameWhenNullOrBlank() {
        TopologyEngineClient client = newClient();

        GenerateRequest nullName = baseRequest();
        nullName.setSchemeName(null);
        assertFalse(client.buildPayload(nullName).containsKey("scheme_name"),
                "schemeName 为 null 时不得下发 scheme_name");

        GenerateRequest blankName = baseRequest();
        blankName.setSchemeName("   ");
        assertFalse(client.buildPayload(blankName).containsKey("scheme_name"),
                "schemeName 为空白时不得下发 scheme_name");

        GenerateRequest okName = baseRequest();
        okName.setSchemeName("摩洛哥-6站点方案");
        assertTrue(client.buildPayload(okName).containsKey("scheme_name"),
                "schemeName 有值时应下发 scheme_name");
        assertEquals("摩洛哥-6站点方案", client.buildPayload(okName).get("scheme_name"));
    }
}
