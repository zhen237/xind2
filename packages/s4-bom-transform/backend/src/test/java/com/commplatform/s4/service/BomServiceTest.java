package com.commplatform.s4.service;

import com.commplatform.s4.config.S4Config;
import com.commplatform.s4.entity.BomTask;
import com.commplatform.s4.exception.S4BusinessException;
import com.commplatform.s4.exception.S4ErrorCode;
import com.commplatform.s4.mapper.BomItemMapper;
import com.commplatform.s4.mapper.BomTaskMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * BomService 单元测试 — 验证 BOM 生成入口的业务规则与导出校验。
 */
@ExtendWith(MockitoExtension.class)
class BomServiceTest {

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

    private S4Config s4Config;
    private BomService bomService;

    @BeforeEach
    void setUp() {
        s4Config = new S4Config();
        bomService = new BomService(bomTaskMapper, bomItemMapper,
                bomAsyncExecutor, s1S3DataService, s4Config, restTemplate);
    }

    // ── 入参校验 ──

    @Test
    @DisplayName("generate: designTaskId 为空 → INVALID_PARAM")
    void generateBlankDesignTaskId() {
        S4BusinessException e = assertThrows(S4BusinessException.class,
                () -> bomService.generate(null, "P-001"));
        assertEquals(S4ErrorCode.INVALID_PARAM, e.getErrorCode());
    }

    @Test
    @DisplayName("generate: designTaskId 含非法字符（路径穿越尝试）→ INVALID_PARAM")
    void generateInvalidDesignTaskId() {
        S4BusinessException e = assertThrows(S4BusinessException.class,
                () -> bomService.generate("../../etc/passwd", "P-001"));
        assertEquals(S4ErrorCode.INVALID_PARAM, e.getErrorCode());
    }

    // ── 审查闸门 ──

    @Test
    @DisplayName("generate: 分级闸门 blocked → REVIEW_BLOCKED")
    void generateBlockedByGate() {
        when(s1S3DataService.checkGate("D-BLOCK")).thenReturn(Map.of(
                "decision", "blocked",
                "counts", Map.of("critical", 1, "error", 0, "warning", 0, "pending", 0),
                "blockers", List.of(Map.of(
                        "severity", "critical", "ruleId", "GD-001", "ruleName", "接地电阻超标"))
        ));
        S4BusinessException e = assertThrows(S4BusinessException.class,
                () -> bomService.generate("D-BLOCK", "P-001"));
        assertEquals(S4ErrorCode.REVIEW_BLOCKED, e.getErrorCode());
        assertTrue(e.getMessage().contains("GD-001"));
        verify(bomTaskMapper, never()).insert(any(BomTask.class));
    }

    // ── 正常生成 ──

    @Test
    @DisplayName("generate: 闸门放行 → 创建任务并触发异步执行")
    void generateHappyPath() {
        when(s1S3DataService.checkGate("D-OK")).thenReturn(Map.of(
                "decision", "allowed",
                "counts", Map.of("critical", 0, "error", 0, "warning", 0, "pending", 0)
        ));
        when(bomTaskMapper.insert(any(BomTask.class))).thenReturn(1);

        String taskId = bomService.generate("D-OK", "P-001");

        assertNotNull(taskId);
        assertTrue(taskId.matches("^[0-9a-f-]{36}$"), "taskId 应为 UUID 格式");

        ArgumentCaptor<BomTask> captor = ArgumentCaptor.forClass(BomTask.class);
        verify(bomTaskMapper).insert(captor.capture());
        assertEquals("D-OK", captor.getValue().getDesignTaskId());
        assertEquals("running", captor.getValue().getStatus());

        verify(bomAsyncExecutor).executeGenerateAsync(taskId, "D-OK", "P-001");
    }

    // ── 导出校验 ──

    @Test
    @DisplayName("export: taskId 非法格式 → INVALID_PARAM（不触达引擎）")
    void exportInvalidTaskId() {
        S4BusinessException e = assertThrows(S4BusinessException.class,
                () -> bomService.exportExcel("..%2F..%2Fetc"));
        assertEquals(S4ErrorCode.INVALID_PARAM, e.getErrorCode());
        verifyNoInteractions(restTemplate);
    }

    @Test
    @DisplayName("export: 任务不存在 → TASK_NOT_FOUND")
    void exportTaskNotFound() {
        when(bomTaskMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());
        S4BusinessException e = assertThrows(S4BusinessException.class,
                () -> bomService.exportExcel("task-x-404"));
        assertEquals(S4ErrorCode.TASK_NOT_FOUND, e.getErrorCode());
    }

    @Test
    @DisplayName("export: 任务未完成（running）→ EXPORT_NOT_READY")
    void exportNotReady() {
        BomTask running = new BomTask();
        running.setTaskId("task-running");
        running.setStatus("running");
        when(bomTaskMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(running));

        S4BusinessException e = assertThrows(S4BusinessException.class,
                () -> bomService.exportExcel("task-running"));
        assertEquals(S4ErrorCode.EXPORT_NOT_READY, e.getErrorCode());
        verifyNoInteractions(restTemplate);
    }

    @Test
    @DisplayName("export: 任务完成 → 从引擎拉取字节流并以 attachment 返回")
    void exportHappyPath() {
        BomTask done = new BomTask();
        done.setTaskId("task-done-1");
        done.setStatus("done");
        when(bomTaskMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(done));
        when(restTemplate.getForObject(anyString(), eq(byte[].class))).thenReturn(new byte[]{1, 2, 3, 4});

        var resp = bomService.exportExcel("task-done-1");

        assertEquals(200, resp.getStatusCode().value());
        assertNotNull(resp.getBody());
        assertEquals(4, resp.getBody().length);
        assertEquals("attachment", resp.getHeaders().getContentDisposition().getType());
        assertTrue(resp.getHeaders().getContentDisposition().getFilename().contains("task-done-1"));
    }

    // ── 查询校验 ──

    @Test
    @DisplayName("status: 任务不存在 → 返回 not_found（不抛异常，供前端轮询）")
    void statusNotFound() {
        when(bomTaskMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());
        Map<String, Object> result = bomService.getStatus("task-missing");
        assertEquals("not_found", result.get("status"));
    }

    @Test
    @DisplayName("history: 分页参数非法 → INVALID_PARAM")
    void historyInvalidPaging() {
        S4BusinessException e = assertThrows(S4BusinessException.class,
                () -> bomService.listHistory(0, 20));
        assertEquals(S4ErrorCode.INVALID_PARAM, e.getErrorCode());
    }
}
