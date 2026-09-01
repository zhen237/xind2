package com.comm.m03.design.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("m03_design_task")
public class DesignTask {

    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String taskNo;
    
    private String taskName;
    
    private Long templateId;
    
    private Long projectId;
    
    private String paramsJson;
    
    private String resultJson;

    /**
     * 任务级本地数据源：前端在任务上加载的原始 GeoJSON（持久化，重进项目可恢复）。
     * 大字段，列表接口不返回（见 getDesignTasks 的 select 排除），详情/成果接口返回。
     */
    private String localDataJson;

    /**
     * 列表展示用轻量标记：该任务是否已加载本地数据（exist=false 不入库）。
     */
    @TableField(exist = false)
    private Boolean localDataFlag;
    
    private String status;
    
    private String createdBy;
    
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;

    /**
     * 创建幂等键(客户端生成UUID)。重复创建同一键时返回已存在任务，不重复写入（防网络重试翻倍）。
     */
    private String idempotencyKey;
}