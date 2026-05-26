package com.comm.m04.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("m04_construction_record")
public class ConstructionRecord {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long projectId;
    private String responsiblePerson;
    private LocalDate workDate;
    private String workContent;
    private String constructionUnits;
    private Integer environmentAssessment;
    private String hazardDescription;
    private String videoPath;
    private String photoPanorama;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
