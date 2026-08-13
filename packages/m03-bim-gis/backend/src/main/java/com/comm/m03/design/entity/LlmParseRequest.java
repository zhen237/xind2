package com.comm.m03.design.entity;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.Map;

@Data
public class LlmParseRequest {
    @NotBlank
    private String text;
    private Map<String, Object> context;
}
