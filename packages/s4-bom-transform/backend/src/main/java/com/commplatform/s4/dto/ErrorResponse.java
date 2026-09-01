package com.commplatform.s4.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 统一错误响应体 — 所有异常经 GlobalExceptionHandler 转换后返回此结构。
 * <p>{@code { "code": "S4_XXX", "message": "...", "timestamp": "..." }}</p>
 */
@Data
public class ErrorResponse {

    private String code;
    private String message;
    private LocalDateTime timestamp;

    public ErrorResponse() {
    }

    public ErrorResponse(String code, String message) {
        this.code = code;
        this.message = message;
        this.timestamp = LocalDateTime.now();
    }
}
