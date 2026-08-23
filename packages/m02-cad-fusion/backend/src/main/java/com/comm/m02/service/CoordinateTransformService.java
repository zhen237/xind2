package com.comm.m02.service;

import com.comm.m02.dto.response.CoordinateTransformResponse;

import java.math.BigDecimal;

public interface CoordinateTransformService {

    CoordinateTransformResponse transform(BigDecimal sourceX, BigDecimal sourceY, BigDecimal sourceZ,
                                          String sourceEpsg, String targetEpsg);

    CoordinateTransformResponse transform(BigDecimal sourceX, BigDecimal sourceY, BigDecimal sourceZ,
                                          String sourceEpsg, String targetEpsg, String transformationType);

    CoordinateTransformResponse wgs84ToCGCS2000(BigDecimal lon, BigDecimal lat);

    CoordinateTransformResponse beijing1954ToWgs84(BigDecimal x, BigDecimal y);
}
