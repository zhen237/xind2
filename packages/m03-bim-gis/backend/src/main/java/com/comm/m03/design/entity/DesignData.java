package com.comm.m03.design.entity;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;

/**
 * 设计数据DTO
 */
@Data
public class DesignData {

    @NotNull(message = "项目ID不能为空")
    private Long projectId;

    @NotBlank(message = "方案名称不能为空")
    private String schemeName;

    private String frequencyBand;

    private BigDecimal towerHeight;

    private String gridSize;

    private Integer totalSites;

    private Integer validSites;

    private Integer invalidSites;

    private BigDecimal avgRsrp;

    @Valid
    private List<SiteData> sites;

    /**
     * 设备拓扑（来自 Python 拓扑引擎的完整设备布局），用于 saveLayout 落库
     */
    @Valid
    private List<DevicePositionData> deviceLayout;
}
