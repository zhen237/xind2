package com.comm.m03.design.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 设计方案实体
 */
@Data
@TableName("m03_design_scheme")
public class DesignScheme {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 项目ID
     */
    private Long projectId;

    /**
     * 来源设计任务编号（S1 taskNo）——任务主线追溯：方案由哪个任务执行产出
     */
    private String taskNo;

    /**
     * 方案名称
     */
    private String schemeName;

    /**
     * 频段
     */
    private String frequencyBand;

    /**
     * 塔高(米)
     */
    private BigDecimal towerHeight;

    /**
     * 网格大小
     */
    private String gridSize;

    /**
     * 总站点数
     */
    private Integer totalSites;

    /**
     * 有效站点数
     */
    private Integer validSites;

    /**
     * 无效站点数
     */
    private Integer invalidSites;

    /**
     * 平均RSRP(dBm)
     */
    private BigDecimal avgRsrp;

    /**
     * 机房经度（QGIS插件同步过来的机房位置，nullable）
     */
    private BigDecimal roomLongitude;

    /**
     * 机房纬度
     */
    private BigDecimal roomLatitude;

    /**
     * 机房名称
     */
    private String roomName;

    /**
     * 管线路由类型（QGIS插件确定：direct=直线路径, manhattan=曼哈顿路径）
     */
    private String routeType;

    /**
     * 上传幂等键（QGIS插件生成的 UUID）。重复上传同一键时返回已存在方案，避免产生重复方案。
     */
    private String idempotencyKey;

    /**
     * 管线工程量 JSON 快照（QGIS插件上传的 {@code DesignData.pipelines} 数组序列化结果）。
     * 列: {@code m03_design_scheme.pipeline_json TEXT NULL COLLATE utf8mb4_unicode_ci}。
     * /result 接口按 task_no 读回该字段并合并进 {@code DesignData.pipelines}，供 S4 生成 BOM。
     */
    private String pipelineJson;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;
}
