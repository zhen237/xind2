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

    /** 完整几何（GeoJSON Geometry JSON串，含全部顶点，坐标系为目标坐标系） */
    private String geometryJson;

    private String propertiesJson;

    private String sourceLayer;

    private String targetLayer;

    private LocalDateTime createTime;
}
