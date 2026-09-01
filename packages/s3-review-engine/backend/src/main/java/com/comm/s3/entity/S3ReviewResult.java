package com.comm.s3.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("s3_review_result")
public class S3ReviewResult {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long taskId;
    private Long ruleId;
    private String ruleCode;
    private String ruleName;
    private String actualValue;
    private String standardValue;
    private String coordinates;
    private String riskLevel;
    private String remark;
    private LocalDateTime createTime;
}
