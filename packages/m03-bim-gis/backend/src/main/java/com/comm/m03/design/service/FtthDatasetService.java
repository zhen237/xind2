package com.comm.m03.design.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * FTTH 数据集业务层：读取 + 「一键同步」上传编排。
 *
 * 上传链路的四道保险（与 design 上传链保持同一套工程约束）：
 * <ol>
 *   <li><b>完整性</b>：对 HTTP 原始 body 字节做 SHA-256，与请求头 X-Payload-Sha256 比对。
 *       用原始字节而非序列化后的对象，规避 Python / Java 的 JSON 规范化差异。</li>
 *   <li><b>幂等</b>：摘要与上次上传一致则跳过写盘，重发不会产生副作用。</li>
 *   <li><b>原子写</b>：.tmp + move，前端不会读到半截文件。</li>
 *   <li><b>回环校验</b>：写完立刻回读，比对箱体/缆/站点计数，不一致直接抛错。</li>
 * </ol>
 */
@Slf4j
@Service
public class FtthDatasetService {

    private final ObjectMapper mapper;
    private final FtthDatasetStore store;
    /** 按 tag 加锁：同一数据集的并发上传串行化，不同数据集互不阻塞。 */
    private final Map<String, Object> tagLocks = new ConcurrentHashMap<>();

    public FtthDatasetService(ObjectMapper mapper, FtthDatasetStore store) {
        this.mapper = mapper;
        this.store = store;
    }

    public boolean isValidTag(String tag) {
        return tag != null && tag.matches("^[A-Za-z0-9._-]{1,64}$");
    }

    public JsonNode read(String tag, String fileName) {
        return store.readJson(tag, fileName);
    }

    /**
     * 接收 QGIS 插件推送的 FTTH 三件套并落盘。
     *
     * @param rawBody   HTTP 原始请求体（{data, validation, plan, uploadId, label, source, client}）
     * @param clientSha 请求头 X-Payload-Sha256，可空（空则跳过完整性比对）
     * @throws IllegalArgumentException 载荷非法（400）
     * @throws IllegalStateException    写盘校验失败（500）
     */
    public Map<String, Object> upload(String tag, byte[] rawBody, String clientSha) throws Exception {
        String serverSha = sha256Hex(rawBody);
        if (clientSha != null && !clientSha.isBlank() && !clientSha.equalsIgnoreCase(serverSha)) {
            throw new IllegalArgumentException(
                    "载荷完整性校验失败：客户端摘要 " + clientSha + " ≠ 服务端 " + serverSha + "（传输过程中被截断或改写）");
        }

        JsonNode root = mapper.readTree(rawBody);
        JsonNode data = root.get("data");
        if (data == null || !data.isObject()) {
            throw new IllegalArgumentException("缺少 data 字段（应为 ftth-data.json 的完整内容）");
        }
        if (!data.path("boites").isArray()) {
            throw new IllegalArgumentException("data.boites 缺失或不是数组，疑似非 FTTH 导出产物");
        }
        String uploadId = text(root, "uploadId", null);

        Object lock = tagLocks.computeIfAbsent(tag, k -> new Object());
        synchronized (lock) {
            JsonNode meta = store.readJson(tag, FtthDatasetStore.FILE_META);
            if (meta != null && serverSha.equalsIgnoreCase(meta.path("sha256").asText())) {
                // 幂等命中：仅当磁盘上的 data 与本次 payload 计数一致才跳过写盘。
                // 否则（如有人手改了文件又把原内容推回来）强制重写，保证后端为准源。
                JsonNode onDisk = store.readJson(tag, FtthDatasetStore.FILE_DATA);
                if (onDisk != null && sameCounts(counts(onDisk), counts(data))) {
                    log.info("FTTH 同步幂等命中 tag={} sha={}", tag, shortSha(serverSha));
                    Map<String, Object> r = baseResult(tag, serverSha, uploadId, true);
                    r.put("written", Collections.emptyList());
                    r.put("counts", counts(data));
                    r.put("message", "内容与上次同步完全一致，已跳过写盘（幂等命中）");
                    return r;
                }
            }

            List<String> written = new ArrayList<>();
            store.writeJson(tag, FtthDatasetStore.FILE_DATA, data);
            written.add(FtthDatasetStore.FILE_DATA);
            if (isObject(root.get("validation"))) {
                store.writeJson(tag, FtthDatasetStore.FILE_VALIDATION, root.get("validation"));
                written.add(FtthDatasetStore.FILE_VALIDATION);
            }
            if (isObject(root.get("plan"))) {
                store.writeJson(tag, FtthDatasetStore.FILE_PLAN, root.get("plan"));
                written.add(FtthDatasetStore.FILE_PLAN);
            }

            Map<String, Integer> expect = counts(data);
            JsonNode back = store.readJson(tag, FtthDatasetStore.FILE_DATA);
            if (back == null) {
                throw new IllegalStateException("写盘校验失败：回读 ftth-data.json 为空，检查 " + store.baseDir() + " 写权限");
            }
            Map<String, Integer> actual = counts(back);
            if (!expect.equals(actual)) {
                throw new IllegalStateException("写盘校验失败：期望 " + expect + "，回读得到 " + actual);
            }

            store.upsertIndex(tag,
                    text(root, "label", tag),
                    text(root, "source", data.path("source").asText(tag)),
                    data.path("generated_at").asText(LocalDateTime.now().format(FtthDatasetStore.TS)),
                    data.get("summary"));

            writeMeta(tag, uploadId, serverSha, rawBody.length, text(root, "client", "unknown"), written, actual);

            log.info("FTTH 同步成功 tag={} files={} counts={} sha={}", tag, written, actual, shortSha(serverSha));
            Map<String, Object> r = baseResult(tag, serverSha, uploadId, false);
            r.put("written", written);
            r.put("counts", actual);
            r.put("message", "同步成功，S1 前端刷新即可看到最新成果");
            return r;
        }
    }

    private void writeMeta(String tag, String uploadId, String sha, int bytes, String client,
                           List<String> written, Map<String, Integer> counts) throws Exception {
        ObjectNode m = mapper.createObjectNode();
        m.put("tag", tag);
        m.put("uploadId", uploadId);
        m.put("sha256", sha);
        m.put("bytes", bytes);
        m.put("client", client);
        m.put("uploaded_at", LocalDateTime.now().format(FtthDatasetStore.TS));
        ArrayNode files = mapper.createArrayNode();
        written.forEach(files::add);
        m.set("files", files);
        m.set("counts", mapper.valueToTree(counts));
        store.writeJson(tag, FtthDatasetStore.FILE_META, m);
    }

    private Map<String, Object> baseResult(String tag, String sha, String uploadId, boolean idempotent) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("tag", tag);
        r.put("sha256", sha);
        r.put("uploadId", uploadId);
        r.put("idempotent", idempotent);
        r.put("dataDir", store.baseDir().toString());
        return r;
    }

    /** 三类核心要素计数，用于写盘回环校验与回执展示。 */
    private Map<String, Integer> counts(JsonNode data) {
        Map<String, Integer> c = new LinkedHashMap<>();
        c.put("boites", size(data.get("boites")));
        c.put("cables", size(data.get("cables")));
        c.put("sites", size(data.get("sites")));
        c.put("pm", size(data.get("pm_list")));
        return c;
    }

    private int size(JsonNode n) {
        return (n != null && n.isArray()) ? n.size() : 0;
    }

    private boolean sameCounts(Map<String, Integer> a, Map<String, Integer> b) {
        return a != null && a.equals(b);
    }

    private boolean isObject(JsonNode n) {
        return n != null && n.isObject() && !n.isNull();
    }

    private String text(JsonNode node, String field, String fallback) {
        JsonNode n = node.get(field);
        return (n == null || n.isNull() || n.asText().isEmpty()) ? fallback : n.asText();
    }

    private String shortSha(String sha) {
        return sha.length() > 12 ? sha.substring(0, 12) : sha;
    }

    private String sha256Hex(byte[] bytes) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder sb = new StringBuilder(digest.length * 2);
        for (byte b : digest) {
            sb.append(Character.forDigit((b >> 4) & 0xF, 16)).append(Character.forDigit(b & 0xF, 16));
        }
        return sb.toString();
    }
}
