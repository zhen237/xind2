"""通信基站智能设计平台 — QGIS Plugin 入口"""
import os
from qgis.gui import QgisInterface
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon


class BaseStationDesignPlugin:
    """插件主类"""

    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.toolbar = None
        self.design_dock = None
        self.bom_dialog = None

    def initGui(self):
        """初始化插件UI — 在QGIS菜单和工具栏注册"""
        icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.png')

        # 如果图标不存在，使用默认空图标
        if not os.path.exists(icon_path):
            icon = QIcon()
        else:
            icon = QIcon(icon_path)

        # 智能设计面板
        design_action = QAction(
            icon,
            '基站智能设计',
            self.iface.mainWindow()
        )
        design_action.triggered.connect(self.open_design_panel)
        self.iface.addPluginToMenu('&通信基建设计', design_action)
        self.iface.addToolBarIcon(design_action)
        self.actions.append(design_action)

        # BOM生成面板
        bom_action = QAction(
            icon,
            'BOM生成',
            self.iface.mainWindow()
        )
        bom_action.triggered.connect(self.open_bom_panel)
        self.iface.addPluginToMenu('&通信基建设计', bom_action)
        self.iface.addToolBarIcon(bom_action)
        self.actions.append(bom_action)

    def unload(self):
        """卸载插件 — 清理所有UI元素"""
        for action in self.actions:
            self.iface.removePluginMenu('&通信基建设计', action)
            self.iface.removeToolBarIcon(action)
        if self.design_dock:
            self.iface.removeDockWidget(self.design_dock)

    def open_design_panel(self):
        """打开基站智能设计面板（子赛题1）"""
        if self.design_dock is None:
            from dock_widget import DesignDockWidget
            self.design_dock = DesignDockWidget(self.iface)
            self.iface.addDockWidget(4, self.design_dock)  # 4=RightDockWidgetArea
        self.design_dock.show()

    def open_bom_panel(self):
        """打开BOM生成面板（子赛题4）"""
        try:
            from bom_generator.bom_dialog import BomDialog
            dialog = BomDialog(self.iface)
            dialog.exec_()
        except ImportError:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self.iface.mainWindow(),
                "BOM生成",
                "BOM生成功能正在开发中..."
            )


def classFactory(iface):  # noqa: N802 - QGIS插件标准入口点
    """QGIS插件入口点"""
    return BaseStationDesignPlugin(iface)
