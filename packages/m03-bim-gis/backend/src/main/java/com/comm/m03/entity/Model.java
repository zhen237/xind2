package com.comm.m03.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_model")
public class Model {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String modelName;
    
    private String modelCode;
    
    private String modelType;
    
    private String filePath;
    
    private String thumbnailPath;
    
    private Double scale;
    
    private String description;
    
    private LocalDateTime createTime;
}