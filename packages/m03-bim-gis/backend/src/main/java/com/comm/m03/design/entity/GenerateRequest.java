package com.comm.m03.design.entity;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class GenerateRequest {

    @NotNull(message = "项目ID不能为空")
    private Long projectId;

    @NotBlank(message = "方案名称不能为空")
    private String schemeName;

    private String templateType;

    @NotNull(message = "中心经度不能为空")
    private BigDecimal centerLongitude;

    @NotNull(message = "中心纬度不能为空")
    private BigDecimal centerLatitude;

    @NotNull(message = "覆盖半径不能为空")
    private BigDecimal coverageRadius;

    @NotBlank(message = "频段不能为空")
    private String frequencyBand;

    private BigDecimal towerHeight;

    private Integer gridSize;

    private Integer antennaHeight;

    private Integer sectorCount;

    private String scenario;
}
