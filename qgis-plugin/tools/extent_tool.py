# -*- coding: utf-8 -*-
"""自定义框选工具 — 使用鼠标按下和释放事件"""
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsPointXY, QgsRectangle, QgsWkbTypes
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor


class ExtentSelectTool(QgsMapTool):
    """拖拽框选区域工具"""
    extent_selected = pyqtSignal(QgsRectangle)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self._start_point = None
        self._rubber_band = None

    def activate(self):
        self.canvas.setCursor(Qt.CrossCursor)

    def deactivate(self):
        self._remove_rubber_band()

    def _remove_rubber_band(self):
        if self._rubber_band:
            self.canvas.scene().removeItem(self._rubber_band)
            self._rubber_band = None

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_point = self.toMapCoordinates(event.pos())
            # 创建橡皮筋
            self._remove_rubber_band()
            self._rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            self._rubber_band.setColor(QColor(255, 0, 0, 255))
            self._rubber_band.setFillColor(QColor(255, 0, 0, 50))
            self._rubber_band.setWidth(3)

    def canvasMoveEvent(self, event):
        if self._start_point and self._rubber_band:
            current = self.toMapCoordinates(event.pos())
            self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            x_min = min(self._start_point.x(), current.x())
            y_min = min(self._start_point.y(), current.y())
            x_max = max(self._start_point.x(), current.x())
            y_max = max(self._start_point.y(), current.y())
            self._rubber_band.addPoint(QgsPointXY(x_min, y_min), False)
            self._rubber_band.addPoint(QgsPointXY(x_max, y_min), False)
            self._rubber_band.addPoint(QgsPointXY(x_max, y_max), False)
            self._rubber_band.addPoint(QgsPointXY(x_min, y_max), True)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._start_point:
            end_point = self.toMapCoordinates(event.pos())
            x_min = min(self._start_point.x(), end_point.x())
            y_min = min(self._start_point.y(), end_point.y())
            x_max = max(self._start_point.x(), end_point.x())
            y_max = max(self._start_point.y(), end_point.y())
            rect = QgsRectangle(x_min, y_min, x_max, y_max)
            self._remove_rubber_band()
            self.extent_selected.emit(rect)
            self._start_point = None
