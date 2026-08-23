package com.comm.m03.design.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * FTTH 数据集文件仓储层：只负责磁盘 IO（路径解析 / 原子写 / 索引维护），不含业务判断。
 *
 * 目录布局（由 {@code ftth.data-dir} 指定，默认 ../frontend/public/datasets）：
 * <pre>
 *   datasets/
 *     index.json                 数据集清单（前端选择器读它）
 *     {tag}/ftth-data.json       竣工/设计要素
 *     {tag}/ftth-validation.json 数据自检结论
 *     {tag}/ftth-plan.json       规划输入（需求点等）
 *     {tag}/.upload-meta.json    上传元数据（幂等键 / 摘要 / 审计）
 * </pre>
 */
@Slf4j
@Component
public class FtthDatasetStore {

    public static final String FILE_DATA = "ftth-data.json";
    public static final String FILE_VALIDATION = "ftth-validation.json";
    public static final String FILE_PLAN = "ftth-plan.json";
    public static final String FILE_INDEX = "index.json";
    public static final String FILE_META = ".upload-meta.json";

    public static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    private final ObjectMapper mapper;

    @Value("${ftth.data-dir:../frontend/public/datasets}")
    private String dataDir;

    public FtthDatasetStore(ObjectMapper mapper) {
        this.mapper = mapper;
    }

    public Path baseDir() {
        return Paths.get(dataDir).toAbsolutePath().normalize();
    }

    /**
     * 解析数据集内的文件路径，带目录穿越防护。
     *
     * @param tag 数据集标识；null / 空串表示 datasets 根目录
     */
    public Path resolve(String tag, String fileName) {
        Path base = baseDir();
        Path target = (tag == null || tag.isEmpty())
                ? base.resolve(fileName).normalize()
                : base.resolve(tag).resolve(fileName).normalize();
        if (!target.startsWith(base)) {
            throw new IllegalArgumentException("非法路径（越出数据目录）: " + tag + "/" + fileName);
        }
        return target;
    }

    /** 读 JSON；文件不存在或解析失败一律返回 null（调用方决定如何降级）。 */
    public JsonNode readJson(String tag, String fileName) {
        try {
            File f = resolve(tag, fileName).toFile();
            if (!f.exists() || !f.isFile()) {
                return null;
            }
            return mapper.readTree(f);
        } catch (Exception e) {
            log.warn("FTTH 数据读取失败 tag={} file={}: {}", tag, fileName, e.getMessage());
            return null;
        }
    }

    /** 原子写：先落 .tmp 再 move，避免前端 fetch 到写了一半的文件。 */
    public void writeJson(String tag, String fileName, JsonNode node) throws IOException {
        Path target = resolve(tag, fileName);
        Files.createDirectories(target.getParent());
        Path tmp = target.resolveSibling(target.getFileName() + ".tmp");
        byte[] bytes = mapper.writerWithDefaultPrettyPrinter().writeValueAsBytes(node);
        Files.write(tmp, bytes);
        try {
            Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (AtomicMoveNotSupportedException e) {
            Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    /**
     * index.json 单条 upsert：同 tag 覆盖，其余保留，整体按 tag 字典序排列。
     * 用 synchronized 保护，避免多个数据集并发上传时索引互相覆盖。
     */
    public synchronized void upsertIndex(String tag, String label, String source,
                                         String generatedAt, JsonNode summary) throws IOException {
        JsonNode existing = readJson(null, FILE_INDEX);
        ObjectNode index = (existing instanceof ObjectNode) ? (ObjectNode) existing : mapper.createObjectNode();

        List<JsonNode> keep = new ArrayList<>();
        JsonNode arr = index.get("datasets");
        if (arr != null && arr.isArray()) {
            for (JsonNode n : arr) {
                if (!tag.equals(n.path("tag").asText())) {
                    keep.add(n);
                }
            }
        }

        ObjectNode entry = mapper.createObjectNode();
        entry.put("tag", tag);
        entry.put("label", label);
        entry.put("source", source);
        entry.put("generated_at", generatedAt);
        entry.set("summary", summary == null || summary.isNull() ? mapper.createObjectNode() : summary);
        keep.add(entry);
        keep.sort(Comparator.comparing(n -> n.path("tag").asText()));

        ArrayNode out = mapper.createArrayNode();
        keep.forEach(out::add);
        index.put("generated_at", LocalDateTime.now().format(TS));
        index.put("count", out.size());
        index.set("datasets", out);
        writeJson(null, FILE_INDEX, index);
    }
}
