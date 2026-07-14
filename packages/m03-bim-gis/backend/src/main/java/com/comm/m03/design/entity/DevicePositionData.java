package com.comm.m03.design.entity;

import lombok.Data;

import java.math.BigDecimal;
import java.util.Map;

/**
 * 设备拓扑位置（来自 Python 拓扑引擎的设备级布局）
 * 用于 saveLayout 落库到 m03_generated_layout
 */
@Data
public class DevicePositionData {

    private String deviceName;

    private String deviceType;

    private String modelSpec;

    private BigDecimal longitude;

    private BigDecimal latitude;

    private BigDecimal altitude;

    private BigDecimal azimuth;

    private BigDecimal downtilt;

    private BigDecimal mountHeight;

    private BigDecimal coverageRadius;

    private String parentDevice;

    private String positionId;

    private Map<String, Object> extraParams;
}
