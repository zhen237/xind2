package com.comm.s2.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("s2_fusion_task")
public class FusionTask {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String taskName;

    private Long projectId;

    private Long sourceFileId;

    private String sourceEpsg;

    private String targetEpsg;

    private String transformationType;

    private Integer status;

    private String resultFilePath;

    private Integer featureCount;

    private String errorMessage;

    private Long createdBy;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
