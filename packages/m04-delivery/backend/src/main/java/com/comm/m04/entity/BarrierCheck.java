package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("m04_barrier_check")
public class BarrierCheck {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long projectId;
    private LocalDate checkDate;
    private Integer barrierIntegrity;
    private String signList;
    private Integer nightLightStatus;
    private String roadPhoto;
    private String environmentRisk;
    private Integer checkConclusion;
    private Long checkBy;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
