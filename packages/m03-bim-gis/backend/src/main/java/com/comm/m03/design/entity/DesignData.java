package com.comm.m03.design.entity;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

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
     * 机房列表（QGIS插件同步过来的机房数据）
     * 每个元素包含: roomId, name, longitude, latitude, roomType
     */
    private List<Map<String, Object>> machineRooms;

    /**
     * 管线路由类型（QGIS插件确定：direct=直线路径, manhattan=曼哈顿路径）
     */
    private String routeType;

    /**
     * 设备拓扑（来自 Python 拓扑引擎的完整设备布局），用于 saveLayout 落库
     */
    @Valid
    private List<DevicePositionData> deviceLayout;
}
