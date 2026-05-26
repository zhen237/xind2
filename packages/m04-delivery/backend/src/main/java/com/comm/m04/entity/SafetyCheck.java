package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("m04_safety_check")
public class SafetyCheck {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long projectId;
    private LocalDate checkDate;
    private String equipmentType;
    private String brandModel;
    private LocalDate productionDate;
    private LocalDate validDate;
    private LocalDate lastTestDate;
    private String testReportNo;
    private Integer quantity;
    private String appearanceStatus;
    private String photoPath;
    private Integer checkResult;
    private Long checkBy;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
