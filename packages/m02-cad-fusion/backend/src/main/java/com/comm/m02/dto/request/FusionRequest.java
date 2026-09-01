package com.comm.m02.dto.request;

import lombok.Data;

import java.util.List;

@Data
public class FusionRequest {
    private String taskName;
    private Long projectId;
    private Long sourceFileId;
    private String sourceEpsg;
    private String targetEpsg;
    private String transformationType;
    private List<FieldMapping> fieldMappings;

    @Data
    public static class FieldMapping {
        private String cadField;
        private String gisField;
        private String transformType;
    }
}
