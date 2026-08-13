"""地图交互工具 — 点击触发跨数据集联动查询"""
from qgis.gui import QgsMapToolEmitPoint
from qgis.PyQt.QtCore import Qt, pyqtSignal


class LinkageQueryTool(QgsMapToolEmitPoint):
    """左键点击地图，发射坐标信号，用于 FTTH ↔ 基站/管线/机房 联动高亮。"""
    point_clicked = pyqtSignal(float, float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.point_clicked.emit(point.x(), point.y())
