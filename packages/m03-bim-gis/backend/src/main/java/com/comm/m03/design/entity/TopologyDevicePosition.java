package com.comm.m03.design.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Python 拓扑引擎返回的设备级位置（snake_case 映射）
 */
@Data
public class TopologyDevicePosition {

    @JsonProperty("device_name")
    private String deviceName;

    @JsonProperty("device_type")
    private String deviceType;

    @JsonProperty("model_spec")
    private String modelSpec;

    @JsonProperty("longitude")
    private BigDecimal longitude;

    @JsonProperty("latitude")
    private BigDecimal latitude;

    @JsonProperty("altitude")
    private BigDecimal altitude;

    @JsonProperty("azimuth")
    private BigDecimal azimuth;

    @JsonProperty("downtilt")
    private BigDecimal downtilt;

    @JsonProperty("mount_height")
    private BigDecimal mountHeight;

    @JsonProperty("coverage_radius")
    private BigDecimal coverageRadius;

    @JsonProperty("parent_device")
    private String parentDevice;

    @JsonProperty("position_id")
    private String positionId;

    @JsonProperty("extra_params")
    private Map<String, Object> extraParams;
}
