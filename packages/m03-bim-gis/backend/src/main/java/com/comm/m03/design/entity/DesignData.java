package com.comm.m03.design.entity;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 设计数据DTO
 */
@Data
public class DesignData {

    @NotNull(message = "项目ID不能为空")
    private Long projectId;

    @NotBlank(message = "方案名称不能为空")
    private String schemeName;

    private String frequencyBand;

    private BigDecimal towerHeight;

    private String gridSize;

    private Integer totalSites;

    private Integer validSites;

    private Integer invalidSites;

    private BigDecimal avgRsrp;

    @Valid
    private List<SiteData> sites;

    /**
     * 机房列表（QGIS插件同步过来的机房数据）
     * 每个元素包含: roomId, name, longitude, latitude, roomType
     */
    private List<Map<String, Object>> machineRooms;

    /**
     * 管线工程量数据（QGIS插件随设计成果上传）。
     * 每个元素为 {@code Pipeline.to_dict()} 结构（含 pipeline_id/pipeline_type/fiber_type/length_m/coordinates 等）。
     * 契约：单独落库到 {@code m03_design_scheme.pipeline_json}，
     * {@code GET /api/m03/design/tasks/{id}/result} 按任务的 task_no 读回并合并进 result.pipelines。
     */
    private List<Map<String, Object>> pipelines;

    /**
     * 管线路由类型（QGIS插件确定：direct=直线路径, manhattan=曼哈顿路径）
     */
    private String routeType;

    /**
     * 上传幂等键（QGIS插件生成 UUID）。服务端据此去重，重复上传返回已存在方案。
     */
    private String idempotencyKey;

    /**
     * 设备拓扑（来自 Python 拓扑引擎的完整设备布局），用于 saveLayout 落库
     */
    @Valid
    private List<DevicePositionData> deviceLayout;

    /** 是否发生降级：true 表示成果由本地兜底算法产出，而非拓扑引擎 */
    private Boolean degraded;

    /** 降级原因（仅 degraded=true 时有值） */
    private String degradeReason;
}
