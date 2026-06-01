package com.comm.m03.common;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
public class Result<T> {
    private int code;
    private String message;
    private T data;

    public Result(int code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> Result<T> success() {
        return new Result<T>(200, "success", null);
    }

    public static <T> Result<T> success(T data) {
        return new Result<T>(200, "success", data);
    }

    public static <T> Result<T> success(String message, T data) {
        return new Result<T>(200, message, data);
    }

    public static <T> Result<T> error(int code, String message) {
        return new Result<T>(code, message, null);
    }

    public static <T> Result<T> error(String message) {
        return new Result<T>(500, message, null);
    }

    public static <T> Result<T> unauthorized(String message) {
        return new Result<T>(401, message, null);
    }

    public static <T> Result<T> forbidden(String message) {
        return new Result<T>(403, message, null);
    }

    public static <T> Result<T> notFound(String message) {
        return new Result<T>(404, message, null);
    }

    public boolean isSuccess() {
        return this.code == 200;
    }
}