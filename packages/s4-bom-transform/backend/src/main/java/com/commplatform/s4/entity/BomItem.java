package com.commplatform.s4.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;

/**
 * BOM 物料明细表 (s4_bom_item)。
 */
@Data
@TableName("s4_bom_item")
public class BomItem {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 关联 BOM 任务 taskId */
    private String taskId;

    /** 物料编码（如 M-ANT-001） */
    private String materialCode;

    /** 物料名称 */
    private String materialName;

    /** 规格型号 */
    private String spec;

    /** 单位（套/根/包/件） */
    private String unit;

    /** 数量 */
    private Integer qty;

    /** 单根长度（米，线缆专用） */
    private BigDecimal singleLength;

    /** 总长度（米，线缆专用） */
    private BigDecimal totalLength;

    /** main_device / auxiliary / cable */
    private String category;

    /** 关联设备名称（如 AAU-扇区1） */
    private String deviceName;

    /** 关联设备类型（如 antenna / rru / bbu） */
    private String deviceType;
}
