package com.comm.m03.rate_limit;

import java.lang.annotation.*;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RateLimit {
    double permitsPerSecond() default 10.0;
    String message() default "请求过于频繁，请稍后再试";
}
