package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("m04_acceptance_task")
public class AcceptanceTask {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long projectId;
    private String taskName;
    private String taskType;
    private Integer status;
    private String acceptanceStandard;
    private String resultDescription;
    private Integer problemCount;
    private Long acceptanceBy;
    private LocalDateTime acceptanceTime;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}