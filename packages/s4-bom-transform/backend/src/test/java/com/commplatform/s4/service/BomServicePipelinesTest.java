package com.commplatform.s4.service;

import com.commplatform.s4.config.S4Config;
import com.commplatform.s4.mapper.BomItemMapper;
import com.commplatform.s4.mapper.BomTaskMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestTemplate;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

/**
 * 验证 S1 成果里的管线工程量（result.pipelines）经 {@code normalizeDesignData}
 * 后透传到返回给前端的 design map 的 pipelines 键。
 *
 * <p>normalizeDesignData 为 private，这里通过 public 入口 {@link BomService#getDesignReview(String)}
 * 触发（mock 掉 {@link S1S3DataService#fetchTaskResult(String)} 注入含 pipelines 的 payload）。</p>
 */
@ExtendWith(MockitoExtension.class)
class BomServicePipelinesTest {

    @Mock
    private BomTaskMapper bomTaskMapper;
    @Mock
    private BomItemMapper bomItemMapper;
    @Mock
    private BomAsyncExecutor bomAsyncExecutor;
    @Mock
    private S1S3DataService s1S3DataService;
    @Mock
    private RestTemplate restTemplate;

    private BomService bomService;

    @BeforeEach
    void setUp() {
        S4Config s4Config = new S4Config();
        bomService = new BomService(bomTaskMapper, bomItemMapper,
                bomAsyncExecutor, s1S3DataService, s4Config, restTemplate);
    }

    /** 构造一个含 deviceLayout（确保 normalizeDesignData 不判为无成果）的任务主线 payload。 */
    private Map<String, Object> taskPayloadWithPipelines(Object pipelines, boolean includeKey) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("schemeName", "测试方案");
        result.put("deviceLayout", List.of(Map.of(
                "deviceName", "网络摄像机", "deviceType", "camera", "modelSpec", "IPC-200")));
        if (includeKey) {
            result.put("pipelines", pipelines);
        }

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("taskNo", "T-100");
        payload.put("projectId", "P-100");
        payload.put("taskName", "测试任务");
        payload.put("result", result);
        return payload;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> designOf(String designTaskId) {
        // S3 审查链路不 mock → 返回 null → review 走 fallback；design 非空故仍是真实规范化结果
        lenient().when(s1S3DataService.fetchReviewByDesign(org.mockito.ArgumentMatchers.anyString()))
                .thenReturn(null);
        Map<String, Object> resp = bomService.getDesignReview(designTaskId);
        return (Map<String, Object>) resp.get("design");
    }

    @Test
    @DisplayName("design.pipelines: payload 含 result.pipelines 数组 → 原样透传")
    void pipelinesPassedThrough() {
        List<Map<String, Object>> pipelines = List.of(
                Map.of("name", "主干管道", "length", 100, "unit", "m"),
                Map.of("name", "支线管道", "length", 40, "unit", "m"));
        when(s1S3DataService.fetchTaskResult("T-100"))
                .thenReturn(taskPayloadWithPipelines(pipelines, true));

        Map<String, Object> design = designOf("T-100");

        assertNotNull(design, "design 不应为空");
        Object got = design.get("pipelines");
        assertNotNull(got, "design 应包含 pipelines 键");
        assertTrue(got instanceof List, "pipelines 应为列表");
        assertSame(pipelines, got, "pipelines 应原样透传（同一引用）");
        assertEquals(2, ((List<?>) got).size());
        // 既有字段不受影响
        assertEquals("测试方案", design.get("projectName"));
        assertEquals(1, ((List<?>) design.get("devices")).size());
        assertEquals(1, design.get("deviceCount"));
    }

    @Test
    @DisplayName("design.pipelines: payload 无 result.pipelines 键 → 空列表")
    void pipelinesMissingKeyYieldsEmptyList() {
        when(s1S3DataService.fetchTaskResult("T-100"))
                .thenReturn(taskPayloadWithPipelines(null, false));

        Map<String, Object> design = designOf("T-100");

        assertNotNull(design.get("pipelines"), "pipelines 键应存在且非 null");
        assertTrue(design.get("pipelines") instanceof List, "pipelines 应为列表");
        assertTrue(((List<?>) design.get("pipelines")).isEmpty(), "缺失时应为空列表");
    }

    @Test
    @DisplayName("design.pipelines: payload 的 result.pipelines 为 null → 空列表")
    void pipelinesNullYieldsEmptyList() {
        when(s1S3DataService.fetchTaskResult("T-100"))
                .thenReturn(taskPayloadWithPipelines(null, true));

        Map<String, Object> design = designOf("T-100");

        assertNotNull(design.get("pipelines"), "pipelines 键应存在且非 null");
        assertTrue(design.get("pipelines") instanceof List, "pipelines 应为列表");
        assertTrue(((List<?>) design.get("pipelines")).isEmpty(), "null 时应为空列表");
    }
}
