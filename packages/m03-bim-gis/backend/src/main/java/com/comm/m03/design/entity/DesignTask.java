package com.comm.m03.design.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_design_task")
public class DesignTask {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String taskNo;
    
    private String taskName;
    
    private Long templateId;
    
    private Long projectId;
    
    private String paramsJson;
    
    private String resultJson;
    
    private String status;
    
    private String createdBy;
    
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;
}