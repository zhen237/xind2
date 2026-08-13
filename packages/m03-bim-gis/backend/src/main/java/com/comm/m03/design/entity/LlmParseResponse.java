package com.comm.m03.design.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class LlmParseResponse {
    @JsonProperty("params")
    private LlmDesignParams params;
}
