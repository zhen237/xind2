package com.comm.m03.s3.client;

import lombok.Data;

import java.util.Map;

/**
 * S3 审查任务状态查询响应体，对应 GET /api/v1/s3/review/task/{id}。
 */
@Data
public class S3ReviewTaskResponse {

    /** 状态码 */
    private Integer code;

    /** 说明 */
    private String message;

    /** 任务数据 */
    private Map<String, Object> data;
}
