package com.commplatform.s4.exception;

import com.commplatform.s4.dto.ErrorResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

/**
 * S4 全局异常处理器 — 统一错误响应格式。
 * <p>{@code { "code": "S4_XXX", "message": "...", "timestamp": "..." }}</p>
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /** 业务异常（含错误码 + HTTP 状态） */
    @ExceptionHandler(S4BusinessException.class)
    public ResponseEntity<ErrorResponse> handleBusiness(S4BusinessException e) {
        log.warn("业务异常: code={} msg={}", e.getErrorCode().getCode(), e.getMessage());
        ErrorResponse resp = new ErrorResponse(e.getErrorCode().getCode(), e.getMessage());
        return ResponseEntity.status(e.getErrorCode().getHttpStatus()).body(resp);
    }

    /** @Valid 请求体校验失败 → 400 */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
                .reduce((a, b) -> a + "; " + b)
                .orElse("参数校验失败");
        log.warn("参数校验失败: {}", msg);
        return badRequest(S4ErrorCode.INVALID_PARAM, msg);
    }

    /** 请求体缺失/JSON 格式错误 → 400 */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleUnreadable(HttpMessageNotReadableException e) {
        log.warn("请求体解析失败: {}", e.getMessage());
        return badRequest(S4ErrorCode.INVALID_PARAM, "请求体缺失或 JSON 格式错误");
    }

    /** 缺少必填 Query 参数 → 400 */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ErrorResponse> handleMissingParam(MissingServletRequestParameterException e) {
        log.warn("缺少参数: {}", e.getParameterName());
        return badRequest(S4ErrorCode.INVALID_PARAM, "缺少必填参数: " + e.getParameterName());
    }

    /** 参数类型不匹配 → 400 */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponse> handleTypeMismatch(MethodArgumentTypeMismatchException e) {
        log.warn("参数类型错误: {}={}", e.getName(), e.getValue());
        return badRequest(S4ErrorCode.INVALID_PARAM, "参数类型错误: " + e.getName());
    }

    /** 引擎/跨服务 连接或读超时 → 504 */
    @ExceptionHandler(ResourceAccessException.class)
    public ResponseEntity<ErrorResponse> handleEngineTimeout(ResourceAccessException e) {
        log.error("下游服务不可达/超时: {}", e.getMessage());
        ErrorResponse resp = new ErrorResponse(
                S4ErrorCode.ENGINE_TIMEOUT.getCode(),
                "下游服务响应超时或不可达: " + e.getMessage());
        return ResponseEntity.status(S4ErrorCode.ENGINE_TIMEOUT.getHttpStatus()).body(resp);
    }

    /** 兜底 → 500 */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception e) {
        log.error("未预期异常", e);
        ErrorResponse resp = new ErrorResponse(
                S4ErrorCode.INTERNAL_ERROR.getCode(),
                "服务内部错误，请稍后重试");
        return ResponseEntity.status(S4ErrorCode.INTERNAL_ERROR.getHttpStatus()).body(resp);
    }

    private ResponseEntity<ErrorResponse> badRequest(S4ErrorCode code, String message) {
        ErrorResponse resp = new ErrorResponse(code.getCode(), message);
        return ResponseEntity.status(code.getHttpStatus()).body(resp);
    }
}
