package com.comm.m03.design.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;

/**
 * 站点数据DTO
 */
@Data
public class SiteData {

    @NotBlank(message = "站点ID不能为空")
    private String siteId;

    private String siteName;

    private BigDecimal longitude;

    private BigDecimal latitude;

    private BigDecimal towerHeight;

    private String siteType;

    private String scenario;

    private BigDecimal rsrp;

    private Boolean isValid;

    private String invalidReason;

    /**
     * 覆盖多边形(扇区)：每个站点一组多边形坐标环，来自拓扑引擎 /generate 的 coverage_polygons。
     * 结构: [ 多边形1, 多边形2, ... ]，每个多边形 = [ [lon,lat], ... ]。
     * 引擎路径下由 mapFromEngine 填充；本地回退路径下为 null（前端/QGIS 不渲染扇区覆盖）。
     */
    @JsonProperty("coveragePolygons")
    private List<List<List<Double>>> coveragePolygons;
}
