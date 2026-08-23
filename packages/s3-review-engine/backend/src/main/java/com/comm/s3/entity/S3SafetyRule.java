package com.comm.s3.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("s3_safety_rule")
public class S3SafetyRule {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String ruleCode;
    private String ruleName;
    private String category;
    private String threshold;
    private String riskLevel;
    private String suggestion;
    private Integer status;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
