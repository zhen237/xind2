package com.comm.m02.dto.response;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class CoordinateTransformResponse {
    private BigDecimal sourceX;
    private BigDecimal sourceY;
    private BigDecimal sourceZ;
    private BigDecimal targetX;
    private BigDecimal targetY;
    private BigDecimal targetZ;
    private String sourceEpsg;
    private String targetEpsg;
    private String transformationType;
    private Double accuracy;
}
