package com.comm.s3.util;

import lombok.extern.slf4j.Slf4j;
import okhttp3.*;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

@Slf4j
public class OkHttpUtil {

    private static final OkHttpClient CLIENT = new OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .connectionPool(new ConnectionPool(5, 5, TimeUnit.MINUTES))
            .build();

    public static String postJson(String url, String json) {
        return postJson(url, json, 60);
    }

    public static String postJson(String url, String json, int timeoutSeconds) {
        OkHttpClient clientWithTimeout = CLIENT.newBuilder()
                .readTimeout(timeoutSeconds, TimeUnit.SECONDS)
                .build();

        RequestBody body = RequestBody.create(json, MediaType.parse("application/json; charset=utf-8"));
        Request request = new Request.Builder()
                .url(url)
                .post(body)
                .header("Content-Type", "application/json; charset=utf-8")
                .build();

        long startTime = System.currentTimeMillis();
        try (Response response = clientWithTimeout.newCall(request).execute()) {
            long duration = System.currentTimeMillis() - startTime;
            log.info("OkHttp post completed, url: {}, duration: {}ms, code: {}", url, duration, response.code());

            if (response.isSuccessful() && response.body() != null) {
                String result = response.body().string();
                log.debug("OkHttp response body length: {}", result != null ? result.length() : 0);
                return result;
            }

            String errorBody = response.body() != null ? response.body().string() : "";
            log.error("OkHttp post failed, url: {}, code: {}, error: {}", url, response.code(), errorBody);

            // 容错原则：引擎返回非成功状态码时，向上抛出明确异常，
            // 交由 ReviewService 将审查任务标记为 FAILED 并在报告中写明对接异常原因，
            // 严禁伪装成 {"code":200,"data":[]} 成功响应（否则任务会被误判为"已完成且无违规"）。
            if (response.code() >= 500) {
                throw new RuntimeException(
                        String.format("Python审查引擎返回服务端错误(HTTP %d)，审查中止；响应: %s",
                                response.code(), errorBody.length() > 300 ? errorBody.substring(0, 300) : errorBody));
            }
            if (response.code() >= 400) {
                throw new RuntimeException(
                        String.format("Python审查引擎返回客户端错误(HTTP %d)，审查中止；响应: %s",
                                response.code(), errorBody.length() > 300 ? errorBody.substring(0, 300) : errorBody));
            }
            // 其他非成功（如 3xx 未重定向）按失败处理
            throw new RuntimeException(String.format("Python审查引擎返回非预期状态码(HTTP %d)", response.code()));
        } catch (IOException e) {
            long duration = System.currentTimeMillis() - startTime;
            log.error("OkHttp post exception, url: {}, duration: {}ms", url, duration, e);

            // 容错原则：连接超时 / 网络异常时抛出明确异常，交由上层标记任务 FAILED，
            // 不得在接口异常时伪装成功。
            throw new RuntimeException(
                    String.format("调用Python审查引擎超时或网络异常(连接失败)，审查中止；url=%s, 耗时=%dms", url, duration), e);
        }
    }

    public static String get(String url) {
        return get(url, 30);
    }

    public static String get(String url, int timeoutSeconds) {
        OkHttpClient clientWithTimeout = CLIENT.newBuilder()
                .readTimeout(timeoutSeconds, TimeUnit.SECONDS)
                .build();

        Request request = new Request.Builder()
                .url(url)
                .get()
                .header("Accept", "application/json; charset=utf-8")
                .build();

        long startTime = System.currentTimeMillis();
        try (Response response = clientWithTimeout.newCall(request).execute()) {
            long duration = System.currentTimeMillis() - startTime;
            log.info("OkHttp get completed, url: {}, duration: {}ms, code: {}", url, duration, response.code());

            if (response.isSuccessful() && response.body() != null) {
                return response.body().string();
            }
            log.error("OkHttp get failed, url: {}, code: {}", url, response.code());
            return null;
        } catch (IOException e) {
            long duration = System.currentTimeMillis() - startTime;
            log.error("OkHttp get exception, url: {}, duration: {}ms", url, duration, e);
            return null;
        }
    }

    public static boolean checkHealth(String url) {
        try {
            OkHttpClient healthClient = CLIENT.newBuilder()
                    .connectTimeout(5, TimeUnit.SECONDS)
                    .readTimeout(5, TimeUnit.SECONDS)
                    .writeTimeout(5, TimeUnit.SECONDS)
                    .build();
            
            Request request = new Request.Builder()
                    .url(url)
                    .get()
                    .build();

            try (Response response = healthClient.newCall(request).execute()) {
                return response.isSuccessful();
            }
        } catch (Exception e) {
            log.warn("Health check failed for: {}", url, e);
            return false;
        }
    }
}
