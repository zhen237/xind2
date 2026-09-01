package com.comm.s3.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("s3_review_task")
public class S3ReviewTask {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String designTaskId;
    private String taskName;
    private String taskStatus;
    private Double coverageRate;
    private Integer totalCount;
    private Integer criticalCount;
    private Integer errorCount;
    private Integer warningCount;
    private String createBy;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
