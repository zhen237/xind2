package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("m04_electricity_check")
public class ElectricityCheck {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long projectId;
    private LocalDate checkDate;
    private String distributionBoxNo;
    private Integer circuitCount;
    private String leakageProtectorModel;
    private Integer leakageProtectorCount;
    private Integer oneMachineOneSwitch;
    private String cableStatus;
    private BigDecimal groundResistance;
    private String boxSurrounding;
    private String photoPath;
    private Integer checkConclusion;
    private Long checkBy;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
