package com.comm.s3.service;

import com.comm.s3.entity.S3ReviewTask;
import com.comm.s3.util.OkHttpUtil;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

/**
 * S3 → S4 下游集成：将审查任务转发到 S4（施工指令 / BOM 生成）。
 * <p>
 * 设计要点（方案 A：后端转发，避免前端跨域与鉴权不一致）：
 * 1. S3 后端持有 S4 后端地址（{@code s3.integration.s4-url}）；
 * 2. 以 reviewTaskId 反查 designTaskId，调用 S4 的 {@code POST /api/s4/bom/generate}；
 * 3. S4 后端自行拉取 S1 设计数据 + S3 审查结果生成 BOM，返回其 taskId；
 * 4. 本服务返回 S4 的 taskId 与可跳转的详情链接，供前端打开 S4 查看。
 * </p>
 */
@Slf4j
@Service
public class S4IntegrationService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private S3ReviewTaskService s3ReviewTaskService;

    @Value("${s3.integration.s4-url}")
    private String s4Url;

    @Value("${s3.integration.s4-frontend-url}")
    private String s4FrontendUrl;

    public Map<String, Object> forwardToS4(Long reviewTaskId) {
        S3ReviewTask task = s3ReviewTaskService.getById(reviewTaskId);
        if (task == null) {
            throw new RuntimeException("S3 审查任务不存在: id=" + reviewTaskId);
        }
        String designTaskId = task.getDesignTaskId();
        // S3ReviewTask 无 projectId 字段，构造可追溯的默认工程编号
        String projectId = "S3-Review-" + reviewTaskId;

        Map<String, String> body = new HashMap<>();
        body.put("designTaskId", designTaskId);
        body.put("projectId", projectId);

        String url = s4Url + "/api/s4/bom/generate";
        log.info("[S4转发] 提交S4生成BOM: reviewTaskId={}, designTaskId={}, url={}", reviewTaskId, designTaskId, url);

        String resp;
        try {
            resp = OkHttpUtil.postJson(url, objectMapper.writeValueAsString(body));
        } catch (RuntimeException e) {
            // OkHttpUtil 在非 2xx / 网络异常时抛 RuntimeException，message 已包含 S4 真实响应体（如审查闸门拦截原因）
            log.error("[S4转发] 调用S4失败 reviewTaskId={}: {}", reviewTaskId, e.getMessage());
            throw new RuntimeException("调用S4生成BOM失败：" + e.getMessage(), e);
        } catch (Exception e) {
            throw new RuntimeException("序列化请求体失败：" + e.getMessage(), e);
        }

        String s4TaskId;
        try {
            JsonNode node = objectMapper.readTree(resp);
            s4TaskId = node.path("taskId").asText(null);
            if (s4TaskId == null || s4TaskId.isEmpty()) {
                throw new RuntimeException("S4 返回缺少 taskId，响应: " + resp);
            }
        } catch (RuntimeException re) {
            throw re;
        } catch (Exception e) {
            throw new RuntimeException("解析S4响应失败: " + e.getMessage() + "，响应: " + resp, e);
        }

        Map<String, Object> data = new HashMap<>();
        data.put("s4TaskId", s4TaskId);
        data.put("s4DetailUrl", s4FrontendUrl + "/#/detail/" + s4TaskId);
        data.put("designTaskId", designTaskId);
        log.info("[S4转发] 成功，S4 taskId={}, 详情地址={}", s4TaskId, data.get("s4DetailUrl"));
        return data;
    }
}
