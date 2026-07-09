# -*- coding: utf-8 -*-
"""插件配置持久化 — 使用 QgsSettings 保存用户偏好

用法:
    from config import get_setting, set_setting
    last_band = get_setting("band", "n41")
    set_setting("band", "n78")
"""

from qgis.core import QgsSettings

from .utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)

_DEFAULTS = {
    "band": "n41",
    "tower_height": 30,
    "sector_count": 3,
    "site_type": "macro",
    "scenario": "URBAN",
    "isr_radius_factor": 1.5,
    "last_bbox_xmin": None,
    "last_bbox_ymin": None,
    "last_bbox_xmax": None,
    "last_bbox_ymax": None,
    "backend_url": "http://localhost:8083",
    "basemap_type": "gaode",
}


def _key(name):
    return f"base_station_design/{name}"


def get_setting(name, default=None):
    """读取持久化设置，带默认值回退"""
    if default is None:
        default = _DEFAULTS.get(name)
    return QgsSettings().value(_key(name), default, type=type(default) if default is not None else None)


def set_setting(name, value):
    """写入持久化设置"""
    QgsSettings().setValue(_key(name), value)


def save_current_config(widget):
    """保存当前面板配置（call on close / design complete）"""
    if widget is None:
        return
    try:
        set_setting("band", widget.band_combo.currentText())
        set_setting("tower_height", int(widget.height_spin.value()))
        set_setting("sector_count", int(widget.sector_spin.value()))
        set_setting("site_type", widget.type_combo.currentText())
        set_setting("scenario", widget.scenario_combo.currentText())
        if widget.selected_extent:
            ext = widget.selected_extent
            set_setting("last_bbox_xmin", ext.xMinimum())
            set_setting("last_bbox_ymin", ext.yMinimum())
            set_setting("last_bbox_xmax", ext.xMaximum())
            set_setting("last_bbox_ymax", ext.yMaximum())
    except Exception as e:
        _logger.warning("保存配置失败: %s", e)


def restore_config(widget):
    """恢复上次的面板配置"""
    if widget is None:
        return
    try:
        band = get_setting("band", "n41")
        idx = widget.band_combo.findText(band)
        if idx >= 0:
            widget.band_combo.setCurrentIndex(idx)
        widget.height_spin.setValue(int(get_setting("tower_height", 30)))
        widget.sector_spin.setValue(int(get_setting("sector_count", 3)))
    except Exception as e:
        _logger.warning("恢复配置失败: %s", e)
