package com.comm.m03.design.service;

import com.comm.m03.design.entity.DesignData;
import com.comm.m03.design.entity.DesignScheme;
import com.comm.m03.design.entity.DesignTask;
import com.comm.m03.design.mapper.DesignSchemeMapper;
import com.comm.m03.design.mapper.DesignTaskMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 纯单元测试：S1(m03) 管线工程量（{@code pipelines}）随设计成果「单独落库 + /result 合并回」。
 * 无需 Spring 容器、无需数据库：mapper 用 Mockito 桩，objectMapper 用真实实例（反射注入）。
 *
 * <p>契约背景（挑战杯 S1→S4 链路）：
 * <ul>
 *   <li>QGIS 上传 body 顶层新增 {@code pipelines}（Pipeline.to_dict() 数组）；</li>
 *   <li>{@code saveDesignScheme} 把 pipelines 序列化写入 {@code m03_design_scheme.pipeline_json}；</li>
 *   <li>{@code GET /tasks/{id}/result} 由 {@code buildTaskResultPayload} 按任务 task_no
 *       从 pipeline_json 读回并合并进 {@code result.pipelines}，供 S4 生成 BOM。</li>
 * </ul>
 * 这些断言在未实现上述逻辑前必然失败（编译期缺字段 / 运行期 pipelines 为 null），锁定行为不回退。
 */
class PipelinePersistenceTest {

    /** 构造一个仅注入 objectMapper 的被测实例（其余依赖保持 null，交由具体用例按需注入桩）。 */
    private static DesignService newServiceWithMapper() {
        DesignService service = new DesignService();
        inject(service, "objectMapper", new ObjectMapper());
        return service;
    }

    private static void inject(Object target, String fieldName, Object value) {
        try {
            Field field = DesignService.class.getDeclaredField(fieldName);
            field.setAccessible(true);
            field.set(target, value);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("无法向 DesignService 注入字段: " + fieldName, e);
        }
    }

    /** 一条贴近真实的管线：Pipeline.to_dict() 结构（snake_case 键 + 坐标数组）。 */
    private static Map<String, Object> samplePipeline(String pipelineId) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("pipeline_id", pipelineId);
        p.put("pipeline_type", "trunk");
        p.put("fiber_type", "G.652D");
        p.put("length_m", 123.45);
        p.put("from_room", "ROOM-A");
        p.put("to_room", "ROOM-B");
        p.put("coordinates", List.of(
                List.of(-8.5359125, 33.2134738),
                List.of(-8.5265861, 33.2269873)));
        return p;
    }

    private static DesignData sampleDesignData(List<Map<String, Object>> pipelines) {
        DesignData data = new DesignData();
        data.setProjectId(null); // 置空以跳过 Project 自动创建分支
        data.setSchemeName("管线落库测试");
        data.setFrequencyBand("3.5GHz");
        data.setTotalSites(2);
        data.setValidSites(2);
        data.setInvalidSites(0);
        data.setPipelines(pipelines);
        return data;
    }

    // ─────────────────────────── 序列化/反序列化 往返 ───────────────────────────

    @Test
    @DisplayName("pipelines → serializePipelines → parsePipelines 往返得到同一列表（字段保真）")
    void pipelinesRoundTripIsLossless() {
        DesignService service = newServiceWithMapper();
        List<Map<String, Object>> original = new ArrayList<>();
        original.add(samplePipeline("PL-001"));
        original.add(samplePipeline("PL-002"));

        String json = service.serializePipelines(original);
        assertNotNull(json, "非空 pipelines 必须序列化出 JSON");
        assertTrue(json.contains("PL-001"), "JSON 应包含第一条管线");

        List<Map<String, Object>> parsed = service.parsePipelines(json);
        assertNotNull(parsed, "合法 JSON 必须解析出列表");
        assertEquals(2, parsed.size(), "往返后管线条数不变");
        assertEquals("PL-001", parsed.get(0).get("pipeline_id"), "pipeline_id 保真");
        assertEquals("trunk", parsed.get(0).get("pipeline_type"), "pipeline_type 保真");
        assertEquals("G.652D", parsed.get(0).get("fiber_type"), "fiber_type 保真");
        assertEquals(123.45, ((Number) parsed.get(0).get("length_m")).doubleValue(), 1e-9,
                "length_m 数值保真");
        Object coords = parsed.get(0).get("coordinates");
        assertTrue(coords instanceof List, "coordinates 应为数组");
        assertEquals(2, ((List<?>) coords).size(), "coordinates 顶点数保真");
    }

    @Test
    @DisplayName("边界：serializePipelines(null)=null；parsePipelines(null/空白/非法)=null 且不抛异常")
    void nullAndInvalidInputsAreSafe() {
        DesignService service = newServiceWithMapper();

        assertNull(service.serializePipelines(null), "null 入参不落库（返回 null）");
        assertNull(service.parsePipelines(null), "null 输入返回 null");
        assertNull(service.parsePipelines("   "), "空白输入返回 null");
        assertNull(service.parsePipelines("not json"), "非法 JSON 返回 null 且不抛异常");
    }

    // ─────────────────────────── 落库：saveDesignScheme ───────────────────────────

    @Test
    @DisplayName("saveDesignScheme：带 pipelines 时插入的 DesignScheme.pipelineJson 可解析回原列表")
    void saveDesignSchemePersistsPipelines() {
        DesignService service = newServiceWithMapper();
        DesignSchemeMapper mapper = mock(DesignSchemeMapper.class);
        inject(service, "designSchemeMapper", mapper);

        List<Map<String, Object>> pipelines = new ArrayList<>();
        pipelines.add(samplePipeline("PL-100"));
        DesignData data = sampleDesignData(pipelines);

        service.saveDesignScheme(data);

        ArgumentCaptor<DesignScheme> captor = ArgumentCaptor.forClass(DesignScheme.class);
        verify(mapper).insert(captor.capture());
        DesignScheme inserted = captor.getValue();

        assertNotNull(inserted.getPipelineJson(), "insert 前必须写入 pipelineJson（管线单独落库）");
        assertEquals("管线落库测试", inserted.getSchemeName(), "既有列不得被破坏");

        List<Map<String, Object>> roundTrip = service.parsePipelines(inserted.getPipelineJson());
        assertNotNull(roundTrip, "落库 JSON 必须可解析");
        assertEquals(1, roundTrip.size(), "落库管线条数正确");
        assertEquals("PL-100", roundTrip.get(0).get("pipeline_id"), "落库管线内容正确");
    }

    @Test
    @DisplayName("saveDesignScheme：pipelines=null 时 pipelineJson 保持 null（不写空串）")
    void saveDesignSchemeWithoutPipelinesLeavesNull() {
        DesignService service = newServiceWithMapper();
        DesignSchemeMapper mapper = mock(DesignSchemeMapper.class);
        inject(service, "designSchemeMapper", mapper);

        service.saveDesignScheme(sampleDesignData(null));

        ArgumentCaptor<DesignScheme> captor = ArgumentCaptor.forClass(DesignScheme.class);
        verify(mapper).insert(captor.capture());
        assertNull(captor.getValue().getPipelineJson(), "无管线时不得写入 pipelineJson");
    }

    // ─────────────────────────── 读回合并：/result ───────────────────────────

    @Test
    @DisplayName("buildTaskResultPayload：按 task_no 从 pipeline_json 读回并合并进 result.pipelines")
    void taskResultMergesPipelinesByTaskNo() throws Exception {
        DesignService service = newServiceWithMapper();
        ObjectMapper om = new ObjectMapper();

        DesignTaskMapper taskMapper = mock(DesignTaskMapper.class);
        DesignSchemeMapper schemeMapper = mock(DesignSchemeMapper.class);
        inject(service, "taskMapper", taskMapper);
        inject(service, "designSchemeMapper", schemeMapper);

        // 任务成果（resultJson 里不含管线，模拟既有行为）
        DesignData resultData = sampleDesignData(null);
        DesignTask task = new DesignTask();
        task.setId(5L);
        task.setTaskNo("DT-ABC123");
        task.setTaskName("任务成果");
        task.setResultJson(om.writeValueAsString(resultData));
        when(taskMapper.selectById(5L)).thenReturn(task);

        // 方案表里存着管线（task_no 关联）
        DesignScheme scheme = new DesignScheme();
        scheme.setId(77L);
        scheme.setTaskNo("DT-ABC123");
        scheme.setPipelineJson(om.writeValueAsString(List.of(samplePipeline("PL-200"))));
        when(schemeMapper.selectOne(any())).thenReturn(scheme);

        Map<String, Object> payload = service.getTaskResult(5L);

        Object result = payload.get("result");
        assertNotNull(result, "resultJson 非空时 result 必须被解析");
        assertTrue(result instanceof DesignData, "result 应为 DesignData");
        List<Map<String, Object>> merged = ((DesignData) result).getPipelines();
        assertNotNull(merged, "result.pipelines 必须由 pipeline_json 合并而来");
        assertEquals(1, merged.size(), "合并管线条数正确");
        assertEquals("PL-200", merged.get(0).get("pipeline_id"), "合并管线内容正确");
        // 既有字段未被破坏
        assertEquals("DT-ABC123", payload.get("taskNo"), "既有 taskNo 字段保持");
    }

    @Test
    @DisplayName("taskNo 为空/空白：不查方案表，result.pipelines 保持 null")
    void blankTaskNoSkipsLookup() throws Exception {
        DesignService service = newServiceWithMapper();
        ObjectMapper om = new ObjectMapper();

        DesignTaskMapper taskMapper = mock(DesignTaskMapper.class);
        DesignSchemeMapper schemeMapper = mock(DesignSchemeMapper.class);
        inject(service, "taskMapper", taskMapper);
        inject(service, "designSchemeMapper", schemeMapper);

        DesignTask task = new DesignTask();
        task.setId(6L);
        task.setTaskNo("  "); // 空白 -> 应跳过查库
        task.setResultJson(om.writeValueAsString(sampleDesignData(null)));
        when(taskMapper.selectById(6L)).thenReturn(task);

        Map<String, Object> payload = service.getTaskResult(6L);

        assertNotNull(payload.get("result"), "result 仍应被解析");
        assertNull(((DesignData) payload.get("result")).getPipelines(), "无 taskNo 时 pipelines 应保持 null");
        verify(schemeMapper, never()).selectOne(any());
    }

    @Test
    @DisplayName("方案存在但 pipeline_json 空白：pipelines 保持 null（不抛异常）")
    void blankPipelineJsonYieldsNullPipelines() throws Exception {
        DesignService service = newServiceWithMapper();
        ObjectMapper om = new ObjectMapper();

        DesignTaskMapper taskMapper = mock(DesignTaskMapper.class);
        DesignSchemeMapper schemeMapper = mock(DesignSchemeMapper.class);
        inject(service, "taskMapper", taskMapper);
        inject(service, "designSchemeMapper", schemeMapper);

        DesignTask task = new DesignTask();
        task.setId(7L);
        task.setTaskNo("DT-NOPIPE");
        task.setResultJson(om.writeValueAsString(sampleDesignData(null)));
        when(taskMapper.selectById(7L)).thenReturn(task);

        DesignScheme scheme = new DesignScheme();
        scheme.setTaskNo("DT-NOPIPE");
        scheme.setPipelineJson(null); // 历史行：无管线
        when(schemeMapper.selectOne(any())).thenReturn(scheme);

        Map<String, Object> payload = service.getTaskResult(7L);

        assertNull(((DesignData) payload.get("result")).getPipelines(), "空白 pipeline_json 应得 null");
    }

    // ─────────────────────── 回退：task_no 未命中 → 按 projectId ───────────────────────

    @Test
    @DisplayName("回退：task_no 查不到时，按 projectId 取「带管线的最新方案」并合并进 result.pipelines")
    void taskResultFallsBackToProjectIdWhenTaskNoMisses() throws Exception {
        DesignService service = newServiceWithMapper();
        ObjectMapper om = new ObjectMapper();

        DesignTaskMapper taskMapper = mock(DesignTaskMapper.class);
        DesignSchemeMapper schemeMapper = mock(DesignSchemeMapper.class);
        inject(service, "taskMapper", taskMapper);
        inject(service, "designSchemeMapper", schemeMapper);

        DesignTask task = new DesignTask();
        task.setId(8L);
        task.setTaskNo("DT-NOT-IN-SCHEME"); // scheme 里没有该 task_no
        task.setProjectId(42L);
        task.setResultJson(om.writeValueAsString(sampleDesignData(null)));
        when(taskMapper.selectById(8L)).thenReturn(task);

        // 第一次（task_no）查不到 -> null；第二次（project_id 回退）命中带管线方案
        DesignScheme projectScheme = new DesignScheme();
        projectScheme.setId(101L);
        projectScheme.setProjectId(42L);
        projectScheme.setPipelineJson(om.writeValueAsString(List.of(samplePipeline("PL-300"))));
        when(schemeMapper.selectOne(any())).thenReturn(null, projectScheme);

        Map<String, Object> payload = service.getTaskResult(8L);

        List<Map<String, Object>> merged = ((DesignData) payload.get("result")).getPipelines();
        assertNotNull(merged, "task_no 未命中时必须按 projectId 回退并合并管线");
        assertEquals(1, merged.size(), "回退合并管线条数正确");
        assertEquals("PL-300", merged.get(0).get("pipeline_id"), "回退合并管线内容正确");
        verify(schemeMapper, times(2)).selectOne(any());
    }

    @Test
    @DisplayName("回退边界：task_no 未命中且 projectId 为 null → pipelines 保持 null，且不回退查库")
    void projectIdNullSkipsFallback() throws Exception {
        DesignService service = newServiceWithMapper();
        ObjectMapper om = new ObjectMapper();

        DesignTaskMapper taskMapper = mock(DesignTaskMapper.class);
        DesignSchemeMapper schemeMapper = mock(DesignSchemeMapper.class);
        inject(service, "taskMapper", taskMapper);
        inject(service, "designSchemeMapper", schemeMapper);

        DesignTask task = new DesignTask();
        task.setId(9L);
        task.setTaskNo("DT-NO-PROJECT");
        task.setProjectId(null); // 无项目 -> 回退必须跳过（不查库）
        task.setResultJson(om.writeValueAsString(sampleDesignData(null)));
        when(taskMapper.selectById(9L)).thenReturn(task);
        when(schemeMapper.selectOne(any())).thenReturn(null);

        Map<String, Object> payload = service.getTaskResult(9L);

        assertNull(((DesignData) payload.get("result")).getPipelines(), "projectId 为 null 时 pipelines 应为 null");
        verify(schemeMapper, times(1)).selectOne(any()); // 仅 task_no 查一次
    }

    @Test
    @DisplayName("回退边界：projectId 下无带管线方案 → pipelines 保持 null（不报错）")
    void projectIdWithoutPipelinesYieldsNull() throws Exception {
        DesignService service = newServiceWithMapper();
        ObjectMapper om = new ObjectMapper();

        DesignTaskMapper taskMapper = mock(DesignTaskMapper.class);
        DesignSchemeMapper schemeMapper = mock(DesignSchemeMapper.class);
        inject(service, "taskMapper", taskMapper);
        inject(service, "designSchemeMapper", schemeMapper);

        DesignTask task = new DesignTask();
        task.setId(10L);
        task.setTaskNo("DT-EMPTY-PROJECT");
        task.setProjectId(77L);
        task.setResultJson(om.writeValueAsString(sampleDesignData(null)));
        when(taskMapper.selectById(10L)).thenReturn(task);
        when(schemeMapper.selectOne(any())).thenReturn(null, null); // 两段都查不到

        Map<String, Object> payload = service.getTaskResult(10L);

        assertNull(((DesignData) payload.get("result")).getPipelines(), "无带管线方案时 pipelines 应保持 null");
        verify(schemeMapper, times(2)).selectOne(any());
    }
}
