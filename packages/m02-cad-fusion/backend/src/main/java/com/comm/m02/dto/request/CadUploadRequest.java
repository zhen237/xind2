package com.comm.m02.dto.request;

import lombok.Data;

@Data
public class CadUploadRequest {
    private Long projectId;
    private String description;
    private String sourceEpsg;
    private String targetEpsg;
}
