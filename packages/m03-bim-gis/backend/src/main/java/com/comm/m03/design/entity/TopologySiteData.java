package com.comm.m03.design.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * Python 拓扑引擎返回的单个站点（含设备拓扑）
 */
@Data
public class TopologySiteData {

    @JsonProperty("site_id")
    private String siteId;

    @JsonProperty("site_name")
    private String siteName;

    @JsonProperty("longitude")
    private BigDecimal longitude;

    @JsonProperty("latitude")
    private BigDecimal latitude;

    @JsonProperty("tower_height")
    private BigDecimal towerHeight;

    @JsonProperty("site_type")
    private String siteType;

    @JsonProperty("scenario")
    private String scenario;

    @JsonProperty("rsrp")
    private BigDecimal rsrp;

    @JsonProperty("is_valid")
    private Boolean isValid;

    @JsonProperty("invalid_reason")
    private String invalidReason;

    @JsonProperty("devices")
    private List<TopologyDevicePosition> devices;
}
