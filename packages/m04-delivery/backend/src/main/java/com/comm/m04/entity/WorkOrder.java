package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("m04_work_order")
public class WorkOrder {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String orderNo;
    private String title;
    private String type;
    private Integer priority;
    private Integer status;
    private String stationCode;
    private String deviceCode;
    private Long assigneeId;
    private Long creatorId;
    private String description;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
