package com.comm.m03.design.controller;

import com.comm.m03.design.client.LlmServiceClient;
import com.comm.m03.design.entity.LlmParseRequest;
import com.comm.m03.design.entity.LlmParseResponse;
import com.comm.m03.design.entity.LlmReportRequest;
import com.comm.m03.design.entity.LlmReportResponse;
import com.comm.common.Result;
import com.comm.m03.rate_limit.RateLimit;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/m03/llm")
public class LlmController {

    @Autowired
    private LlmServiceClient llmServiceClient;

    /**
     * ① 自然语言 -> 结构化设计参数。
     * 鉴权：/api/m03/llm/** 未列入 security.permit-paths，由 SecurityAutoConfiguration
     * 强制 JWT 鉴权，前端/插件须持用户 Token 调用；LLM Key 不离开同机 llm-service。
     */
    @PostMapping("/parse-design-params")
    @RateLimit(permitsPerSecond = 2.0)
    public Result<LlmParseResponse> parseDesignParams(@Valid @RequestBody LlmParseRequest request) {
        LlmParseResponse resp = llmServiceClient.parseDesignParams(request);
        if (resp == null) {
            return Result.error(503, "大模型服务暂不可用，请稍后重试");
        }
        return Result.success("解析成功", resp);
    }

    /**
     * ② 设计方案 -> Markdown 评审/交付报告。
     */
    @PostMapping("/generate-report")
    @RateLimit(permitsPerSecond = 2.0)
    public Result<LlmReportResponse> generateReport(@Valid @RequestBody LlmReportRequest request) {
        LlmReportResponse resp = llmServiceClient.generateReport(request);
        if (resp == null) {
            return Result.error(503, "大模型服务暂不可用，请稍后重试");
        }
        return Result.success("生成成功", resp);
    }
}
