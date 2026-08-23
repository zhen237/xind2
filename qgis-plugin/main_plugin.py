# -*- coding: utf-8 -*-
"""基站智能设计插件 - 主入口"""
import os
import sys


class BaseStationDesignPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock_widget = None
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
        self.iface.removePluginMenu("&基站智能设计", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)

    def run(self):
        if self.dock_widget is None:
            from ui.design_dock import DesignDockWidget
            self.dock_widget = DesignDockWidget(self.iface, self.iface.mainWindow())
            # addDockWidget 第一个参数是 Qt.DockWidgetArea 枚举值
            # Qt.RightDockWidgetArea = 2
            self.iface.addDockWidget(2, self.dock_widget)
        self.dock_widget.show()
        self.dock_widget.raise_()
