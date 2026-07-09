"""内存管理器

管理插件内存使用，防止内存泄漏

作者: M03模块开发团队
日期: 2026-07-02
"""

import gc
import sys
import tracemalloc
from typing import Dict, Optional
from collections import OrderedDict

from ..utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)


class MemoryManager:
    """内存管理器"""
    
    def __init__(self, max_cache_size: int = 100):
        self.max_cache_size = max_cache_size
        self._cache = OrderedDict()
        self._lock = None  # 简化版不使用锁
        self._initial_memory = self._get_memory_usage()
        
        # 启动追踪
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """获取当前内存使用情况"""
        current, peak = tracemalloc.get_traced_memory()
        return {
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024,
            'gc_count': gc.get_count()
        }
    
    def cache_get(self, key: str):
        """获取缓存项"""
        if key in self._cache:
            # 移动到末尾 (LRU)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def cache_set(self, key: str, value):
        """设置缓存项"""
        if key in self._cache:
            # 更新并移动到末尾
            self._cache.move_to_end(key)
            self._cache[key] = value
        else:
            # 添加新项
            self._cache[key] = value
            
            # 如果超出限制，删除最久未使用的
            while len(self._cache) > self.max_cache_size:
                self._cache.popitem(last=False)
    
    def cache_delete(self, key: str):
        """删除缓存项"""
        if key in self._cache:
            del self._cache[key]
    
    def cache_clear(self):
        """清空缓存"""
        self._cache.clear()
        gc.collect()
    
    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        return {
            'size': len(self._cache),
            'max_size': self.max_cache_size,
            'utilization': len(self._cache) / self.max_cache_size if self.max_cache_size > 0 else 0
        }
    
    def get_memory_stats(self) -> Dict:
        """获取内存统计"""
        mem = self._get_memory_usage()
        mem['cache_info'] = self.get_cache_info()
        return mem
    
    def force_gc(self) -> Dict:
        """强制垃圾回收"""
        before = self._get_memory_usage()
        collected = gc.collect()
        after = self._get_memory_usage()
        
        return {
            'collected': collected,
            'before': before,
            'after': after,
            'freed_mb': before['current_mb'] - after['current_mb']
        }
    
    def check_memory_threshold(self, threshold_mb: float = 100.0) -> bool:
        """检查内存是否超过阈值"""
        stats = self._get_memory_usage()
        return stats['current_mb'] > threshold_mb
    
    def cleanup_if_needed(self, threshold_mb: float = 100.0):
        """如果内存超过阈值则清理"""
        if self.check_memory_threshold(threshold_mb):
            _logger.warning("内存使用超过 %s MB，执行清理", threshold_mb)
            self.cache_clear()
            self.force_gc()


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self._timings: Dict[str, list] = {}
        self._call_counts: Dict[str, int] = {}
    
    def start_timer(self, operation: str):
        """开始计时"""
        import time
        if operation not in self._timings:
            self._timings[operation] = []
            self._call_counts[operation] = 0
        self._timings[operation].append(time.time())
    
    def end_timer(self, operation: str) -> float:
        """结束计时，返回耗时(秒)"""
        if operation not in self._timings or not self._timings[operation]:
            return 0.0
        
        start_time = self._timings[operation].pop(0)
        elapsed = time.time() - start_time
        self._call_counts[operation] = self._call_counts.get(operation, 0) + 1
        return elapsed
    
    def record_timing(self, operation: str, duration: float):
        """记录单次耗时"""
        if operation not in self._timings:
            self._timings[operation] = []
        self._timings[operation].append(duration)
        self._call_counts[operation] = self._call_counts.get(operation, 0) + 1
    
    def get_stats(self, operation: str) -> Dict:
        """获取操作统计"""
        if operation not in self._timings or not self._timings[operation]:
            return {
                'avg_time': 0.0,
                'min_time': 0.0,
                'max_time': 0.0,
                'total_calls': 0
            }
        
        timings = self._timings[operation]
        return {
            'avg_time': sum(timings) / len(timings),
            'min_time': min(timings),
            'max_time': max(timings),
            'total_time': sum(timings),
            'total_calls': self._call_counts.get(operation, 0)
        }
    
    def get_all_stats(self) -> Dict:
        """获取所有操作统计"""
        return {
            op: self.get_stats(op)
            for op in self._timings
        }
    
    def reset(self):
        """重置统计"""
        self._timings.clear()
        self._call_counts.clear()


# 全局单例
_memory_manager = MemoryManager()
_performance_monitor = PerformanceMonitor()


def get_memory_manager() -> MemoryManager:
    """获取内存管理器单例"""
    return _memory_manager


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器单例"""
    return _performance_monitor


def cleanup_memory():
    """清理内存"""
    _memory_manager.cleanup_if_needed()


def record_performance(operation: str, duration: float):
    """记录性能数据"""
    _performance_monitor.record_timing(operation, duration)
