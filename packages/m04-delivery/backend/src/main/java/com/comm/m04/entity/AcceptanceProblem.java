package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("m04_acceptance_problem")
public class AcceptanceProblem {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long taskId;
    private String problemTitle;
    private Integer problemLevel;
    private String problemDescription;
    private String photoPath;
    private Integer status;
    private LocalDate rectifyDeadline;
    private String rectifyResult;
    private Long rectifyBy;
    private Long reviewBy;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}