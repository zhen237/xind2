# -*- coding: utf-8 -*-
"""机房点击工具 - 在地图上点击添加机房"""

from qgis.gui import QgsMapTool
from qgis.PyQt.QtCore import pyqtSignal


class AddRoomTool(QgsMapTool):
    """点击地图添加机房的工具"""

    point_clicked = pyqtSignal(float, float)  # 经度, 纬度

    def __init__(self, canvas):
        super().__init__(canvas)

    def canvasPressEvent(self, event):
        """鼠标点击事件"""
        point = self.toMapCoordinates(event.pos())
        self.point_clicked.emit(point.x(), point.y())
