package com.comm.m03.design.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

/**
 * 大模型解析出的结构化设计参数（对应 m03-llm-service 的 DesignParams）。
 * 字段名用 snake_case 与 Python 返回值对齐（项目无全局 snake 配置，故显式标注）。
 */
@Data
public class LlmDesignParams {
    @JsonProperty("template_type")
    private String templateType;
    @JsonProperty("center_longitude")
    private Double centerLongitude;
    @JsonProperty("center_latitude")
    private Double centerLatitude;
    @JsonProperty("coverage_radius")
    private Double coverageRadius;
    @JsonProperty("frequency_band")
    private String frequencyBand;
    @JsonProperty("tower_height")
    private Double towerHeight;
    @JsonProperty("antenna_height")
    private Double antennaHeight;
    @JsonProperty("sector_count")
    private Integer sectorCount;
    @JsonProperty("scenario")
    private String scenario;
    @JsonProperty("site_count")
    private Integer siteCount;
    @JsonProperty("notes")
    private String notes;
}
