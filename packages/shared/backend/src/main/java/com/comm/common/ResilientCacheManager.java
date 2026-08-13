package com.comm.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;

import java.time.Duration;
import java.util.Collection;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 韧性缓存管理器：优先使用 Redis，Redis 不可达时自动降级到内存缓存，恢复后自动切回。
 *
 * 设计意图（解决"Redis 条件化降级"遗留项）：
 * 1. 启动探测一次 Redis 连通性，若不可达则直接进入降级模式，应用不会因为 Redis 缺失而启动失败或请求打挂。
 * 2. 运行中按固定间隔（默认 30s）探活；Redis 恢复后自动切回 Redis 缓存。
 * 3. 降级期间使用进程内 ConcurrentMap 缓存，保证业务连续性（单实例 MVP 场景足够）。
 *
 * 注意：降级模式下的内存缓存无 TTL、不跨实例共享，这是"条件降级"的有意取舍，而非生产级分布式缓存。
 */
public class ResilientCacheManager implements CacheManager {

    private static final Logger log = LoggerFactory.getLogger(ResilientCacheManager.class);

    private final CacheManager redisManager;
    private final CacheManager memoryManager;
    private final RedisConnectionFactory factory;
    private final AtomicBoolean degraded = new AtomicBoolean(false);
    private volatile long lastProbe = 0;
    private final long probeIntervalMillis;

    public ResilientCacheManager(CacheManager redisManager,
                                 CacheManager memoryManager,
                                 RedisConnectionFactory factory) {
        this(redisManager, memoryManager, factory, Duration.ofSeconds(30));
    }

    public ResilientCacheManager(CacheManager redisManager,
                                 CacheManager memoryManager,
                                 RedisConnectionFactory factory,
                                 Duration probeInterval) {
        this.redisManager = redisManager;
        this.memoryManager = memoryManager;
        this.factory = factory;
        this.probeIntervalMillis = probeInterval.toMillis();
        if (!redisReachable()) {
            degraded.set(true);
            log.warn("[Cache] 启动探测 Redis 不可达，已降级到内存缓存（功能可用，但不跨实例共享）");
        } else {
            log.info("[Cache] Redis 连接正常，使用 Redis 缓存");
        }
    }

    @Override
    public Cache getCache(String name) {
        if (degraded.get()) {
            return memoryManager.getCache(name);
        }
        // 周期性探活：到达间隔则检查 Redis，必要时切换降级/恢复状态
        if (System.currentTimeMillis() - lastProbe > probeIntervalMillis) {
            if (!redisReachable()) {
                if (degraded.compareAndSet(false, true)) {
                    log.warn("[Cache] 运行中探测 Redis 不可达，已降级到内存缓存");
                }
                return memoryManager.getCache(name);
            } else if (degraded.compareAndSet(true, false)) {
                log.info("[Cache] Redis 已恢复，切回 Redis 缓存");
            }
        }
        try {
            Cache cache = redisManager.getCache(name);
            if (cache == null) {
                degraded.set(true);
                return memoryManager.getCache(name);
            }
            return cache;
        } catch (RedisConnectionFailureException ex) {
            if (degraded.compareAndSet(false, true)) {
                log.warn("[Cache] 访问 Redis 缓存失败，已降级到内存缓存: {}", ex.getMessage());
            }
            return memoryManager.getCache(name);
        }
    }

    @Override
    public Collection<String> getCacheNames() {
        return degraded.get() ? memoryManager.getCacheNames() : redisManager.getCacheNames();
    }

    private boolean redisReachable() {
        lastProbe = System.currentTimeMillis();
        try (RedisConnection conn = factory.getConnection()) {
            conn.ping();
            return true;
        } catch (Exception ex) {
            return false;
        }
    }
}
