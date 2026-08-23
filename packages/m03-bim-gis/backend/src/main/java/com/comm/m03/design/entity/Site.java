package com.comm.m03.design.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 站点实体
 */
@Data
@TableName("m03_site")
public class Site {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 方案ID
     */
    private Long schemeId;

    /**
     * 站点ID
     */
    private String siteId;

    /**
     * 站点名称
     */
    private String siteName;

    /**
     * 经度
     */
    private BigDecimal longitude;

    /**
     * 纬度
     */
    private BigDecimal latitude;

    /**
     * 塔高(米)
     */
    private BigDecimal towerHeight;

    /**
     * 站点类型
     */
    private String siteType;

    /**
     * 场景
     */
    private String scenario;

    /**
     * RSRP(dBm)
     */
    private BigDecimal rsrp;

    /**
     * RSRP 数据来源: simulated=模型仿真(Okumura-Hata), measured=实测/现场勘测
     * 前端覆盖分析据此判断使用真值还是估算值
     */
    private String rsrpSource;

    /**
     * 是否有效(0:无效,1:有效)
     */
    private Integer isValid;

    /**
     * 无效原因
     */
    private String invalidReason;

    /**
     * 站点幂等键(客户端生成UUID)。重复提交同一键站点时跳过不翻倍（防网络重试翻倍）。
     */
    private String idempotencyKey;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;
}
