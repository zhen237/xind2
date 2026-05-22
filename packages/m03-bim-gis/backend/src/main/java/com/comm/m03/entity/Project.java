package com.comm.m03.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_project")
public class Project {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String projectName;
    
    private String projectCode;
    
    private String regionCode;
    
    private String description;
    
    private Integer status;
    
    private Long creatorId;
    
    private LocalDateTime createTime;
    
    private LocalDateTime updateTime;
}