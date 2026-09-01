package com.comm.s3.entity;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * S1 图纸设计数据永久落库实体（B-1 MySQL 持久层）。
 * 主键为 S1 图纸标识 designTaskId；完整设计数据以 JSON 形式存放在 designDataJson 列。
 */
@Data
@TableName("s3_design_data")
public class S3DesignData {

    /** S1 图纸标识（主键，对应 S1DesignDataDTO.designTaskId） */
    @TableId
    private String designTaskId;

    /** S1 传入完整 designData JSON（缓存 wrapper：{"design_data": {...}}） */
    private String designDataJson;

    /** 工程元信息 JSON（projectName/region/designType/deviceCount/layerCounts） */
    private String projectMetaJson;

    /** 首次创建该图纸的审查任务 ID（审计用） */
    private Long taskId;

    /** 创建时间 */
    private LocalDateTime createTime;
}
