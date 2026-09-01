"""站点编辑/添加对话框"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QPushButton, QDialogButtonBox, QLabel,
)
from PyQt5.QtCore import Qt

# 全局计数器，用于生成唯一站点ID
_site_counter = 0


class StationDialog(QDialog):
    def __init__(self, lon, lat, site_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加基站" if site_data is None else "编辑基站")
        self.setMinimumWidth(320)
        self.lon = lon
        self.lat = lat

        global _site_counter
        _site_counter += 1

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 站点ID
        self.site_id_edit = QLineEdit(
            site_data.get("site_id", f"MANUAL-{_site_counter:03d}") if site_data else f"MANUAL-{_site_counter:03d}"
        )
        form.addRow("站点ID:", self.site_id_edit)

        # 站点名称
        self.name_edit = QLineEdit(
            site_data.get("name", f"手动站点-{_site_counter}") if site_data else f"手动站点-{_site_counter}"
        )
        form.addRow("站点名称:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["宏站", "微站", "室内站"])
        if site_data:
            idx = self.type_combo.findText(site_data.get("site_type", "宏站"))
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        form.addRow("站点类型:", self.type_combo)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(2, 80)
        self.height_spin.setValue(site_data.get("tower_height", 35) if site_data else 35)
        self.height_spin.setSuffix(" m")
        form.addRow("塔高:", self.height_spin)

        self.mount_combo = QComboBox()
        self.mount_combo.addItems(["地面塔", "楼面塔"])
        if site_data:
            midx = self.mount_combo.findText(site_data.get("mount_type", "地面塔"))
            if midx >= 0:
                self.mount_combo.setCurrentIndex(midx)
        form.addRow("安装方式:", self.mount_combo)

        self.azimuth_spin = QSpinBox()
        self.azimuth_spin.setRange(0, 359)
        self.azimuth_spin.setValue(site_data.get("azimuth", 0) if site_data else 0)
        self.azimuth_spin.setSuffix("°")
        form.addRow("方位角:", self.azimuth_spin)

        coord_label = QLabel(f"经度: {lon:.6f}  纬度: {lat:.6f}")
        coord_label.setStyleSheet("color: gray;")
        form.addRow(coord_label)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_site_data(self):
        type_map = {"宏站": "MACRO", "微站": "SMALL", "室内站": "INDOOR"}
        mount_map = {"地面塔": "GROUND", "楼面塔": "ROOFTOP"}
        return {
            "site_id": self.site_id_edit.text(),
            "name": self.name_edit.text(),
            "site_type": type_map.get(self.type_combo.currentText(), "MACRO"),
            "tower_height": self.height_spin.value(),
            "mount_type": mount_map.get(self.mount_combo.currentText(), "GROUND"),
            "azimuth": self.azimuth_spin.value(),
            "longitude": self.lon,
            "latitude": self.lat,
        }
