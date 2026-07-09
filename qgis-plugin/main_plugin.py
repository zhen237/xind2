# -*- coding: utf-8 -*-
"""基站智能设计插件 - 主入口"""
import os
import sys
import gc
import traceback

from .utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)


class BaseStationDesignPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock_widget = None
        self._worker = None
        self._plugin_layers = []  # 跟踪插件创建的图层
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)

    def initGui(self):
        from qgis.PyQt.QtWidgets import QAction
        from qgis.PyQt.QtCore import Qt
        self.action = QAction("基站智能设计", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&基站智能设计", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        """插件卸载 — 完整清理资源"""
        # 1. 清理画布注解（热力图图例等）
        if self.dock_widget and hasattr(self.dock_widget, '_cleanup_legend'):
            try:
                self.dock_widget._cleanup_legend()
            except Exception as e:
                _logger.warning("清理图例失败(unload): %s", e)

        # 2. 停止后台任务
        if self.dock_widget and hasattr(self.dock_widget, '_cancel_requested'):
            self.dock_widget._cancel_requested = True

        # 3. 移除插件创建的图层
        from qgis.core import QgsProject
        project = QgsProject.instance()
        layer_names = [
            "覆盖热力图", "RSRP覆盖图例", "通信管线",
            "通信管线_对比", "管线连接", "基站站点",
            "高德卫星图", "OpenStreetMap", "覆盖范围圈",
            "临时选区范围",
        ]
        for name in layer_names:
            for layer in project.mapLayersByName(name):
                try:
                    project.removeMapLayer(layer)
                except Exception as e:
                    _logger.debug("移除图层失败(unload): %s: %s", name, e)

        # 4. 移除 UI
        self.iface.removePluginMenu("&基站智能设计", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dock_widget:
            try:
                self.iface.removeDockWidget(self.dock_widget)
            except Exception as e:
                _logger.warning("移除DockWidget失败(unload): %s", e)

        # 5. 强制垃圾回收
        gc.collect()

    def run(self):
        if self.dock_widget is None:
            from ui.design_dock import DesignDockWidget
            self.dock_widget = DesignDockWidget(self.iface, self.iface.mainWindow())
            # addDockWidget 第一个参数是 Qt.DockWidgetArea 枚举值
            # Qt.RightDockWidgetArea = 2
            self.iface.addDockWidget(2, self.dock_widget)
        self.dock_widget.show()
        self.dock_widget.raise_()
