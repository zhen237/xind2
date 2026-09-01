package com.commplatform.s4.exception;

/**
 * S4 模块统一错误码枚举。
 * <p>
 * 每个错误码包含：业务码（返回给前端）、默认提示文案、HTTP 状态码。
 */
public enum S4ErrorCode {

    INVALID_PARAM("S4_INVALID_PARAM", "参数校验失败", 400),
    TASK_NOT_FOUND("S4_TASK_NOT_FOUND", "BOM 任务不存在", 404),
    REVIEW_BLOCKED("S4_REVIEW_BLOCKED", "设计审查未通过，BOM 生成被拦截", 400),
    ENGINE_TIMEOUT("S4_ENGINE_TIMEOUT", "BOM 引擎响应超时", 504),
    ENGINE_ERROR("S4_ENGINE_ERROR", "BOM 引擎调用失败", 502),
    EXPORT_NOT_READY("S4_EXPORT_NOT_READY", "Excel 导出文件尚未就绪", 409),
    INTERNAL_ERROR("S4_INTERNAL_ERROR", "服务内部错误", 500);

    private final String code;
    private final String defaultMessage;
    private final int httpStatus;

    S4ErrorCode(String code, String defaultMessage, int httpStatus) {
        this.code = code;
        this.defaultMessage = defaultMessage;
        this.httpStatus = httpStatus;
    }

    public String getCode() {
        return code;
    }

    public String getDefaultMessage() {
        return defaultMessage;
    }

    public int getHttpStatus() {
        return httpStatus;
    }
}
