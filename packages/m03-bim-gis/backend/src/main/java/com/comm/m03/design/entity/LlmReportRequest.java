package com.comm.m03.design.entity;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.Map;

@Data
public class LlmReportRequest {
    @NotNull
    private Map<String, Object> scheme;
    private Map<String, Object> context;
}
