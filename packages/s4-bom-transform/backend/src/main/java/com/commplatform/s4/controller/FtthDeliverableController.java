package com.commplatform.s4.controller;

import com.commplatform.s4.config.S4Config;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.util.*;

/**
 * [S4-S1-迁移 §5.2 2026-09-22] FTTH 交付物上传式 REST API。
 * <p>
 * 接收前端上传的 8 个 .dbf 文件（IMB/SITE/BOITE/CABLE/PTECH/INFRASTRUCTURE/ZNRO/ZPM），
 * 转发到 Python 引擎 {@code /api/v1/ftth/upload} 复用
 * {@code qgis-plugin/ftth.export_runner.export_from_dbf_single_workbook} 生成合并工作簿，
 * 再由本 controller 提供下载端点。
 * </p>
 * <p>
 * 端点前缀: {@code /api/s4/ftth}
 * </p>
 *
 * @see com.commplatform.s4.controller.BomController 工程量报表端点风格一致
 */
@Slf4j
@RestController
@RequestMapping("/api/s4/ftth")
@RequiredArgsConstructor
public class FtthDeliverableController {

    private final S4Config s4Config;
    private final RestTemplate restTemplate;

    /** Python 引擎 FTTH 路由前缀（与 engine/app/routers/ftth.py 对齐）。 */
    private static final String ENGINE_FTTH_PREFIX = "/api/v1/ftth";

    /** 期望的 8 层 .dbf 文件名清单（与 qgis-plugin/ftth/field_map.LAYER_FILE_PREFIX 对齐）。 */
    private static final List<String> EXPECTED_LAYERS = List.of(
            "IMB", "SITE", "BOITE", "CABLE",
            "PTECH", "INFRASTRUCTURE", "ZNRO", "ZPM"
    );

    /**
     * 上传 8 个 .dbf → 触发 Python 引擎复用 {@code qgis-plugin/ftth.export_runner} 生成合并工作簿。
     * <p>
     * multipart 字段名：每个文件以 layer 名作为 part 名（{@code IMB / SITE / BOITE / ...}），
     * 兼容也接受任意 part 名（Python 端按文件名后缀归一化）。
     * </p>
     *
     * @param files 8 个 .dbf multipart 文件
     * @return Python 引擎返回的元数据 JSON（taskId / sheetCount / sheetNames / downloadUrl 等）
     */
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Map<String, Object>> upload(@RequestParam("files") MultipartFile[] files) {
        if (files == null || files.length == 0) {
            throw new IllegalArgumentException("至少上传 1 个 .dbf 文件（需要完整 8 层）");
        }
        // 校验 8 层齐全性（按文件名去后缀大写匹配）
        Set<String> provided = new HashSet<>();
        for (MultipartFile f : files) {
            String name = f.getOriginalFilename();
            if (name == null) continue;
            String stem = stripExt(name).toUpperCase(Locale.ROOT);
            provided.add(stem);
        }
        List<String> missing = new ArrayList<>();
        for (String layer : EXPECTED_LAYERS) {
            if (!provided.contains(layer)) missing.add(layer);
        }
        if (!missing.isEmpty()) {
            throw new IllegalArgumentException(
                    "缺少 .dbf 文件：" + String.join(", ", missing) +
                            "。需要完整 8 层：" + String.join(", ", EXPECTED_LAYERS));
        }

        // 构造 multipart 转发到 Python 引擎
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        for (MultipartFile f : files) {
            byte[] bytes;
            try {
                bytes = f.getBytes();
            } catch (Exception e) {
                throw new RuntimeException("读取上传文件失败：" + f.getOriginalFilename(), e);
            }
            // 用 ByteArrayResource 让 RestTemplate 把字节作为文件 part 转发
            ByteArrayResource resource = new ByteArrayResource(bytes) {
                @Override
                public String getFilename() {
                    return f.getOriginalFilename();
                }
            };
            body.add("files", resource);
        }

        String engineUrl = s4Config.getEngine().getUrl() + ENGINE_FTTH_PREFIX + "/upload";
        log.info("[ftth] 转发 {} 个 .dbf 到 Python 引擎：{}", files.length, engineUrl);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        HttpEntity<MultiValueMap<String, Object>> req = new HttpEntity<>(body, headers);

        @SuppressWarnings("unchecked")
        Map<String, Object> engineResp = restTemplate.postForObject(engineUrl, req, Map.class);
        if (engineResp == null) {
            throw new RuntimeException("Python 引擎返回空响应");
        }
        // 把 Python 引擎返回的相对 URL 改成经 Spring Boot 暴露的 URL
        Object taskIdObj = engineResp.get("taskId");
        if (taskIdObj != null) {
            String taskId = taskIdObj.toString();
            engineResp.put("downloadUrl",    "/api/s4/ftth/" + taskId + "/download");
            engineResp.put("validationUrl",  "/api/s4/ftth/" + taskId + "/validation");
            engineResp.put("jsonUrl",        "/api/s4/ftth/" + taskId + "/json");
        }
        log.info("[ftth] 导出成功：taskId={} sheetCount={}",
                engineResp.get("taskId"), engineResp.get("sheetCount"));
        return ResponseEntity.ok(engineResp);
    }

    /**
     * 下载 FTTH 合并工作簿 xlsx（透传 Python 引擎产物）。
     */
    @GetMapping("/{taskId}/download")
    public ResponseEntity<byte[]> download(@PathVariable String taskId) {
        String url = s4Config.getEngine().getUrl() + ENGINE_FTTH_PREFIX + "/" + taskId + "/download";
        log.info("[ftth] 下载工作簿：taskId={}", taskId);
        byte[] bytes = restTemplate.getForObject(url, byte[].class);
        if (bytes == null || bytes.length == 0) {
            throw new RuntimeException("Python 引擎未返回 xlsx 内容（taskId=" + taskId + "）");
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
        headers.setContentDisposition(ContentDisposition.attachment()
                .filename(taskId + "_FTTH_Deliverables.xlsx")
                .build());
        return new ResponseEntity<>(bytes, headers, HttpStatus.OK);
    }

    /**
     * 查询 FTTH 导出任务元数据（sheet 列表 / 8 层记录数 / summary）。
     */
    @GetMapping("/{taskId}")
    public ResponseEntity<Map<String, Object>> info(@PathVariable String taskId) {
        String url = s4Config.getEngine().getUrl() + ENGINE_FTTH_PREFIX + "/" + taskId;
        @SuppressWarnings("unchecked")
        Map<String, Object> engineResp = restTemplate.getForObject(url, Map.class);
        if (engineResp == null) {
            throw new RuntimeException("Python 引擎未返回任务元数据（taskId=" + taskId + "）");
        }
        return ResponseEntity.ok(engineResp);
    }

    /**
     * 下载 FTTH 自检报告 JSON。
     */
    @GetMapping("/{taskId}/validation")
    public ResponseEntity<byte[]> validation(@PathVariable String taskId) {
        String url = s4Config.getEngine().getUrl() + ENGINE_FTTH_PREFIX + "/" + taskId + "/validation";
        byte[] bytes = restTemplate.getForObject(url, byte[].class);
        if (bytes == null || bytes.length == 0) {
            throw new RuntimeException("Python 引擎未返回自检报告（taskId=" + taskId + "）");
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setContentDisposition(ContentDisposition.attachment()
                .filename(taskId + "_ftth-validation.json").build());
        return new ResponseEntity<>(bytes, headers, HttpStatus.OK);
    }

    /**
     * 下载 FTTH 前端 JSON 数据。
     */
    @GetMapping("/{taskId}/json")
    public ResponseEntity<byte[]> ftthJson(@PathVariable String taskId) {
        String url = s4Config.getEngine().getUrl() + ENGINE_FTTH_PREFIX + "/" + taskId + "/json";
        byte[] bytes = restTemplate.getForObject(url, byte[].class);
        if (bytes == null || bytes.length == 0) {
            throw new RuntimeException("Python 引擎未返回 ftth-data JSON（taskId=" + taskId + "）");
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setContentDisposition(ContentDisposition.attachment()
                .filename(taskId + "_ftth-data.json").build());
        return new ResponseEntity<>(bytes, headers, HttpStatus.OK);
    }

    /** 去掉文件名后缀（.dbf / .DBF / .shp 等）。 */
    private static String stripExt(String name) {
        int dot = name.lastIndexOf('.');
        return dot > 0 ? name.substring(0, dot) : name;
    }
}
