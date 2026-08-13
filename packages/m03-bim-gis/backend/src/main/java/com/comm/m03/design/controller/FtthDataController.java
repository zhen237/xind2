package com.comm.m03.design.controller;

import com.comm.common.Result;
import com.comm.m03.design.service.FtthDatasetService;
import com.comm.m03.design.service.FtthDatasetStore;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * FTTH 数据集接口（契约 C 补充：S1 设计成果交移的 FTTH 维度）。
 *
 * 数据来源：QGIS 插件 ftth 导出链生成的 ftth-data/validation/plan.json，
 * 目录由 {@code ftth.data-dir} 配置（默认 {@code ../frontend/public/datasets}，
 * 可用环境变量 {@code FTTH_DATA_DIR} 覆盖）。
 *
 * 端点：
 * <pre>
 *   GET  /api/m03/ftth              数据集列表(index.json)
 *   GET  /api/m03/ftth/{tag}        三件套聚合 {data, validation, plan}
 *   GET  /api/m03/ftth/{tag}/{type} 单件 type∈{data|validation|plan}
 *   POST /api/m03/ftth/{tag}        插件一键同步：接收三件套并落盘 + 更新索引
 * </pre>
 *
 * 鉴权：GET 内网免鉴权（只读）；POST 必须携带 X-API-Key，
 * 见 {@link com.comm.m03.config.DesignApiKeyInterceptor} 与 WebConfig 的路径注册。
 */
@Slf4j
@RestController
@RequestMapping("/api/m03/ftth")
public class FtthDataController {

    private final FtthDatasetService service;

    public FtthDataController(FtthDatasetService service) {
        this.service = service;
    }

    @GetMapping
    public Result<JsonNode> listDatasets() {
        JsonNode node = service.read(null, FtthDatasetStore.FILE_INDEX);
        if (node == null) {
            return Result.notFound("未找到 datasets/index.json，请先运行 QGIS 插件 ftth 导出链生成真实数据集");
        }
        return Result.success(node);
    }

    @GetMapping("/{tag}")
    public Result<Map<String, JsonNode>> getDataset(@PathVariable String tag) {
        if (!service.isValidTag(tag)) {
            return Result.badRequest("非法的数据集标识: " + tag);
        }
        JsonNode data = service.read(tag, FtthDatasetStore.FILE_DATA);
        if (data == null) {
            return Result.notFound("未找到数据集: " + tag);
        }
        Map<String, JsonNode> bundle = new LinkedHashMap<>();
        bundle.put("data", data);
        bundle.put("validation", service.read(tag, FtthDatasetStore.FILE_VALIDATION));
        bundle.put("plan", service.read(tag, FtthDatasetStore.FILE_PLAN));
        return Result.success(bundle);
    }

    @GetMapping("/{tag}/{type}")
    public Result<JsonNode> getDatasetPart(@PathVariable String tag, @PathVariable String type) {
        if (!service.isValidTag(tag)) {
            return Result.badRequest("非法的数据集标识: " + tag);
        }
        String file = fileOf(type);
        if (file == null) {
            return Result.badRequest("未知的 dataType: " + type + "（应为 data|validation|plan）");
        }
        JsonNode node = service.read(tag, file);
        if (node == null) {
            return Result.notFound("未找到 " + tag + " 的 " + type + " 数据");
        }
        return Result.success(node);
    }

    /**
     * 一键同步：QGIS 插件把 FTTH 导出成果直接推到 S1，免去手工拷贝 JSON + 重建前端。
     *
     * 请求体：{ data, validation?, plan?, uploadId?, label?, source?, client? }
     * 请求头：X-API-Key（必须）、X-Payload-Sha256（可选，做完整性校验）
     */
    @PostMapping(value = "/{tag}", consumes = MediaType.APPLICATION_JSON_VALUE)
    public Result<Map<String, Object>> uploadDataset(
            @PathVariable String tag,
            @RequestHeader(value = "X-Payload-Sha256", required = false) String clientSha,
            @RequestBody byte[] rawBody) {
        if (!service.isValidTag(tag)) {
            return Result.badRequest("非法的数据集标识: " + tag + "（只允许字母/数字/点/中划线/下划线，≤64 字符）");
        }
        if (rawBody == null || rawBody.length == 0) {
            return Result.badRequest("请求体为空");
        }
        try {
            return Result.success(service.upload(tag, rawBody, clientSha));
        } catch (IllegalArgumentException e) {
            log.warn("FTTH 同步载荷非法 tag={}: {}", tag, e.getMessage());
            return Result.badRequest(e.getMessage());
        } catch (Exception e) {
            log.error("FTTH 同步失败 tag={}", tag, e);
            return Result.error("同步失败: " + e.getMessage());
        }
    }

    private String fileOf(String type) {
        if ("data".equals(type)) {
            return FtthDatasetStore.FILE_DATA;
        }
        if ("validation".equals(type)) {
            return FtthDatasetStore.FILE_VALIDATION;
        }
        if ("plan".equals(type)) {
            return FtthDatasetStore.FILE_PLAN;
        }
        return null;
    }
}
