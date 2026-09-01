package com.comm.s3.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * S1 数据接收接口响应体。
 * 响应字段严格遵循约定：code / message / reviewTaskId / status，
 * 不修改原有返回字段结构（与 S3 其他接口保持 code、message 字段一致）。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class S1ReceiveResponse {
    /** 业务状态码：200=接收成功并已启动审查；400=参数校验失败（任务已记为 FAILED） */
    private Integer code;
    /** 说明信息（成功或失败原因） */
    private String message;
    /** 审查任务 ID */
    private Long reviewTaskId;
    /** 任务状态：PENDING / PROCESSING / COMPLETED / FAILED */
    private String status;
}
