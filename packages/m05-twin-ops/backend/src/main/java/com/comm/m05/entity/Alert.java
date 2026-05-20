package com.comm.m05.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m05_alert")
public class Alert {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long deviceId;
    private String deviceCode;
    private String alertContent;
    private Integer level;
    private Integer status;
    private String source;
    private String orderNo;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
