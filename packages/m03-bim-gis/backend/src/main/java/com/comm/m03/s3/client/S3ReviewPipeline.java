package com.comm.m03.s3.client;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * S3 审查请求体中的管线埋深对象，对应 GD-001 等管线类规则。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class S3ReviewPipeline {

    /** 管线唯一 ID */
    private String pipeId;

    /** 管线名称 */
    private String pipeName;

    /** 管线语义类型，如 communication_cable / power_cable / pipeline */
    private String deviceType;

    /** 敷设方式，如 direct / pipe / duct / aerial */
    private String layingType;

    /** 场景，如 urban / suburban / rural */
    private String scenario;

    /** 埋深（m） */
    private BigDecimal burialDepth;

    /** 坐标 JSON 字符串 */
    private String coordinates;
}
