# -*- coding: utf-8 -*-
"""机房信息对话框"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QLabel
)
from qgis.PyQt.QtCore import Qt


class RoomDialog(QDialog):
    """机房信息输入对话框"""

    def __init__(self, lon, lat, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加机房")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 机房ID
        self.room_id_edit = QLineEdit("ROOM-001")
        form.addRow("机房编号:", self.room_id_edit)

        # 机房名称
        self.name_edit = QLineEdit("汇聚机房1")
        form.addRow("机房名称:", self.name_edit)

        # 机房类型
        self.type_combo = QComboBox()
        self.type_combo.addItems(["汇聚机房", "接入机房", "核心机房"])
        form.addRow("机房类型:", self.type_combo)

        # 坐标
        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(70.0, 140.0)
        self.lon_spin.setValue(lon)
        self.lon_spin.setDecimals(6)
        form.addRow("经度:", self.lon_spin)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(20.0, 50.0)
        self.lat_spin.setValue(lat)
        self.lat_spin.setDecimals(6)
        form.addRow("纬度:", self.lat_spin)

        # 容量
        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 100)
        self.capacity_spin.setValue(10)
        self.capacity_spin.setSuffix(" 个基站")
        form.addRow("容量:", self.capacity_spin)

        layout.addLayout(form)

        # 提示
        hint = QLabel("提示: 机房位置将自动更新到左侧参数面板")
        hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(hint)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_room_data(self):
        """获取机房数据"""
        return {
            'room_id': self.room_id_edit.text(),
            'name': self.name_edit.text(),
            'room_type': self.type_combo.currentText(),
            'longitude': self.lon_spin.value(),
            'latitude': self.lat_spin.value(),
            'capacity': self.capacity_spin.value(),
        }
