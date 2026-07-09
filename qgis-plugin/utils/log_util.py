"""
QGIS 插件统一日志模块

提供带 QGIS 消息栏集成的统一日志接口。
在 QGIS 环境外用标准 logging 作为回退。
"""

import logging
import sys
from datetime import datetime


# 模块级 logger 实例
_MODULE_LOGGER: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    """获取或创建模块级 logger"""
    global _MODULE_LOGGER
    if _MODULE_LOGGER is None:
        _MODULE_LOGGER = logging.getLogger("xind2.qgis_plugin")
        _MODULE_LOGGER.setLevel(logging.DEBUG)
        if not _MODULE_LOGGER.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s][%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            _MODULE_LOGGER.addHandler(handler)
    return _MODULE_LOGGER


def get_plugin_logger(name: str | None = None) -> logging.Logger:
    """获取插件子模块 logger

    Args:
        name: 子模块名称（如 'data_sync'），None 则返回根 logger

    Returns:
        配置好的 logging.Logger 实例
    """
    base = _get_logger()
    if name:
        return base.getChild(name)
    return base


def log_to_qgis(iface, level: str, message: str):
    """同时输出到 Python logging 和 QGIS 消息栏

    Args:
        iface: QGIS iface 接口对象（或 None）
        level: 日志级别 (DEBUG/INFO/WARN/ERROR)
        message: 日志消息
    """
    logger = _get_logger()
    level_upper = level.upper()
    getattr(logger, level_upper.lower(), logger.info)(message)

    if iface is not None:
        try:
            from qgis.core import Qgis

            qgis_levels = {
                "DEBUG": Qgis.MessageLevel.Info,
                "INFO": Qgis.MessageLevel.Info,
                "WARN": Qgis.MessageLevel.Warning,
                "ERROR": Qgis.MessageLevel.Critical,
            }
            iface.messageBar().pushMessage(
                "Xind2",
                message,
                level=qgis_levels.get(level_upper, Qgis.MessageLevel.Info),
                duration=5,
            )
        except Exception:
            pass  # 非 QGIS 环境静默忽略


def log_exception(name: str, exc: Exception, context: str = "") -> None:
    """异常统一日志记录

    Args:
        name: 模块名称
        context: 上下文描述
        exc: 异常实例
    """
    logger = get_plugin_logger(name)
    msg = f"{context}: {exc}" if context else str(exc)
    logger.error(msg, exc_info=True)
