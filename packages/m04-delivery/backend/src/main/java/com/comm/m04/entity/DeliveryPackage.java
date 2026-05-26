package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("m04_delivery_package")
public class DeliveryPackage {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long projectId;
    private String packageName;
    private String packageType;
    private Integer status;
    private Integer fileCount;
    private Long totalSize;
    private String minioPath;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}