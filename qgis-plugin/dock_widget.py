"""基站智能设计面板 — QGIS Dock Widget"""
import json
import os
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton, QGroupBox,
    QCheckBox, QProgressBar, QTextEdit, QFileDialog, QMessageBox,
    QFormLayout, QTabWidget, QListWidget, QListWidgetItem,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from models.site import Site
from models.antenna import Antenna
from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
from design_engine.rules import BAND_CONFIGS, DEFAULT_SITE_PARAMS
from design_engine.coverage import generate_coverage_raster, okumura_hata_path_loss
from design_engine.avoidance import AvoidanceChecker


class DesignDockWidget(QDockWidget):
    """基站智能设计面板 — 停靠在QGIS主窗口右侧"""

    design_completed = pyqtSignal(list)  # 携带生成的Site列表

    def __init__(self, iface, parent=None):
        super().__init__("基站智能设计", parent)
        self.iface = iface
        self.generated_sites: List[Site] = []
        self.avoidance_checker = AvoidanceChecker()

        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.setMinimumWidth(380)

        # 主容器
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)

        # Tab分页
        tabs = QTabWidget()

        # === Tab 1: 参数输入 ===
        param_tab = QWidget()
        param_layout = QVBoxLayout(param_tab)

        # 设计区域
        region_group = QGroupBox("1. 设计区域")
        region_form = QFormLayout()
        self.bbox_btn = QPushButton("在地图上框选区域")
        self.bbox_btn.clicked.connect(self._select_extent)
        self.bbox_label = QLabel("未选择（将使用当前地图范围）")
        self.bbox_label.setStyleSheet("color: gray;")
        self.bbox_label.setWordWrap(True)
        region_form.addRow(self.bbox_btn)
        region_form.addRow(self.bbox_label)
        region_group.setLayout(region_form)
        param_layout.addWidget(region_group)

        # 频段选择
        band_group = QGroupBox("2. 频段参数")
        band_form = QFormLayout()
        self.band_combo = QComboBox()
        self.band_combo.addItems(["3.5GHz", "2.6GHz", "700MHz", "4.9GHz"])
        self.band_combo.setCurrentText("3.5GHz")
        self.band_combo.currentTextChanged.connect(self._on_band_changed)
        band_form.addRow("频段:", self.band_combo)

        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.3, 10.0)
        self.radius_spin.setValue(1.0)
        self.radius_spin.setSuffix(" km")
        self.radius_spin.setSingleStep(0.1)
        band_form.addRow("覆盖半径:", self.radius_spin)

        self.isr_label = QLabel("站间距: 0.5 km")
        band_form.addRow(self.isr_label)
        band_group.setLayout(band_form)
        param_layout.addWidget(band_group)

        # 站点参数
        site_group = QGroupBox("3. 站点参数")
        site_form = QFormLayout()
        self.site_type_combo = QComboBox()
        self.site_type_combo.addItems(["MACRO", "SMALL", "INDOOR"])
        self.site_type_combo.currentTextChanged.connect(self._on_site_type_changed)
        site_form.addRow("基站类型:", self.site_type_combo)

        self.tower_height_spin = QDoubleSpinBox()
        self.tower_height_spin.setRange(10, 100)
        self.tower_height_spin.setValue(35.0)
        self.tower_height_spin.setSuffix(" m")
        site_form.addRow("塔高:", self.tower_height_spin)

        self.sectors_spin = QSpinBox()
        self.sectors_spin.setRange(0, 6)
        self.sectors_spin.setValue(3)
        self.sectors_spin.setToolTip("0=全向天线, 3=三扇区, 6=六扇区")
        site_form.addRow("扇区数:", self.sectors_spin)
        site_group.setLayout(site_form)
        param_layout.addWidget(site_group)

        # 避让选项
        avoid_group = QGroupBox("4. 避让选项")
        avoid_layout = QVBoxLayout()
        self.avoid_buildings = QCheckBox("建筑物避让（需OSM建筑数据）")
        self.avoid_buildings.setChecked(True)
        self.avoid_water = QCheckBox("水体避让（需水体数据）")
        self.avoid_water.setChecked(True)
        avoid_layout.addWidget(self.avoid_buildings)
        avoid_layout.addWidget(self.avoid_water)

        # 加载避让数据按钮
        self.load_avoidance_btn = QPushButton("加载避让数据...")
        self.load_avoidance_btn.clicked.connect(self._load_avoidance_data)
        avoid_layout.addWidget(self.load_avoidance_btn)
        self.avoidance_label = QLabel("未加载避让数据")
        self.avoidance_label.setStyleSheet("color: gray;")
        avoid_layout.addWidget(self.avoidance_label)

        avoid_group.setLayout(avoid_layout)
        param_layout.addWidget(avoid_group)

        # 已有站点
        existing_group = QGroupBox("5. 已有站点约束（可选）")
        existing_layout = QVBoxLayout()
        self.load_existing_btn = QPushButton("加载当前选中图层")
        self.load_existing_btn.clicked.connect(self._load_existing_layer)
        self.existing_label = QLabel("未加载")
        self.existing_label.setStyleSheet("color: gray;")
        existing_layout.addWidget(self.load_existing_btn)
        existing_layout.addWidget(self.existing_label)
        existing_group.setLayout(existing_layout)
        param_layout.addWidget(existing_group)

        param_layout.addStretch()
        tabs.addTab(param_tab, "参数设置")

        # === Tab 2: 生成结果 ===
        result_tab = QWidget()
        result_layout = QVBoxLayout(result_tab)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        result_layout.addWidget(self.progress_bar)

        self.site_list = QListWidget()
        self.site_list.setAlternatingRowColors(True)
        self.site_list.itemClicked.connect(self._on_site_selected)
        result_layout.addWidget(self.site_list)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(120)
        result_layout.addWidget(self.result_text)

        tabs.addTab(result_tab, "站点列表")

        main_layout.addWidget(tabs)

        # 操作按钮
        btn_layout = QHBoxLayout()

        self.generate_btn = QPushButton("一键生成设计方案")
        self.generate_btn.setStyleSheet(
            "QPushButton { background-color: #1890ff; color: white; font-size: 14px; "
            "padding: 8px 16px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #40a9ff; }"
            "QPushButton:disabled { background-color: #999; }"
        )
        self.generate_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(self.generate_btn)

        self.export_btn = QPushButton("导出GeoJSON")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)

        main_layout.addLayout(btn_layout)

        self.setWidget(main_widget)

        # 存储状态
        self.selected_extent = None  # (xmin, ymin, xmax, ymax) in EPSG:4326
        self.existing_sites: List[Site] = []

    def _select_extent(self):
        """激活地图框选工具"""
        try:
            from qgis.gui import QgsMapToolExtent
            from qgis.core import QgsRectangle

            canvas = self.iface.mapCanvas()
            tool = QgsMapToolExtent(canvas)

            def on_extent_captured(extent):
                self.selected_extent = (
                    extent.xMinimum(), extent.yMinimum(),
                    extent.xMaximum(), extent.yMaximum()
                )
                self.bbox_label.setText(
                    f"已选择: [{self.selected_extent[0]:.4f}, {self.selected_extent[1]:.4f}] "
                    f"→ [{self.selected_extent[2]:.4f}, {self.selected_extent[3]:.4f}]"
                )
                self.bbox_label.setStyleSheet("color: #00d4ff;")
                canvas.unsetMapTool(tool)

            tool.extentCreated.connect(on_extent_captured)
            canvas.setMapTool(tool)
            self.bbox_label.setText("请在地图上拖拽框选区域...")
            self.bbox_label.setStyleSheet("color: orange;")
        except Exception as e:
            self.bbox_label.setText(f"框选失败: {e}")
            # 使用当前地图范围作为备选
            canvas = self.iface.mapCanvas()
            extent = canvas.extent()
            self.selected_extent = (
                extent.xMinimum(), extent.yMinimum(),
                extent.xMaximum(), extent.yMaximum()
            )
            self.bbox_label.setText(
                f"使用当前视图: [{self.selected_extent[0]:.4f}, {self.selected_extent[1]:.4f}] "
                f"→ [{self.selected_extent[2]:.4f}, {self.selected_extent[3]:.4f}]"
            )

    def _on_band_changed(self, band_text):
        """频段变更时更新站间距显示"""
        if band_text in BAND_CONFIGS:
            config = BAND_CONFIGS[band_text]
            self.isr_label.setText(f"站间距: {config.ideal_isr_km} km")

    def _on_site_type_changed(self, site_type):
        """基站类型变更时更新塔高默认值"""
        if site_type in DEFAULT_SITE_PARAMS:
            params = DEFAULT_SITE_PARAMS[site_type]
            self.tower_height_spin.setValue(params["default_tower_height"])
            self.sectors_spin.setValue(params["default_sectors"])

    def _load_avoidance_data(self):
        """加载避让数据文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择避让数据文件", "", "GeoJSON文件 (*.geojson *.json);;所有文件 (*)"
        )
        if file_path:
            try:
                rule_name = os.path.splitext(os.path.basename(file_path))[0]
                self.avoidance_checker.load_geojson(file_path, rule_name, buffer_m=20.0)
                summary = self.avoidance_checker.get_avoidance_summary()
                parts = [f"{k}: {v['count']}个" for k, v in summary.items()]
                self.avoidance_label.setText(f"已加载: {', '.join(parts)}")
                self.avoidance_label.setStyleSheet("color: #52c41a;")
            except Exception as e:
                QMessageBox.warning(self, "加载失败", f"无法加载文件: {e}")

    def _load_existing_layer(self):
        """从当前选中图层加载已有站点"""
        layer = self.iface.activeLayer()
        if layer is None:
            QMessageBox.warning(self, "提示", "请先在图层列表中选中已有基站图层")
            return

        count = 0
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom and geom.type() == 0:  # Point
                point = geom.asPoint()
                site = Site(
                    site_id=feature.attribute("siteId") or f"EXIST-{count}",
                    name=feature.attribute("name") or f"已有站点{count}",
                    longitude=point.x(),
                    latitude=point.y(),
                    tower_height=float(feature.attribute("towerHeight") or 35.0),
                )
                self.existing_sites.append(site)
                count += 1

        self.existing_label.setText(f"已加载 {count} 个已有站点")
        self.existing_label.setStyleSheet("color: #52c41a;")

    def _on_generate(self):
        """执行基站设计生成"""
        # 确定设计区域
        if self.selected_extent is None:
            canvas = self.iface.mapCanvas()
            extent = canvas.extent()
            self.selected_extent = (
                extent.xMinimum(), extent.yMinimum(),
                extent.xMaximum(), extent.yMaximum()
            )

        xmin, ymin, xmax, ymax = self.selected_extent
        band_key = self.band_combo.currentText()
        band_config = BAND_CONFIGS[band_key]

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.generate_btn.setEnabled(False)
        self.result_text.clear()

        try:
            # Step 1: 生成六边形网格
            self.progress_bar.setValue(10)
            centers = generate_hex_grid(
                (xmin, ymin, xmax, ymax),
                isr_km=band_config.ideal_isr_km,
            )
            self.result_text.append(f"Step 1: 生成 {len(centers)} 个候选网格中心点")

            # Step 2: 障碍物避让过滤
            self.progress_bar.setValue(30)
            if self.avoidance_checker.avoidance_polygons:
                centers = self.avoidance_checker.filter_valid_sites(centers)
                self.result_text.append(f"Step 2: 避让过滤后剩余 {len(centers)} 个候选点")

            # Step 3: 生成站点
            self.progress_bar.setValue(50)
            self.generated_sites = generate_sites_from_grid(
                centers,
                band_config=band_config,
                site_type=self.site_type_combo.currentText(),
                tower_height=self.tower_height_spin.value(),
                num_sectors=self.sectors_spin.value(),
                existing_sites=self.existing_sites,
                bbox=(xmin, ymin, xmax, ymax),
            )
            self.result_text.append(f"Step 3: 生成 {len(self.generated_sites)} 个站点")

            # Step 4: 在地图上渲染
            self.progress_bar.setValue(70)
            self._render_sites_on_map()

            # Step 5: 更新站点列表
            self.progress_bar.setValue(90)
            self._update_site_list()

            self.progress_bar.setValue(100)
            self.result_text.append(f"完成！共生成 {len(self.generated_sites)} 个基站站点")
            self.export_btn.setEnabled(True)

            # 发送信号
            self.design_completed.emit(self.generated_sites)

        except Exception as e:
            self.result_text.append(f"错误: {e}")
            QMessageBox.critical(self, "生成失败", str(e))
        finally:
            self.generate_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

    def _render_sites_on_map(self):
        """在QGIS地图上渲染生成的站点"""
        try:
            from qgis.core import (
                QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
                QgsPointXY, QgsField, QgsSymbol, QgsRendererCategory,
                QgsCategorizedSymbolRenderer, QgsMarkerSymbol,
            )
            from PyQt5.QtCore import QVariant
            from PyQt5.QtGui import QColor

            # 创建内存图层
            layer = QgsVectorLayer(
                "Point?crs=EPSG:4326",
                "设计方案站点",
                "memory"
            )
            provider = layer.dataProvider()

            # 添加字段
            provider.addAttributes([
                QgsField("siteId", QVariant.String),
                QgsField("name", QVariant.String),
                QgsField("siteType", QVariant.String),
                QgsField("towerHeight", QVariant.Double),
                QgsField("scenario", QVariant.String),
                QgsField("antennaCount", QVariant.Int),
            ])
            layer.updateFields()

            # 添加要素
            features = []
            for site in self.generated_sites:
                feat = QgsFeature(layer.fields())
                feat.setGeometry(QgsGeometry.fromPointXY(
                    QgsPointXY(site.longitude, site.latitude)
                ))
                feat.setAttributes([
                    site.site_id,
                    site.name,
                    site.site_type,
                    site.tower_height,
                    site.scenario,
                    len(site.antennas),
                ])
                features.append(feat)

            provider.addFeatures(features)
            layer.updateExtents()

            # 设置样式 - 不同类型不同颜色
            symbol_macro = QgsMarkerSymbol.createSimple({"name": "circle", "color": "#1890ff", "size": "5"})
            symbol_small = QgsMarkerSymbol.createSimple({"name": "circle", "color": "#52c41a", "size": "4"})
            symbol_indoor = QgsMarkerSymbol.createSimple({"name": "circle", "color": "#faad14", "size": "3"})

            categories = [
                QgsRendererCategory("MACRO", symbol_macro, "宏站"),
                QgsRendererCategory("SMALL", symbol_small, "微站"),
                QgsRendererCategory("INDOOR", symbol_indoor, "室内站"),
            ]
            renderer = QgsCategorizedSymbolRenderer("siteType", categories)
            layer.setRenderer(renderer)

            # 添加到项目
            QgsProject.instance().addMapLayer(layer)
            self.result_text.append("已将站点渲染到地图图层")

        except ImportError:
            self.result_text.append("注意: 非QGIS环境，跳过地图渲染")
        except Exception as e:
            self.result_text.append(f"地图渲染失败: {e}")

    def _update_site_list(self):
        """更新站点列表显示"""
        self.site_list.clear()
        for site in self.generated_sites:
            item_text = (
                f"{site.site_id} | {site.site_type} | "
                f"H={site.tower_height}m | {len(site.antennas)}天线 | "
                f"({site.longitude:.4f}, {site.latitude:.4f})"
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, site)
            self.site_list.addItem(item)

    def _on_site_selected(self, item):
        """点击站点列表项，定位到地图"""
        site = item.data(Qt.UserRole)
        if site:
            try:
                from qgis.core import QgsPointXY
                canvas = self.iface.mapCanvas()
                canvas.setCenter(QgsPointXY(site.longitude, site.latitude))
                canvas.zoomScale(10000)  # 1:10000
                canvas.refresh()
            except Exception:
                pass

    def _on_export(self):
        """导出设计方案为GeoJSON"""
        if not self.generated_sites:
            QMessageBox.warning(self, "提示", "没有可导出的设计方案")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出设计方案", "design_scheme.geojson",
            "GeoJSON文件 (*.geojson);;所有文件 (*)"
        )
        if file_path:
            try:
                geojson = {
                    "type": "FeatureCollection",
                    "features": [s.to_geojson_feature() for s in self.generated_sites],
                    "metadata": {
                        "band": self.band_combo.currentText(),
                        "siteType": self.site_type_combo.currentText(),
                        "towerHeight": self.tower_height_spin.value(),
                        "totalSites": len(self.generated_sites),
                    }
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(geojson, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "导出成功", f"已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))
