package com.comm.s3.cache;

import com.comm.s3.entity.S3DesignData;
import com.comm.s3.entity.S3ReviewTask;
import com.comm.s3.service.S3DesignDataService;
import com.comm.s3.service.S3ReviewTaskService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * S1 设计数据缓存服务（B-1 需求：三级存储 Redis → 内存 Map → MySQL）。
 *
 * 设计要点：
 * 1. 持久化主键：以 designTaskId（图纸标识）为持久化主键，同时按 taskId 建快速索引，
 *    满足"同一份图纸重复提交复用"与"按任务读取原始设计数据"双重需求。
 * 2. 三级存储读取优先级：Redis → 内存 ConcurrentHashMap → MySQL（s3_design_data 表）。
 *    Redis 可用时优先；Redis 不可用时回退内存；内存也无数据时从 MySQL 恢复原始图纸，
 *    恢复后回填内存（及 Redis，若可用），保证后续读取命中。
 * 3. Redis 优先 + 内存兜底降级：Redis 可用时读写 Redis（跨重启持久化）；
 *    Redis 不可用时（未安装/宕机/网络异常）自动切回内存 ConcurrentHashMap，应用不崩溃。
 * 4. MySQL 永久落库：无论走 Redis 还是内存模式，S1 图纸接收完成后都【同步写入 MySQL】，
 *    保证原始图纸数据永久留存，服务重启后仍可从数据库读出（验收核心）。
 * 5. TTL 自动过期：Redis 默认 168 小时（7 天），到期自动清理过期图纸缓存（MySQL 层不失效）。
 * 6. 序列化兼容：依赖 RedisConfig 的 Jackson JSON 序列化，反序列化产物与原 LinkedHashMap 结构一致。
 */
@Service
public class DesignDataCacheService {

    private static final Logger log = LoggerFactory.getLogger(DesignDataCacheService.class);
    private static final String KEY_TASK = "s3:design:task:";
    private static final String KEY_DTASK = "s3:design:dtask:";

    private final RedisTemplate<String, Object> redisTemplate;
    /** 内存兜底：taskId -> designData（Redis 不可用时使用，重启即丢，与原行为一致） */
    private final Map<Long, Map<String, Object>> memoryFallback = new ConcurrentHashMap<>();
    /** MySQL 持久层服务（第三级存储） */
    private final S3DesignDataService designDataService;
    /** 任务服务：用于由 taskId 反查 designTaskId，再从 MySQL 恢复图纸 */
    private final S3ReviewTaskService taskService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private final boolean enabled;
    private final long ttlHours;
    private volatile boolean redisAvailable = false;

    public DesignDataCacheService(RedisTemplate<String, Object> redisTemplate,
                                  S3DesignDataService designDataService,
                                  S3ReviewTaskService taskService,
                                  @Value("${s3.redis.enabled:true}") boolean enabled,
                                  @Value("${s3.redis.ttl-hours:168}") long ttlHours) {
        this.redisTemplate = redisTemplate;
        this.designDataService = designDataService;
        this.taskService = taskService;
        this.enabled = enabled;
        this.ttlHours = ttlHours;
        this.redisAvailable = probe();
    }

    /** 启动时探测 Redis 是否可达；不可达则标记为不可用并降级内存模式（不抛异常，保证应用可启动） */
    private boolean probe() {
        if (!enabled) {
            log.warn("[DesignDataCache] Redis 已通过配置禁用(s3.redis.enabled=false)，使用内存兜底模式");
            return false;
        }
        try {
            String pong = redisTemplate.getConnectionFactory().getConnection().ping();
            boolean ok = "PONG".equalsIgnoreCase(pong);
            log.info("[DesignDataCache] Redis 连接探测结果: {} ({})", ok ? "可用" : "不可用", pong);
            return ok;
        } catch (Exception e) {
            log.warn("[DesignDataCache] Redis 不可用，已降级为内存兜底模式（重启后缓存丢失，将回退 MySQL 恢复）。原因: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 存储设计数据：
     *  - 内存兜底强写；
     *  - Redis 可用时按 taskId 与 designTaskId 双键持久化（带 TTL）；
     *  - 【第三级】无论 Redis 或内存模式，均同步写入 MySQL 永久落库（失败仅告警，不波及主流程）。
     */
    public void store(Long taskId, String designTaskId, Map<String, Object> data) {
        if (taskId != null) {
            memoryFallback.put(taskId, data);
        }
        if (redisAvailable) {
            try {
                Duration ttl = Duration.ofHours(ttlHours);
                if (taskId != null) {
                    redisTemplate.opsForValue().set(KEY_TASK + taskId, data, ttl);
                }
                if (designTaskId != null && !designTaskId.trim().isEmpty()) {
                    redisTemplate.opsForValue().set(KEY_DTASK + designTaskId, data, ttl);
                }
            } catch (Exception e) {
                log.warn("[DesignDataCache] Redis 写入失败，保留内存兜底。原因: {}", e.getMessage());
                redisAvailable = false;
            }
        }
        // 第三级：MySQL 永久落库（与 Redis/内存模式无关，始终执行）
        if (designTaskId != null && !designTaskId.trim().isEmpty()) {
            try {
                designDataService.saveDesignData(designTaskId, taskId, data);
            } catch (Exception e) {
                log.error("[DesignDataCache] MySQL 持久化失败(不影响主流程): {}", e.getMessage());
            }
        }
    }

    /**
     * 按 taskId 读取（三级）：Redis → 内存 → MySQL 恢复。
     * 从 MySQL 恢复的数据会回填内存（及 Redis，若可用），保证后续读取命中。
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getByTaskId(Long taskId) {
        if (taskId == null) return null;
        if (redisAvailable) {
            try {
                Object o = redisTemplate.opsForValue().get(KEY_TASK + taskId);
                if (o instanceof Map) {
                    Map<String, Object> m = (Map<String, Object>) o;
                    memoryFallback.put(taskId, m);
                    return m;
                }
            } catch (Exception e) {
                log.warn("[DesignDataCache] Redis 读取失败，降级内存兜底。原因: {}", e.getMessage());
                redisAvailable = false;
            }
        }
        Map<String, Object> mem = memoryFallback.get(taskId);
        if (mem != null) {
            return mem;
        }
        // 第三级：MySQL 恢复
        Map<String, Object> db = recoverByTaskId(taskId);
        if (db != null) {
            memoryFallback.put(taskId, db);
            if (redisAvailable) {
                try {
                    redisTemplate.opsForValue().set(KEY_TASK + taskId, db, Duration.ofHours(ttlHours));
                } catch (Exception e) {
                    redisAvailable = false;
                }
            }
            return db;
        }
        return null;
    }

    /**
     * 按 taskId 读取并返回数据来源（供 getDesignMeta 标识数据源）：
     * 返回 source ∈ {REDIS, MEMORY, DATABASE, NONE}。
     */
    @SuppressWarnings("unchecked")
    public LookupResult getByTaskIdWithSource(Long taskId) {
        if (taskId == null) return new LookupResult(null, "NONE");
        if (redisAvailable) {
            try {
                Object o = redisTemplate.opsForValue().get(KEY_TASK + taskId);
                if (o instanceof Map) {
                    Map<String, Object> m = (Map<String, Object>) o;
                    memoryFallback.put(taskId, m);
                    return new LookupResult(m, "REDIS");
                }
            } catch (Exception e) {
                log.warn("[DesignDataCache] Redis 读取失败，降级内存兜底。原因: {}", e.getMessage());
                redisAvailable = false;
            }
        }
        Map<String, Object> mem = memoryFallback.get(taskId);
        if (mem != null) {
            return new LookupResult(mem, "MEMORY");
        }
        Map<String, Object> db = recoverByTaskId(taskId);
        if (db != null) {
            memoryFallback.put(taskId, db);
            if (redisAvailable) {
                try {
                    redisTemplate.opsForValue().set(KEY_TASK + taskId, db, Duration.ofHours(ttlHours));
                } catch (Exception e) {
                    redisAvailable = false;
                }
            }
            return new LookupResult(db, "DATABASE");
        }
        return new LookupResult(null, "NONE");
    }

    /**
     * 按 designTaskId 读取（用于重复提交复用 / 跨重启恢复）：
     * Redis → 内存 → MySQL（只读恢复，不回填，避免 taskId 键歧义）。
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getByDesignTaskId(String designTaskId) {
        if (designTaskId == null || designTaskId.trim().isEmpty()) return null;
        if (redisAvailable) {
            try {
                Object o = redisTemplate.opsForValue().get(KEY_DTASK + designTaskId);
                if (o instanceof Map) {
                    return (Map<String, Object>) o;
                }
            } catch (Exception e) {
                log.warn("[DesignDataCache] Redis(按designTaskId)读取失败，降级内存兜底。原因: {}", e.getMessage());
                redisAvailable = false;
            }
        }
        for (Map<String, Object> v : memoryFallback.values()) {
            Object dd = v.get("design_data");
            if (dd instanceof Map) {
                Object id = ((Map<?, ?>) dd).get("designTaskId");
                if (designTaskId.equals(String.valueOf(id))) {
                    return v;
                }
            }
        }
        // 第三级：MySQL 恢复
        return recoverByDesignTaskId(designTaskId);
    }

    /** 同一份图纸（designTaskId）是否已在缓存中（用于重复提交命中判断） */
    public boolean existsByDesignTaskId(String designTaskId) {
        return getByDesignTaskId(designTaskId) != null;
    }

    /** 当前是否使用 Redis 持久层（供前端/日志判断数据来源） */
    public boolean isRedisAvailable() {
        return redisAvailable;
    }

    /** 由 taskId 反查 designTaskId，再从 MySQL 恢复图纸原始数据 */
    private Map<String, Object> recoverByTaskId(Long taskId) {
        try {
            S3ReviewTask task = taskService.getById(taskId);
            if (task == null || task.getDesignTaskId() == null) {
                return null;
            }
            return recoverByDesignTaskId(task.getDesignTaskId());
        } catch (Exception e) {
            log.error("[DesignDataCache] 由 taskId 反查 designTaskId 失败 taskId={}: {}", taskId, e.getMessage());
            return null;
        }
    }

    /** 从 MySQL(s3_design_data) 恢复图纸原始数据；恢复时打印明确日志（需求6） */
    @SuppressWarnings("unchecked")
    private Map<String, Object> recoverByDesignTaskId(String designTaskId) {
        if (designTaskId == null || designTaskId.trim().isEmpty()) {
            return null;
        }
        try {
            S3DesignData row = designDataService.getByDesignTaskId(designTaskId);
            if (row == null || row.getDesignDataJson() == null) {
                return null;
            }
            Map<String, Object> m = objectMapper.readValue(row.getDesignDataJson(), Map.class);
            log.warn("[DesignDataCache] 从数据库(s3_design_data)恢复图纸原始数据 designTaskId={}", designTaskId);
            return m;
        } catch (Exception e) {
            log.error("[DesignDataCache] 从数据库恢复图纸数据失败 designTaskId={}: {}", designTaskId, e.getMessage());
            return null;
        }
    }

    /** 读取结果载体：携带数据来源，供数据源标识使用 */
    public static class LookupResult {
        private final Map<String, Object> data;
        private final String source; // REDIS / MEMORY / DATABASE / NONE

        public LookupResult(Map<String, Object> data, String source) {
            this.data = data;
            this.source = source;
        }

        public Map<String, Object> getData() {
            return data;
        }

        public String getSource() {
            return source;
        }
    }
}
