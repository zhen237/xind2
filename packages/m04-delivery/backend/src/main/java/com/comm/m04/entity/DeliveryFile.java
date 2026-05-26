package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("m04_delivery_file")
public class DeliveryFile {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long packageId;
    private String fileName;
    private String filePath;
    private Long fileSize;
    private String fileType;
    private String md5;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}