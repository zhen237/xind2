package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("m04_cert_verification")
public class CertVerification {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long projectId;
    private String personName;
    private String idCard;
    private String certType;
    private String certNumber;
    private String issuingAuthority;
    private LocalDate validFrom;
    private LocalDate validTo;
    private String photoDistance;
    private String photoClose;
    private String videoPath;
    private Integer verifyResult;
    private String verifyComment;
    private Long verifyBy;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
