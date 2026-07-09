package com.comm.m03.design.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_parametric_template")
public class ParametricTemplate {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String name;
    
    private String category;
    
    private String description;
    
    private String devicesJson;
    
    private String topologyRule;
    
    private String coverageType;
    
    private String defaultParams;
    
    private Integer isActive;
    
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;
}