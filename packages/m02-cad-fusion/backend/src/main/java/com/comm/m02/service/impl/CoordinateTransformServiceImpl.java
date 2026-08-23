package com.comm.m02.service.impl;

import com.comm.m02.dto.response.CoordinateTransformResponse;
import com.comm.m02.transform.CoordinateTransformer;
import com.comm.m02.service.CoordinateTransformService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;

@Service
public class CoordinateTransformServiceImpl implements CoordinateTransformService {

    @Autowired
    private CoordinateTransformer coordinateTransformer;

    @Override
    public CoordinateTransformResponse transform(BigDecimal sourceX, BigDecimal sourceY, 
                                                  BigDecimal sourceZ, String sourceEpsg, String targetEpsg) {
        return transform(sourceX, sourceY, sourceZ, sourceEpsg, targetEpsg, "AUTO");
    }

    @Override
    public CoordinateTransformResponse transform(BigDecimal sourceX, BigDecimal sourceY, 
                                                  BigDecimal sourceZ, String sourceEpsg, 
                                                  String targetEpsg, String transformationType) {
        CoordinateTransformer.TransformResult result = coordinateTransformer.transform(
                sourceX, sourceY, sourceZ, sourceEpsg, targetEpsg, transformationType
        );

        CoordinateTransformResponse response = new CoordinateTransformResponse();
        response.setSourceX(result.getSourceX());
        response.setSourceY(result.getSourceY());
        response.setSourceZ(result.getSourceZ());
        response.setTargetX(result.getTargetX());
        response.setTargetY(result.getTargetY());
        response.setTargetZ(result.getTargetZ());
        response.setSourceEpsg(result.getSourceEpsg());
        response.setTargetEpsg(result.getTargetEpsg());
        response.setTransformationType(result.getTransformType());
        response.setAccuracy(result.getAccuracy());

        return response;
    }

    @Override
    public CoordinateTransformResponse wgs84ToCGCS2000(BigDecimal lon, BigDecimal lat) {
        return transform(lon, lat, BigDecimal.ZERO, "EPSG:4326", "EPSG:4490", "WGS84_TO_CGCS2000");
    }

    @Override
    public CoordinateTransformResponse beijing1954ToWgs84(BigDecimal x, BigDecimal y) {
        return transform(x, y, BigDecimal.ZERO, "EPSG:4214", "EPSG:4326", "BEIJING54_TO_WGS84");
    }
}
