package com.comm.m03.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_region")
public class Region {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String regionCode;
    
    private String regionName;
    
    private String parentCode;
    
    private String bounds;
    
    private String centerCoord;
    
    private LocalDateTime createTime;
}