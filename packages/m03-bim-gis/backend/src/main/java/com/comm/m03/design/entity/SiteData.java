package com.comm.m03.design.entity;

import lombok.Data;
import java.math.BigDecimal;

/**
 * 站点数据DTO
 */
@Data
public class SiteData {

    /**
     * 站点ID
     */
    private String siteId;

    /**
     * 站点名称
     */
    private String siteName;

    /**
     * 经度
     */
    private BigDecimal longitude;

    /**
     * 纬度
     */
    private BigDecimal latitude;

    /**
     * 塔高(米)
     */
    private BigDecimal towerHeight;

    /**
     * 站点类型
     */
    private String siteType;

    /**
     * 场景
     */
    private String scenario;

    /**
     * RSRP(dBm)
     */
    private BigDecimal rsrp;

    /**
     * 是否有效
     */
    private Boolean isValid;

    /**
     * 无效原因
     */
    private String invalidReason;
}
