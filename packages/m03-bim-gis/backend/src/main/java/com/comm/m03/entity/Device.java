package com.comm.m03.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_device")
public class Device {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String deviceCode;
    
    private String deviceName;
    
    private String deviceType;
    
    private String stationCode;
    
    private Double longitude;
    
    private Double latitude;
    
    private Double height;
    
    private String status;
    
    private String manufacturer;
    
    private String model;
    
    private String installationTime;
    
    private String remark;
    
    private Long projectId;
    
    private LocalDateTime createTime;
    
    private LocalDateTime updateTime;
}