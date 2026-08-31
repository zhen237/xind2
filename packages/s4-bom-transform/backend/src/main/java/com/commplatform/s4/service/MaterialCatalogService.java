package com.commplatform.s4.service;

import com.commplatform.s4.config.S4Config;
import com.commplatform.s4.exception.S4BusinessException;
import com.commplatform.s4.exception.S4ErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 物料编码库服务 — [FR-2] 从 Python 引擎拉取 material_catalog.json，
 * 内存缓存（TTL 5 分钟），支持按设备类型过滤。
 * <p>引擎不可达时返回上次缓存；无缓存则抛 ENGINE_ERROR。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MaterialCatalogService {

    private static final long CACHE_TTL_MS = 5 * 60 * 1000L;

    private final S4Config s4Config;
    private final RestTemplate restTemplate;

    /** 最后一次成功拉取的完整编码库（结构: {_meta, mappings, siteLevelAuxiliaries}） */
    private volatile Map<String, Object> cachedCatalog = null;
    private volatile long cacheTimestamp = 0L;

    /**
     * 查询物料编码库。
     *
     * @param deviceType 可选，按设备类型过滤 mappings（如 antenna / rru / bbu）；空则返回全量
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getCatalog(String deviceType) {
        Map<String, Object> catalog = ensureCache();
        if (deviceType == null || deviceType.isBlank()) {
            return catalog;
        }

        // 按设备类型过滤 mappings
        Map<String, Object> filtered = new LinkedHashMap<>();
        filtered.put("_meta", catalog.getOrDefault("_meta", Map.of()));
        List<Map<String, Object>> mappings = new ArrayList<>();
        Object raw = catalog.get("mappings");
        if (raw instanceof List<?> list) {
            for (Object o : list) {
                if (o instanceof Map<?, ?> m && deviceType.equals(String.valueOf(m.get("deviceType")))) {
                    mappings.add((Map<String, Object>) m);
                }
            }
        }
        filtered.put("mappings", mappings);
        filtered.put("count", mappings.size());
        filtered.put("deviceType", deviceType);
        return filtered;
    }

    /** 强制刷新缓存（管理用途）。 */
    public Map<String, Object> refresh() {
        cachedCatalog = null;
        cacheTimestamp = 0L;
        return ensureCache();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> ensureCache() {
        Map<String, Object> snapshot = cachedCatalog;
        if (snapshot != null && System.currentTimeMillis() - cacheTimestamp < CACHE_TTL_MS) {
            return snapshot;
        }
        synchronized (this) {
            // double-check：并发场景下另一线程可能已完成刷新
            if (cachedCatalog != null && System.currentTimeMillis() - cacheTimestamp < CACHE_TTL_MS) {
                return cachedCatalog;
            }
            String url = s4Config.getEngine().getUrl() + "/api/v1/bom/catalog";
            try {
                Map<String, Object> resp = restTemplate.getForObject(url, Map.class);
                if (resp == null || !(resp.get("mappings") instanceof List<?>)) {
                    throw new IllegalStateException("引擎返回的编码库结构异常（缺少 mappings）");
                }
                cachedCatalog = resp;
                cacheTimestamp = System.currentTimeMillis();
                log.info("物料编码库已缓存: {} 条映射", ((List<?>) resp.get("mappings")).size());
                return cachedCatalog;
            } catch (S4BusinessException e) {
                throw e;
            } catch (Exception e) {
                log.warn("拉取物料编码库失败: {}", e.getMessage());
                if (cachedCatalog != null) {
                    // 引擎暂时不可达 → 沿用旧缓存（软降级）
                    return cachedCatalog;
                }
                throw new S4BusinessException(S4ErrorCode.ENGINE_ERROR,
                        "物料编码库不可用（引擎不可达且无缓存）: " + e.getMessage(), e);
            }
        }
    }
}
