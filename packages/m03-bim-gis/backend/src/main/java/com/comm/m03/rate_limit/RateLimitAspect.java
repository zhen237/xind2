package com.comm.m03.rate_limit;

import com.comm.common.Result;
import com.google.common.util.concurrent.RateLimiter;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;
import java.util.concurrent.ConcurrentHashMap;

@Aspect
@Component
public class RateLimitAspect {

    /**
     * 总开关：生产默认开启。集成测试通过 test 资源配置 rate-limit.enabled=false 关闭，
     * 避免 MockMvc 连续请求触发令牌桶误拒（测试本身不应受限流影响）。
     */
    @Value("${rate-limit.enabled:true}")
    private boolean enabled;

    private final ConcurrentHashMap<String, RateLimiter> limiters = new ConcurrentHashMap<>();

    @Around("@annotation(rateLimit)")
    public Object around(ProceedingJoinPoint point, RateLimit rateLimit) throws Throwable {
        if (!enabled) {
            return point.proceed();
        }
        MethodSignature signature = (MethodSignature) point.getSignature();
        Method method = signature.getMethod();
        String key = method.getDeclaringClass().getName() + "." + method.getName();

        RateLimiter limiter = limiters.computeIfAbsent(key,
                k -> RateLimiter.create(rateLimit.permitsPerSecond()));

        if (!limiter.tryAcquire()) {
            return Result.error(rateLimit.message());
        }
        return point.proceed();
    }
}
