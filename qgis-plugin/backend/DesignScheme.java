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
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;
}
