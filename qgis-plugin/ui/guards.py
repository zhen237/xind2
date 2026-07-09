"""QGIS 插件前置条件守卫装饰器

用途: 消除 design_dock.py 中 13 处重复的
     "if not self.generated_sites: QMessageBox.warning(...)" 模式。

使用:
    from ui.guards import require_sites, require_extent

    @require_sites("请先在第四步生成基站")
    def _generate_heatmap(self):
        # 不再需要手动检查 self.generated_sites
        ...

    @require_extent("请先在第二步选择设计区域")
    def _generate_hex_grid(self):
        ...
"""

from functools import wraps
from qgis.PyQt.QtWidgets import QMessageBox


def _warn(parent, title, message):
    """弹出 warning 对话框"""
    QMessageBox.warning(parent, title, str(message))


def require_sites(message="请先生成基站"):
    """要求 self.generated_sites 非空且非 None"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, 'generated_sites', None):
                _warn(self, "提示", message)
                return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def require_extent(message="请先在第二步选择设计区域"):
    """要求 self.selected_extent 非空"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, 'selected_extent', None):
                _warn(self, "提示", message)
                return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def require_rooms(message="请至少添加一个机房"):
    """要求有至少一个机房（管线生成前置条件）"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            rooms = getattr(self, 'machine_rooms', [])
            if not rooms:
                _warn(self, "提示", message)
                return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def require_design(message="请先生成基站方案"):
    """要求 self.generated_sites 非空 且 self.generated_pipelines 非空"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            sites = getattr(self, 'generated_sites', None)
            pipelines = getattr(self, 'generated_pipelines', None)
            if not sites:
                _warn(self, "提示", "请先生成基站")
                return
            if not pipelines:
                _warn(self, "提示", "请先生成管线")
                return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def log_call(func_name=None):
    """自动给方法添加 self._log() 调用（可选）"""
    def decorator(func):
        name = func_name or func.__name__
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            log = getattr(self, '_log', None)
            if log:
                log(f"→ {name}")
            result = func(self, *args, **kwargs)
            if log:
                log(f"✓ {name} 完成")
            return result
        return wrapper
    return decorator


def require_sites_count(min_count=1, message="先确保已有足够基站"):
    """要求 self.generated_sites 至少有 min_count 个元素"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            sites = getattr(self, 'generated_sites', None)
            if not sites or len(sites) < min_count:
                _warn(self, "提示", message)
                return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def safe_execute(show_errors=True):
    """捕获异常的统一 try/except/finally 模式

    替代设计中的重复模式:
        try:
            ...
        except Exception as e:
            self._log(f"错误: {e}")
            QMessageBox.critical(self, "失败", str(e))
            self._show_progress(False)

    会自动:
    - 在方法开始时重置 _cancel_requested = False
    - 在异常或正常返回时调用 _show_progress(False)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 重置取消标志
            cancel_flag = getattr(self, '_cancel_requested', None)
            if cancel_flag is not None:
                self._cancel_requested = False

            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                log = getattr(self, '_log', None)
                if log:
                    log(f"✗ {func.__name__} 失败: {e}")
                if show_errors:
                    QMessageBox.critical(self, "操作失败", str(e))
                progress = getattr(self, '_show_progress', None)
                if progress:
                    progress(False)
        return wrapper
    return decorator
