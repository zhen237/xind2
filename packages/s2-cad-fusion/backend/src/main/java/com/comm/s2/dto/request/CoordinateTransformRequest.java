package com.comm.s2.dto.request;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class CoordinateTransformRequest {
    private BigDecimal sourceX;
    private BigDecimal sourceY;
    private BigDecimal sourceZ;
    private String sourceEpsg;
    private String targetEpsg;
    private String transformationType;
}
