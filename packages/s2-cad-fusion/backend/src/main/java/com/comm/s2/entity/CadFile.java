package com.comm.s2.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("s2_cad_file")
public class CadFile {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String fileName;

    private String originalName;

    private String filePath;

    private String fileType;

    private Long fileSize;

    private Long projectId;

    private Long uploadedBy;

    private String sourceEpsg;

    private String targetEpsg;

    private Integer parseStatus;

    private String parseResult;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
