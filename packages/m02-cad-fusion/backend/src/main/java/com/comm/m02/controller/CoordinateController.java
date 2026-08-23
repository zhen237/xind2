package com.comm.m02.controller;

import com.comm.m02.common.Result;
import com.comm.m02.dto.request.CoordinateTransformRequest;
import com.comm.m02.dto.response.CoordinateTransformResponse;
import com.comm.m02.service.CoordinateTransformService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/m02/coordinate")
public class CoordinateController {

    @Autowired
    private CoordinateTransformService transformService;

    @PostMapping("/transform")
    public Result<CoordinateTransformResponse> transform(@RequestBody CoordinateTransformRequest request) {
        CoordinateTransformResponse response = transformService.transform(
                request.getSourceX(),
                request.getSourceY(),
                request.getSourceZ(),
                request.getSourceEpsg(),
                request.getTargetEpsg(),
                request.getTransformationType()
        );
        return Result.success("转换成功", response);
    }

    @PostMapping("/batch-transform")
    public Result<List<CoordinateTransformResponse>> batchTransform(
            @RequestBody Map<String, Object> request) {
        
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> coordinates = (List<Map<String, Object>>) request.get("coordinates");
        String sourceEpsg = (String) request.get("sourceEpsg");
        String targetEpsg = (String) request.get("targetEpsg");

        java.util.List<CoordinateTransformResponse> results = new java.util.ArrayList<>();
        for (Map<String, Object> coord : coordinates) {
            BigDecimal x = new BigDecimal(coord.get("x").toString());
            BigDecimal y = new BigDecimal(coord.get("y").toString());
            BigDecimal z = coord.containsKey("z") ? 
                    new BigDecimal(coord.get("z").toString()) : BigDecimal.ZERO;
            
            CoordinateTransformResponse response = transformService.transform(
                    x, y, z, sourceEpsg, targetEpsg
            );
            results.add(response);
        }

        return Result.success("批量转换成功", results);
    }

    @PostMapping("/wgs84-to-cgcs2000")
    public Result<CoordinateTransformResponse> wgs84ToCGCS2000(
            @RequestParam BigDecimal lon,
            @RequestParam BigDecimal lat) {
        CoordinateTransformResponse response = transformService.wgs84ToCGCS2000(lon, lat);
        return Result.success("转换成功", response);
    }

    @PostMapping("/beijing54-to-wgs84")
    public Result<CoordinateTransformResponse> beijing54ToWgs84(
            @RequestParam BigDecimal x,
            @RequestParam BigDecimal y) {
        CoordinateTransformResponse response = transformService.beijing1954ToWgs84(x, y);
        return Result.success("转换成功", response);
    }

    @GetMapping("/supported-systems")
    public Result<Map<String, Object>> getSupportedSystems() {
        Map<String, Object> systems = new HashMap<>();
        
        Map<String, String> wgs84 = new HashMap<>();
        wgs84.put("epsg", "EPSG:4326");
        wgs84.put("name", "WGS 84");
        wgs84.put("description", "全球定位系统标准坐标系");
        systems.put("WGS84", wgs84);

        Map<String, String> cgcs2000 = new HashMap<>();
        cgcs2000.put("epsg", "EPSG:4490");
        cgcs2000.put("name", "CGCS2000");
        cgcs2000.put("description", "中国大地坐标系2000");
        systems.put("CGCS2000", cgcs2000);

        Map<String, String> beijing54 = new HashMap<>();
        beijing54.put("epsg", "EPSG:4214");
        beijing54.put("name", "Beijing 1954");
        beijing54.put("description", "北京1954坐标系");
        systems.put("BEIJING54", beijing54);

        Map<String, String> xian80 = new HashMap<>();
        xian80.put("epsg", "EPSG:4610");
        xian80.put("name", "Xi'an 1980");
        xian80.put("description", "西安1980坐标系");
        systems.put("XIAN80", xian80);

        Map<String, String> webMercator = new HashMap<>();
        webMercator.put("epsg", "EPSG:3857");
        webMercator.put("name", "Web Mercator");
        webMercator.put("description", "Web地图投影坐标系");
        systems.put("WEBMERCATOR", webMercator);

        return Result.success("获取成功", systems);
    }
}
