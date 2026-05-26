package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("m04_project")
public class Project {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String projectName;
    private String projectCode;
    private String regionCode;
    private String currentPhase;
    private BigDecimal phaseProgress;
    private BigDecimal totalProgress;
    private LocalDate startDate;
    private LocalDate plannedEndDate;
    private LocalDate actualEndDate;
    private String constructionUnit;
    private String designUnit;
    private String supervisionUnit;
    private String ownerUnit;
    private Integer status;
    private Long creatorId;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
