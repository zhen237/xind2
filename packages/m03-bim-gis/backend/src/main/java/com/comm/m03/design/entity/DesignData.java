package com.comm.m03.design.entity;

import lombok.Data;
import java.math.BigDecimal;
import java.util.List;

/**
 * 设计数据DTO
 */
@Data
public class DesignData {

    /**
     * 项目ID
     */
    private Long projectId;

    /**
     * 方案名称
     */
    private String schemeName;

    /**
     * 频段
     */
    private String frequencyBand;

    /**
     * 塔高(米)
     */
    private BigDecimal towerHeight;

    /**
     * 网格大小
     */
    private String gridSize;

    /**
     * 总站点数
     */
    private Integer totalSites;

    /**
     * 有效站点数
     */
    private Integer validSites;

    /**
     * 无效站点数
     */
    private Integer invalidSites;

    /**
     * 平均RSRP(dBm)
     */
    private BigDecimal avgRsrp;

    /**
     * 站点列表
     */
    private List<SiteData> sites;
}
