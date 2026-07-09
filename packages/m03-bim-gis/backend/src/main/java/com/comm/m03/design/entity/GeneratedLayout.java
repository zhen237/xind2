package com.comm.m03.design.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_generated_layout")
public class GeneratedLayout {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long taskId;
    
    private String deviceName;
    
    private String deviceType;
    
    private String modelSpec;
    
    private Double longitude;
    
    private Double latitude;
    
    private Double altitude;
    
    private Double azimuth;
    
    private Double downtilt;
    
    private Double mountHeight;
    
    private Double coverageRadius;
    
    private String parentDevice;
    
    private String extraParams;
    
    private Integer sortOrder;
    
    private LocalDateTime createdAt;
}