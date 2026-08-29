package com.comm.m03.s3.client;

import lombok.Data;

/**
 * S3 智能审查接收接口响应体。
 */
@Data
public class S3ReviewReceiveResponse {

    /** 状态码，200 表示接收成功 */
    private Integer code;

    /** 说明 */
    private String message;

    /** 审查任务 ID */
    private Long reviewTaskId;

    /** 任务状态 */
    private String status;
}
