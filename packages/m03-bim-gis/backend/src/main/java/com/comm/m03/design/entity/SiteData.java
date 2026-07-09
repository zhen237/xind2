package com.comm.m03.design.entity;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import java.math.BigDecimal;

/**
 * 站点数据DTO
 */
@Data
public class SiteData {

    @NotBlank(message = "站点ID不能为空")
    private String siteId;

    private String siteName;

    private BigDecimal longitude;

    private BigDecimal latitude;

    private BigDecimal towerHeight;

    private String siteType;

    private String scenario;

    private BigDecimal rsrp;

    private Boolean isValid;

    private String invalidReason;
}
