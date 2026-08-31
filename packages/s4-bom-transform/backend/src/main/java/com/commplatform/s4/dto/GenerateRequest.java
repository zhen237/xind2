package com.commplatform.s4.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * POST /api/s4/bom/generate 请求体。
 * <p>designTaskId 必填（S1 设计任务 ID），projectId 可选。</p>
 */
@Data
public class GenerateRequest {

    /** 关联 S1 设计任务 ID（必填） */
    @NotBlank(message = "designTaskId 不能为空")
    @Size(max = 64, message = "designTaskId 长度不能超过 64")
    private String designTaskId;

    /** 项目 ID（可选） */
    @Size(max = 64, message = "projectId 长度不能超过 64")
    private String projectId;
}
