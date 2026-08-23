package com.comm.m02.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("m02_gis_feature")
public class GisFeature {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long fusionTaskId;

    private String featureId;

    private String featureType;

    private String geometryType;

    private BigDecimal coordinateX;

    private BigDecimal coordinateY;

    private BigDecimal coordinateZ;

    private String propertiesJson;

    private String sourceLayer;

    private String targetLayer;

    private LocalDateTime createTime;
}
