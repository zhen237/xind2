package com.comm.m02.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m02_coordinate_system")
public class CoordinateSystem {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String epsgCode;

    private String name;

    private String type;

    private String projection;

    private String datum;

    private String parameters;

    private Boolean isPreset;

    private String description;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
