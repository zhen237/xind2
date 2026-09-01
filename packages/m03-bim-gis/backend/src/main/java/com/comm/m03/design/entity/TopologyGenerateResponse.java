package com.comm.m03.design.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * Python 拓扑引擎 /generate 响应的根对象（snake_case 映射）
 */
@Data
public class TopologyGenerateResponse {

    @JsonProperty("project_id")
    private Long projectId;

    @JsonProperty("scheme_name")
    private String schemeName;

    @JsonProperty("frequency_band")
    private String frequencyBand;

    @JsonProperty("tower_height")
    private BigDecimal towerHeight;

    @JsonProperty("grid_size")
    private String gridSize;

    @JsonProperty("total_sites")
    private Integer totalSites;

    @JsonProperty("valid_sites")
    private Integer validSites;

    @JsonProperty("invalid_sites")
    private Integer invalidSites;

    @JsonProperty("avg_rsrp")
    private BigDecimal avgRsrp;

    @JsonProperty("sites")
    private List<TopologySiteData> sites;

    @JsonProperty("layout")
    private TopologyLayout layout;
}
