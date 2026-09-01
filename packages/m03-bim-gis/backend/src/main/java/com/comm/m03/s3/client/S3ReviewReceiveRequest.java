package com.comm.m03.s3.client;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * S3 智能审查接收接口请求体，对应 POST /api/v1/s3/review/s1/receive。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class S3ReviewReceiveRequest {

    /** 设计任务唯一 ID（建议使用 S1 自身 taskNo 或格式化字符串） */
    private String designTaskId;

    /** 设计任务名称 */
    private String designTaskName;

    /** 设计类型，如 communication / ftth / macro / mixed */
    private String designType;

    /** 设备/线缆数组 */
    private List<S3ReviewDevice> devices;

    /** 管线埋深数组（GD-001 用），可选 */
    private List<S3ReviewPipeline> pipeline;

    /** 其他扩展参数，原样透传 */
    private Map<String, Object> extraData;
}
