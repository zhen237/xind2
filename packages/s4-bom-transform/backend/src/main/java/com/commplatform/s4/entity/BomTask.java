package com.commplatform.s4.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * BOM 任务表 (s4_bom_task)。
 */
@Data
@TableName("s4_bom_task")
public class BomTask {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 任务 ID（UUID） */
    private String taskId;

    /** 关联 S1 设计任务 ID */
    private String designTaskId;

    /** 项目 ID */
    private String projectId;

    /** pending / running / done / failed */
    private String status;

    /** 失败时的错误信息 */
    private String errorMessage;

    /** 总类目数 */
    private Integer totalCategories;

    /** 总数量 */
    private Integer totalQty;

    /** 主设备数量 */
    private Integer mainDeviceQty;

    /** 辅材数量 */
    private Integer auxiliaryQty;

    /** 线缆数量 */
    private Integer cableQty;

    private LocalDateTime createdAt;
    private LocalDateTime finishedAt;

    /** 关键工序工艺要求（JSON 文本） */
    private String processRequirements;

    /** 纤芯分配表（JSON 文本） */
    private String fiberAllocation;
}
