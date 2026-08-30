package com.commplatform.s4.exception;

/**
 * S4 业务异常 — 携带统一错误码，由 GlobalExceptionHandler 统一转换为
 * {@code {code, message, timestamp}} 响应体。
 */
public class S4BusinessException extends RuntimeException {

    private final transient S4ErrorCode errorCode;

    public S4BusinessException(S4ErrorCode errorCode) {
        super(errorCode.getDefaultMessage());
        this.errorCode = errorCode;
    }

    public S4BusinessException(S4ErrorCode errorCode, String detail) {
        super(detail != null && !detail.isBlank() ? detail : errorCode.getDefaultMessage());
        this.errorCode = errorCode;
    }

    public S4BusinessException(S4ErrorCode errorCode, String detail, Throwable cause) {
        super(detail != null && !detail.isBlank() ? detail : errorCode.getDefaultMessage(), cause);
        this.errorCode = errorCode;
    }

    public S4ErrorCode getErrorCode() {
        return errorCode;
    }
}
