# -*- coding: utf-8 -*-
"""通信设施智能设计面板 — 基站+管线+机房

功能：
1. 加载底图（高德卫星、OSM）
2. 选择设计区域（缩放+点击）
3. 设置基站参数
4. 生成蜂窝拓扑 / 手动添加
5. 覆盖分析 / 导出
6. 管线设计（路由规划、工程量计算）
7. 机房设计（选址、容量规划）
"""

import os
import json
from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QFileDialog, QMessageBox, QApplication,
    QTextEdit, QInputDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsProject, QgsRectangle, QgsPointXY, QgsWkbTypes,
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsField,
    QgsMarkerSymbol, QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
    QgsRendererCategory, QgsRendererRange, QgsGraduatedSymbolRenderer,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsRasterLayer,
)
from qgis.gui import QgsRubberBand

from design_engine.rules import BAND_CONFIGS
from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
from design_engine.coverage import generate_coverage_raster, rsrp_to_color
from design_engine.coverage_heatmap import generate_coverage_heatmap_data
from design_engine.avoidance import AvoidanceChecker
from design_engine.pipeline import (
    generate_pipelines_for_sites, calculate_total_engineering_volume,
    PipelineType, PipelineConfig
)
from layers.pipeline_layer import (
    create_pipeline_layer, add_pipeline_labels,
    get_pipeline_info, export_pipelines_to_geojson
)
from ui.basemap import add_gaode_satellite, add_osm
from tools.station_tool import AddStationTool
from ui.station_dialog import StationDialog
from tools.room_tool import AddRoomTool
from ui.room_dialog import RoomDialog
from design_engine.layout_export import (
    create_design_layout, add_map_to_layout, add_title_to_layout,
    add_info_box_to_layout, add_legend_to_layout, add_scale_bar_to_layout,
    add_north_arrow_to_layout, export_layout_to_pdf,
)


# ==================== 主面板 ====================

class DesignDockWidget(QDockWidget):
    design_completed = pyqtSignal(list)

    def __init__(self, iface, parent=None):
        super().__init__("通信设施智能设计", parent)
        self.iface = iface
        self.generated_sites = []
        self.selected_extent = None
        self._extent_bands = []
        self._marker_bands = []
        self._avoidance_features = []

        # 管线设计相关
        self.generated_pipelines = []
        self.machine_rooms = []
        self.room_counter = 0

        # 步骤页面
        self.step_pages = {}
        self.current_step = 0

        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(450)
        self._build_ui()

    # =================================================================
    #  UI 构建 — 左侧菜单 + 右侧内容
    # =================================================================

    def _build_ui(self):
        main = QWidget()
        main_layout = QHBoxLayout(main)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧菜单栏
        left_panel = QWidget()
        left_panel.setFixedWidth(100)
        left_panel.setStyleSheet("background-color: #2c3e50;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(2)
        left_layout.setContentsMargins(5, 10, 5, 10)

        # 标题
        title = QLabel("设计平台")
        title.setStyleSheet("color: white; font-size: 12px; font-weight: bold; padding: 5px;")
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)

        # 步骤按钮
        self.step_buttons = []
        steps = ["底图", "区域", "参数", "基站", "管线", "导出"]
        for i, step_name in enumerate(steps):
            btn = QPushButton(f"{i+1}.{step_name}")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #34495e;
                    color: white;
                    border: none;
                    padding: 8px;
                    text-align: left;
                    font-size: 11px;
                }
                QPushButton:checked {
                    background-color: #3498db;
                }
                QPushButton:hover {
                    background-color: #4a6a8a;
                }
            """)
            btn.clicked.connect(lambda checked, idx=i: self._switch_step(idx))
            left_layout.addWidget(btn)
            self.step_buttons.append(btn)

        left_layout.addStretch()

        # 日志区域
        log_label = QLabel("日志:")
        log_label.setStyleSheet("color: white; font-size: 10px;")
        left_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        self.log_text.setStyleSheet("background-color: #34495e; color: white; font-size: 10px;")
        left_layout.addWidget(self.log_text)

        main_layout.addWidget(left_panel)

        # 右侧内容区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # 创建各个步骤页面
        self.step_pages = {
            0: self._build_step1(),
            1: self._build_step2(),
            2: self._build_step3(),
            3: self._build_step4(),
            4: self._build_step5(),
            5: self._build_step6(),
        }

        # 页面容器
        self.page_stack = QWidget()
        self.page_stack_layout = QVBoxLayout(self.page_stack)
        self.page_stack_layout.setContentsMargins(0, 0, 0, 0)

        # 添加所有页面
        for page in self.step_pages.values():
            self.page_stack_layout.addWidget(page)

        right_layout.addWidget(self.page_stack)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right_layout.addWidget(self.progress)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        right_layout.addWidget(self.status_label)

        right_layout.addStretch()
        main_layout.addWidget(right_panel)

        self.setWidget(main)

        # 默认显示第一步
        self._switch_step(0)

    def _switch_step(self, step_index):
        """切换步骤页面"""
        # 隐藏所有页面
        for page in self.step_pages.values():
            page.hide()

        # 显示选中的页面
        if step_index in self.step_pages:
            self.step_pages[step_index].show()

        # 更新按钮状态
        for i, btn in enumerate(self.step_buttons):
            btn.setChecked(i == step_index)

        self.current_step = step_index

    def _build_step1(self):
        """加载底图"""
        page = QWidget()
        layout = QVBoxLayout(page)

        # 标题
        title = QLabel("第一步：加载底图")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 5px;")
        layout.addWidget(title)

        # 说明
        desc = QLabel("选择底图类型，加载到地图画布")
        desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(desc)

        # 按钮
        btn_row = QHBoxLayout()

        btn_gaode = QPushButton("高德卫星图")
        btn_gaode.setStyleSheet("background-color: #27ae60; color: white; padding: 10px;")
        btn_gaode.clicked.connect(self._add_gaode_basemap)
        btn_row.addWidget(btn_gaode)

        btn_osm = QPushButton("OSM地图")
        btn_osm.setStyleSheet("background-color: #2980b9; color: white; padding: 10px;")
        btn_osm.clicked.connect(self._add_osm_basemap)
        btn_row.addWidget(btn_osm)

        layout.addLayout(btn_row)
        layout.addStretch()

        return page

    def _build_step2(self):
        """选择设计区域"""
        page = QWidget()
        layout = QVBoxLayout(page)

        # 标题
        title = QLabel("第二步：选择设计区域")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 5px;")
        layout.addWidget(title)

        # 说明
        desc = QLabel("缩放地图到目标区域，然后点击按钮框选")
        desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(desc)

        # 按钮行
        btn_row = QHBoxLayout()

        self.select_btn = QPushButton("使用当前可视范围")
        self.select_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 10px;")
        self.select_btn.clicked.connect(self._select_extent)
        btn_row.addWidget(self.select_btn)

        clear_btn = QPushButton("清除")
        clear_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px;")
        clear_btn.clicked.connect(self._clear_extent)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        # 状态
        self.extent_label = QLabel("未选择区域")
        self.extent_label.setStyleSheet("color: gray; font-size: 12px;")
        self.extent_label.setWordWrap(True)
        layout.addWidget(self.extent_label)

        layout.addStretch()

        return page

    def _build_step3(self):
        """设置基站参数"""
        page = QWidget()
        layout = QVBoxLayout(page)

        # 标题
        title = QLabel("第三步：设置基站参数")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 5px;")
        layout.addWidget(title)

        # 参数表单
        form = QFormLayout()

        self.band_combo = QComboBox()
        self.band_combo.addItems(BAND_CONFIGS.keys())
        self.band_combo.setCurrentText("3.5GHz")
        self.band_combo.currentTextChanged.connect(self._on_band_changed)
        form.addRow("频段:", self.band_combo)

        self.isr_label = QLabel(f"站间距: {BAND_CONFIGS['3.5GHz'].ideal_isr_km} km")
        self.isr_label.setStyleSheet("color: #3498db;")
        form.addRow("", self.isr_label)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(20, 60)
        self.height_spin.setValue(45)
        self.height_spin.setSuffix(" 米")
        form.addRow("塔高:", self.height_spin)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["宏站(MACRO)", "微站(SMALL)", "室内站(INDOOR)"])
        form.addRow("基站类型:", self.type_combo)

        self.sector_spin = QSpinBox()
        self.sector_spin.setRange(0, 6)
        self.sector_spin.setValue(3)
        self.sector_spin.setToolTip("0=全向, 3=三扇区, 6=六扇区")
        form.addRow("扇区数:", self.sector_spin)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems(["城市(URBAN)", "郊区(SUBURBAN)", "农村(RURAL)"])
        form.addRow("场景:", self.scenario_combo)

        layout.addLayout(form)
        layout.addStretch()

        return page

    def _build_step4(self):
        """生成基站布局"""
        page = QWidget()
        layout = QVBoxLayout(page)

        # 标题
        title = QLabel("第四步：生成基站布局")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 5px;")
        layout.addWidget(title)

        # 一键生成
        btn_generate = QPushButton("一键生成蜂窝拓扑")
        btn_generate.setStyleSheet("font-size: 14px; padding: 10px; background-color: #e74c3c; color: white;")
        btn_generate.clicked.connect(self._generate_hex_grid)
        layout.addWidget(btn_generate)

        # 手动添加
        btn_row = QHBoxLayout()

        self.add_station_btn = QPushButton("手动添加基站")
        self.add_station_btn.setCheckable(True)
        self.add_station_btn.setStyleSheet("padding: 8px;")
        self.add_station_btn.clicked.connect(self._toggle_add_station)
        btn_row.addWidget(self.add_station_btn)

        btn_clear = QPushButton("清除所有站点")
        btn_clear.setStyleSheet("padding: 8px;")
        btn_clear.clicked.connect(self._clear_all_sites)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)

        # 避让
        avoid_row = QHBoxLayout()
        btn_avoid = QPushButton("加载避让数据")
        btn_avoid.clicked.connect(self._load_avoidance)
        avoid_row.addWidget(btn_avoid)

        btn_clear_avoid = QPushButton("清除避让")
        btn_clear_avoid.clicked.connect(self._clear_avoidance)
        avoid_row.addWidget(btn_clear_avoid)
        layout.addLayout(avoid_row)

        self.avoid_label = QLabel("未加载避让数据")
        self.avoid_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.avoid_label)

        layout.addStretch()

        return page

    def _build_step5(self):
        """管线设计"""
        page = QWidget()
        layout = QVBoxLayout(page)

        # 标题
        title = QLabel("第五步：管线设计")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 5px;")
        layout.addWidget(title)

        # 说明
        desc = QLabel("设置机房位置，生成基站到机房的管线")
        desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(desc)

        # 机房位置
        room_group = QGroupBox("机房位置")
        room_layout = QVBoxLayout()

        # 坐标输入
        coord_layout = QFormLayout()

        self.room_lon_spin = QDoubleSpinBox()
        self.room_lon_spin.setRange(70.0, 140.0)
        self.room_lon_spin.setValue(111.0)  # 山西运城运城学院
        self.room_lon_spin.setDecimals(6)
        coord_layout.addRow("经度:", self.room_lon_spin)

        self.room_lat_spin = QDoubleSpinBox()
        self.room_lat_spin.setRange(20.0, 50.0)
        self.room_lat_spin.setValue(35.0)  # 山西运城运城学院
        self.room_lat_spin.setDecimals(6)
        coord_layout.addRow("纬度:", self.room_lat_spin)

        room_layout.addLayout(coord_layout)

        # 在地图上添加机房按钮
        btn_add_room = QPushButton("在地图上点击添加机房")
        btn_add_room.setStyleSheet("padding: 8px; background-color: #9b59b6; color: white;")
        btn_add_room.clicked.connect(self._toggle_add_room)
        room_layout.addWidget(btn_add_room)

        # 机房列表
        self.room_list_label = QLabel("已添加机房: 0个")
        self.room_list_label.setStyleSheet("color: #2c3e50; font-size: 11px;")
        room_layout.addWidget(self.room_list_label)

        room_group.setLayout(room_layout)
        layout.addWidget(room_group)

        # 管线类型选择
        type_group = QGroupBox("管线参数")
        type_layout = QFormLayout()

        self.pipeline_type_combo = QComboBox()
        self.pipeline_type_combo.addItems(["直埋光缆", "通信管道", "架空光缆"])
        type_layout.addRow("管线类型:", self.pipeline_type_combo)

        self.route_type_combo = QComboBox()
        self.route_type_combo.addItems(["直线路径", "曼哈顿路径"])
        type_layout.addRow("路由类型:", self.route_type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 生成管线按钮
        btn_row = QHBoxLayout()

        btn_generate = QPushButton("生成管线")
        btn_generate.setStyleSheet("padding: 10px; background-color: #e67e22; color: white;")
        btn_generate.clicked.connect(self._generate_pipelines)
        btn_row.addWidget(btn_generate)

        btn_clear = QPushButton("清除管线")
        btn_clear.setStyleSheet("padding: 10px;")
        btn_clear.clicked.connect(self._clear_pipelines)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)

        # 管线统计
        self.pipeline_stats_label = QLabel("管线: 0条, 总长度: 0m")
        self.pipeline_stats_label.setStyleSheet("color: #2c3e50; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.pipeline_stats_label)

        layout.addStretch()

        return page

    def _build_step6(self):
        """分析与导出"""
        page = QWidget()
        layout = QVBoxLayout(page)

        # 标题
        title = QLabel("第六步：分析与导出")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 5px;")
        layout.addWidget(title)

        # 覆盖分析
        btn_heatmap = QPushButton("生成覆盖热力图")
        btn_heatmap.setStyleSheet("padding: 10px; background-color: #9b59b6; color: white;")
        btn_heatmap.clicked.connect(self._generate_heatmap)
        layout.addWidget(btn_heatmap)

        # 导出行
        export_row = QHBoxLayout()

        btn_export = QPushButton("导出当前视图")
        btn_export.setStyleSheet("padding: 10px; background-color: #3498db; color: white;")
        btn_export.clicked.connect(self._export_pdf)
        export_row.addWidget(btn_export)

        layout.addLayout(export_row)

        # 保存加载行
        file_row = QHBoxLayout()

        btn_save = QPushButton("保存方案")
        btn_save.setStyleSheet("padding: 10px;")
        btn_save.clicked.connect(self._save_design)
        file_row.addWidget(btn_save)

        btn_load = QPushButton("加载方案")
        btn_load.setStyleSheet("padding: 10px;")
        btn_load.clicked.connect(self._load_design)
        file_row.addWidget(btn_load)
        layout.addLayout(file_row)

        # 后端同步
        btn_sync = QPushButton("同步到M03后端")
        btn_sync.setStyleSheet("padding: 10px; background-color: #1abc9c; color: white;")
        btn_sync.clicked.connect(self._sync_to_backend)
        layout.addWidget(btn_sync)

        layout.addStretch()

        return page

    def _build_site_table(self):
        group = QGroupBox("站点列表")
        layout = QVBoxLayout()

        self.site_table = QTableWidget()
        self.site_table.setColumnCount(5)
        self.site_table.setHorizontalHeaderLabels(["ID", "类型", "塔高", "经度", "纬度"])
        self.site_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.site_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.site_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.site_table.setMaximumHeight(150)
        layout.addWidget(self.site_table)

        # 操作按钮
        btn_row = QHBoxLayout()

        btn_fly = QPushButton("定位到选中站点")
        btn_fly.clicked.connect(self._fly_to_site)
        btn_row.addWidget(btn_fly)

        btn_delete = QPushButton("删除选中站点")
        btn_delete.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_delete.clicked.connect(self._delete_site)
        btn_row.addWidget(btn_delete)
        layout.addLayout(btn_row)

        self.stats_label = QLabel("站点: 0")
        self.stats_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.stats_label)

        group.setLayout(layout)
        return group

    # =================================================================
    #  第一步：底图
    # =================================================================

    def _add_gaode_basemap(self):
        try:
            ok, msg = add_gaode_satellite()
            self._log(f"高德卫星图{'已加载' if ok else '加载失败: ' + msg}")
        except Exception as e:
            self._log(f"加载失败: {e}")

    def _add_osm_basemap(self):
        try:
            ok, msg = add_osm()
            self._log(f"OSM地图{'已加载' if ok else '加载失败: ' + msg}")
        except Exception as e:
            self._log(f"加载失败: {e}")

    # =================================================================
    #  第二步：选择区域
    # =================================================================

    def _select_extent(self):
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()

        # 转换到WGS84
        project_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        if project_crs != wgs84:
            transform = QgsCoordinateTransform(project_crs, wgs84, QgsProject.instance())
            extent_wgs84 = transform.transform(extent)
        else:
            extent_wgs84 = extent

        # 计算面积
        area_km2 = self._calc_area_km2(extent_wgs84)

        if area_km2 > 50:
            QMessageBox.warning(self, "范围太大",
                                f"当前可视范围约 {area_km2:.0f} km²，太大。\n"
                                f"请缩放到较小区域（建议<10km²）。")
            return

        self.selected_extent = (extent_wgs84.xMinimum(), extent_wgs84.yMinimum(),
                                extent_wgs84.xMaximum(), extent_wgs84.yMaximum())

        self.extent_label.setText(
            f"已选择: [{self.selected_extent[0]:.4f}, {self.selected_extent[1]:.4f}] "
            f"→ [{self.selected_extent[2]:.4f}, {self.selected_extent[3]:.4f}]\n"
            f"面积约 {area_km2:.1f} km²"
        )
        self.extent_label.setStyleSheet("color: #27ae60;")
        self._add_extent_rubber(extent)
        self._log(f"已选择区域: {area_km2:.1f} km²")

    def _add_extent_rubber(self, rect):
        canvas = self.iface.mapCanvas()
        # 用线几何绘制边框，天然无填充
        rb = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
        rb.setColor(QColor(255, 0, 0))
        rb.setWidth(3)
        rb.addPoint(QgsPointXY(rect.xMinimum(), rect.yMinimum()), False)
        rb.addPoint(QgsPointXY(rect.xMaximum(), rect.yMinimum()), False)
        rb.addPoint(QgsPointXY(rect.xMaximum(), rect.yMaximum()), False)
        rb.addPoint(QgsPointXY(rect.xMinimum(), rect.yMaximum()), False)
        rb.addPoint(QgsPointXY(rect.xMinimum(), rect.yMinimum()), True)
        self._extent_bands.append(rb)
        canvas.refresh()

    def _clear_extent(self):
        canvas = self.iface.mapCanvas()
        for rb in self._extent_bands:
            canvas.scene().removeItem(rb)
        self._extent_bands.clear()
        self.selected_extent = None
        self.extent_label.setText("未选择区域")
        self.extent_label.setStyleSheet("color: gray;")
        canvas.refresh()

    # =================================================================
    #  第三步：参数
    # =================================================================

    def _on_band_changed(self, band):
        if band in BAND_CONFIGS:
            self.isr_label.setText(f"站间距: {BAND_CONFIGS[band].ideal_isr_km} km")

    # =================================================================
    #  第四步：生成基站
    # =================================================================

    def _generate_hex_grid(self):
        if not self.selected_extent:
            QMessageBox.warning(self, "提示", "请先在第二步选择设计区域")
            return

        bbox = self.selected_extent
        band_key = self.band_combo.currentText()
        config = BAND_CONFIGS[band_key]
        isr_km = config.ideal_isr_km

        area_km2 = self._calc_area_km2_from_bbox(bbox)
        self._log(f"选区面积: {area_km2:.2f} km²")
        self._log(f"频段: {band_key}, 站间距: {isr_km} km")

        if area_km2 < isr_km * isr_km:
            QMessageBox.warning(self, "面积太小",
                                f"选区面积 {area_km2:.2f} km² 太小，\n"
                                f"站间距 {isr_km} km，至少需要 {isr_km*isr_km:.1f} km²。\n"
                                f"请放大地图后重新选择。")
            return

        self._show_progress(True, 0)

        try:
            centers = generate_hex_grid(bbox, isr_km)
            self._log(f"网格点: {len(centers)} 个")
            self._show_progress(True, 30)

            avoidance_checker = None
            if self._avoidance_features:
                avoidance_checker = AvoidanceChecker()
                for feat in self._avoidance_features:
                    coords = avoidance_checker._extract_coords(feat)
                    if coords:
                        avoidance_checker.avoidance_polygons.append(feat)
                centers = avoidance_checker.filter_valid_sites(centers)
                self._log(f"避让过滤后: {len(centers)} 个")

            if len(centers) > 200:
                centers = centers[:200]
                self._log("截取前200个站点")

            self._show_progress(True, 60)

            engine_sites = generate_sites_from_grid(
                centers, config,
                site_type=self.type_combo.currentText().split("(")[1].rstrip(")"),
                tower_height=float(self.height_spin.value()),
                num_sectors=self.sector_spin.value(),
                bbox=bbox,
            )

            sites = []
            for i, es in enumerate(engine_sites):
                site = {
                    'site_id': es.site_id,
                    'name': es.name,
                    'longitude': round(es.longitude, 7),
                    'latitude': round(es.latitude, 7),
                    'tower_height': es.tower_height,
                    'site_type': es.site_type,
                    'num_sectors': self.sector_spin.value(),
                    'scenario': es.scenario,
                    'band': band_key,
                    'frequency': config.frequency_mhz,
                    'power': config.default_power_w,
                    'gain': config.default_gain_dbi,
                    'is_valid': True,
                }
                sites.append(site)

            self._show_progress(True, 90)

            self.generated_sites = sites
            self._add_sites_to_map(sites)
            self._update_site_table()
            self._log(f"完成！生成 {len(sites)} 个基站")
            self._show_progress(False)
            self.design_completed.emit(sites)

        except Exception as e:
            self._log(f"错误: {e}")
            QMessageBox.critical(self, "生成失败", str(e))
            self._show_progress(False)

    def _toggle_add_station(self, checked):
        if checked:
            canvas = self.iface.mapCanvas()
            self._station_tool = AddStationTool(canvas)
            self._station_tool.point_clicked.connect(self._on_station_clicked)
            canvas.setMapTool(self._station_tool)
            self.add_station_btn.setText("停止添加（左键点击地图）")
            self._log("左键点击地图添加基站")
        else:
            if hasattr(self, '_station_tool'):
                self.iface.mapCanvas().unsetMapTool(self._station_tool)
            self.add_station_btn.setText("手动添加基站")

    def _on_station_clicked(self, lon, lat):
        dialog = StationDialog(lon, lat, parent=self)
        if dialog.exec_() != StationDialog.Accepted:
            return

        data = dialog.get_site_data()
        band_key = self.band_combo.currentText()
        config = BAND_CONFIGS[band_key]
        site = {
            'site_id': data['site_id'],
            'name': data['name'],
            'longitude': data['longitude'],
            'latitude': data['latitude'],
            'tower_height': data['tower_height'],
            'site_type': data['site_type'],
            'num_sectors': self.sector_spin.value(),
            'scenario': self.scenario_combo.currentText().split("(")[1].rstrip(")"),
            'band': band_key,
            'frequency': config.frequency_mhz,
            'power': config.default_power_w,
            'gain': config.default_gain_dbi,
            'is_valid': True,
        }

        self.generated_sites.append(site)
        self._add_marker(lon, lat)
        self._update_site_table()
        self._log(f"已添加: {data['name']}")

    def _add_marker(self, lon, lat):
        """添加手动基站标记 - 使用与蜂窝拓扑相同的大小"""
        canvas = self.iface.mapCanvas()

        # 外圈白色（增加可见性）
        rb_outer = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_outer.setColor(QColor(255, 255, 255))
        rb_outer.setFillColor(QColor(255, 255, 255))
        rb_outer.setIconSize(16)
        rb_outer.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_outer.addPoint(QgsPointXY(lon, lat))

        # 内圈蓝色（与蜂窝拓扑相同的蓝色）
        rb_inner = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_inner.setColor(QColor(0, 120, 255))
        rb_inner.setFillColor(QColor(0, 120, 255))
        rb_inner.setIconSize(10)
        rb_inner.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_inner.addPoint(QgsPointXY(lon, lat))

        self._marker_bands.extend([rb_outer, rb_inner])
        canvas.refresh()

    def _clear_all_sites(self):
        if not self.generated_sites:
            return
        reply = QMessageBox.question(self, "确认", "确定清除所有站点？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.generated_sites.clear()
            self._update_site_table()
            # 清除基站图层
            layers = QgsProject.instance().mapLayersByName("基站设计")
            if layers:
                layers[0].startEditing()
                layers[0].deleteFeatures(layers[0].allFeatureIds())
                layers[0].commitChanges()
            # 清除手动添加的标记
            canvas = self.iface.mapCanvas()
            for rb in self._marker_bands:
                canvas.scene().removeItem(rb)
            self._marker_bands.clear()
            canvas.refresh()
            self._log("已清除所有站点")

    def _load_avoidance(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self, "选择避让数据", "", "GeoJSON (*.geojson *.json);;All (*)")
        if not fpath:
            return
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._avoidance_features = data.get('features', [])
            self.avoid_label.setText(f"已加载: {os.path.basename(fpath)} ({len(self._avoidance_features)}个)")
            self.avoid_label.setStyleSheet("color: #27ae60;")
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))

    def _clear_avoidance(self):
        self._avoidance_features = []
        self.avoid_label.setText("未加载避让数据")
        self.avoid_label.setStyleSheet("color: gray;")

    # =================================================================
    #  第五步：管线设计
    # =================================================================

    def _toggle_add_room(self):
        """激活添加机房模式"""
        canvas = self.iface.mapCanvas()
        self._room_tool = AddRoomTool(canvas)
        self._room_tool.point_clicked.connect(self._on_room_clicked)
        canvas.setMapTool(self._room_tool)
        self._log("左键点击地图添加机房位置")

    def _on_room_clicked(self, lon, lat):
        """地图点击添加机房 - 直接生成，无需输入"""
        # 自动生成机房编号
        self.room_counter += 1
        room_id = f"ROOM-{self.room_counter:03d}"
        room_name = f"机房{self.room_counter}"

        # 机房数据
        data = {
            'room_id': room_id,
            'name': room_name,
            'room_type': '汇聚机房',
            'longitude': lon,
            'latitude': lat,
            'capacity': 10,
        }

        # 更新机房位置SpinBox
        self.room_lon_spin.setValue(lon)
        self.room_lat_spin.setValue(lat)

        # 保存机房数据
        self.machine_rooms.append(data)

        # 添加机房标记到地图
        self._add_room_marker(lon, lat, room_name)

        # 更新机房列表显示
        self.room_list_label.setText(f"已添加机房: {len(self.machine_rooms)}个")

        self._log(f"已添加机房: {room_name} ({lon:.6f}, {lat:.6f})")

        # 取消添加模式
        if hasattr(self, '_room_tool'):
            self.iface.mapCanvas().unsetMapTool(self._room_tool)

    def _find_nearest_room(self, site_lon, site_lat):
        """找到距离基站最近的机房"""
        import math

        def calc_distance(lon1, lat1, lon2, lat2):
            """计算两点间距离（米）"""
            R = 6371000
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)
            a = (math.sin(delta_phi / 2) ** 2 +
                 math.cos(phi1) * math.cos(phi2) *
                 math.sin(delta_lambda / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        nearest = None
        min_dist = float('inf')

        for room in self.machine_rooms:
            dist = calc_distance(site_lon, site_lat, room['longitude'], room['latitude'])
            if dist < min_dist:
                min_dist = dist
                nearest = room

        return nearest

    def _add_room_marker(self, lon, lat, name):
        """添加机房标记到地图"""
        canvas = self.iface.mapCanvas()

        # 外圈白色
        rb_outer = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_outer.setColor(QColor(255, 255, 255))
        rb_outer.setFillColor(QColor(255, 255, 255))
        rb_outer.setIconSize(20)
        rb_outer.setIcon(QgsRubberBand.ICON_DIAMOND)
        rb_outer.addPoint(QgsPointXY(lon, lat))

        # 内圈紫色（机房颜色）
        rb_inner = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_inner.setColor(QColor(155, 89, 182))
        rb_inner.setFillColor(QColor(155, 89, 182))
        rb_inner.setIconSize(14)
        rb_inner.setIcon(QgsRubberBand.ICON_DIAMOND)
        rb_inner.addPoint(QgsPointXY(lon, lat))

        self._marker_bands.extend([rb_outer, rb_inner])
        canvas.refresh()

    def _generate_pipelines(self):
        """生成管线"""
        if not self.generated_sites:
            QMessageBox.warning(self, "提示", "请先生成基站")
            return

        # 检查是否有可用的机房
        if not self.machine_rooms:
            # 如果没有在地图上添加机房，使用输入框的经纬度
            self.machine_rooms.append({
                'room_id': 'ROOM-001',
                'name': '默认机房',
                'room_type': '汇聚机房',
                'longitude': self.room_lon_spin.value(),
                'latitude': self.room_lat_spin.value(),
                'capacity': 10,
            })

        self._log("正在生成管线...")
        self._show_progress(True, 0)

        try:
            # 获取管线类型
            type_map = {
                "直埋光缆": PipelineType.DIRECT_BURIED,
                "通信管道": PipelineType.DUCT,
                "架空光缆": PipelineType.AERIAL,
            }
            pipeline_type = type_map[self.pipeline_type_combo.currentText()]

            # 获取路由类型
            route_type = "direct" if self.route_type_combo.currentIndex() == 0 else "manhattan"

            self._show_progress(True, 30)

            # 为每个基站找到最近的机房，生成管线
            all_pipelines = []
            for i, site in enumerate(self.generated_sites):
                # 找到最近的机房
                nearest_room = self._find_nearest_room(site['longitude'], site['latitude'])

                # 生成单个基站到最近机房的管线
                from design_engine.pipeline import generate_pipeline_to_room
                pipeline = generate_pipeline_to_room(
                    site_lon=site['longitude'],
                    site_lat=site['latitude'],
                    room_lon=nearest_room['longitude'],
                    room_lat=nearest_room['latitude'],
                    pipeline_type=pipeline_type,
                    route_type=route_type,
                )
                pipeline.pipeline_id = f"PL-{i+1:04d}"
                pipeline.start_site_id = site['site_id']
                pipeline.end_site_id = nearest_room['room_id']
                all_pipelines.append(pipeline)

                self._show_progress(True, 30 + int((i + 1) / len(self.generated_sites) * 50))

            self._show_progress(True, 80)

            # 创建管线图层
            layer = create_pipeline_layer(all_pipelines, "通信管线")
            add_pipeline_labels(layer)

            # 保存管线数据
            self.generated_pipelines = all_pipelines

            # 更新统计
            total_volume = calculate_total_engineering_volume(all_pipelines)
            self.pipeline_stats_label.setText(
                f"管线: {len(all_pipelines)}条, 总长度: {total_volume['总长度(m)']:.0f}m"
            )

            self._show_progress(False)
            self._log(f"管线生成完成: {len(all_pipelines)}条, 总长度{total_volume['总长度(m)']:.0f}m")

            # 缩放到管线范围
            canvas = self.iface.mapCanvas()
            canvas.setExtent(layer.extent())
            canvas.refresh()

        except Exception as e:
            self._log(f"管线生成失败: {e}")
            self._show_progress(False)
            QMessageBox.critical(self, "错误", f"管线生成失败: {e}")

    def _clear_pipelines(self):
        """清除管线"""
        # 清除图层（无论是否有数据都清除）
        layers = QgsProject.instance().mapLayersByName("通信管线")
        if layers:
            for layer in layers:
                QgsProject.instance().removeMapLayer(layer.id())

        # 清除数据
        self.generated_pipelines.clear()

        # 更新统计
        self.pipeline_stats_label.setText("管线: 0条, 总长度: 0m")
        self.iface.mapCanvas().refresh()
        self._log("已清除所有管线")

    # =================================================================
    #  第六步：分析与导出
    # =================================================================

    def _generate_heatmap(self):
        if not self.generated_sites:
            QMessageBox.warning(self, "提示", "请先生成基站")
            return

        self._log("正在生成覆盖热力图...")
        self._show_progress(True, 0)

        try:
            band_key = self.band_combo.currentText()
            config = BAND_CONFIGS[band_key]
            tower_height = self.height_spin.value()
            radius_km = config.ideal_isr_km * 1.5
            scenario = self.scenario_combo.currentText().split("(")[1].rstrip(")")

            all_data = []
            total = len(self.generated_sites)

            for i, site in enumerate(self.generated_sites):
                data = generate_coverage_heatmap_data(
                    site_lon=site['longitude'],
                    site_lat=site['latitude'],
                    tx_height_m=tower_height,
                    frequency_mhz=config.frequency_mhz,
                    tx_power_w=config.default_power_w,
                    antenna_gain_dbi=config.default_gain_dbi,
                    radius_km=radius_km,
                    resolution_m=100,
                    rsrp_threshold_dbm=-110,
                    environment=scenario,
                )
                all_data.extend(data)
                self._show_progress(True, int((i + 1) / total * 80))

            if all_data:
                self._create_heatmap_layer(all_data)
                self._log(f"热力图已生成: {len(all_data)}个点, {total}个基站叠加")
            else:
                self._log("热力图数据为空")

            self._show_progress(False)

        except Exception as e:
            self._log(f"热力图生成失败: {e}")
            self._show_progress(False)

    def _create_heatmap_layer(self, data, site_lon=None, site_lat=None):
        """创建覆盖热力图 — 栅格渐变色块 + 图例"""
        import numpy as np
        from osgeo import gdal, osr
        import tempfile
        from qgis.core import (
            QgsSingleBandPseudoColorRenderer,
            QgsColorRampShader,
            QgsRasterShader
        )
        from qgis.PyQt.QtGui import QColor

        layer_name = "覆盖热力图"
        # 移除旧图层
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            QgsProject.instance().removeMapLayer(layers[0])

        # 计算栅格范围和分辨率
        lons = [d['longitude'] for d in data]
        lats = [d['latitude'] for d in data]

        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)

        # 分辨率（像素数）
        resolution = 200
        lon_step = (lon_max - lon_min) / resolution
        lat_step = (lat_max - lat_min) / resolution

        # 创建栅格数组（初始值为 NaN）
        raster = np.full((resolution, resolution), np.nan)

        # 将 RSRP 数据填入栅格（多站点叠加取最强信号）
        for d in data:
            col = int((d['longitude'] - lon_min) / lon_step)
            row = int((d['latitude'] - lat_min) / lat_step)
            if 0 <= col < resolution and 0 <= row < resolution:
                if np.isnan(raster[row, col]) or d['rsrp'] > raster[row, col]:
                    raster[row, col] = d['rsrp']

        # 创建临时 GeoTIFF 文件
        tiff_path = os.path.join(tempfile.gettempdir(), "heatmap_coverage.tif")
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(tiff_path, resolution, resolution, 1, gdal.GDT_Float32)

        # 设置地理变换和投影
        geotransform = (lon_min, lon_step, 0, lat_max, 0, -lat_step)
        ds.SetGeoTransform(geotransform)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())

        # 写入数据
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(np.nan)
        band.WriteArray(raster)
        band.FlushCache()
        ds = None

        # 加载栅格图层
        raster_layer = QgsRasterLayer(tiff_path, layer_name)
        if not raster_layer.isValid():
            self._log("栅格图层创建失败")
            return

        # 设置颜色渐变（红→黄→绿）
        color_ramp = QgsColorRampShader()
        color_ramp.setColorRampType(QgsColorRampShader.Interpolated)

        # RSRP 颜色映射：红色(强) → 橙色 → 黄色 → 黄绿色 → 绿色(弱)
        items = [
            QgsColorRampShader.ColorRampItem(-50, QColor(255, 0, 0), '强信号 (-50 dBm)'),
            QgsColorRampShader.ColorRampItem(-65, QColor(255, 100, 0), '较强 (-65 dBm)'),
            QgsColorRampShader.ColorRampItem(-80, QColor(255, 200, 0), '良好 (-80 dBm)'),
            QgsColorRampShader.ColorRampItem(-90, QColor(200, 255, 0), '一般 (-90 dBm)'),
            QgsColorRampShader.ColorRampItem(-100, QColor(100, 255, 0), '较弱 (-100 dBm)'),
            QgsColorRampShader.ColorRampItem(-110, QColor(0, 200, 0), '弱信号 (-110 dBm)'),
        ]
        color_ramp.setColorRampItemList(items)

        shader = QgsRasterShader()
        shader.setRasterShaderFunction(color_ramp)

        renderer = QgsSingleBandPseudoColorRenderer(
            raster_layer.dataProvider(), 1, shader
        )
        raster_layer.setRenderer(renderer)

        # 添加图层到项目
        QgsProject.instance().addMapLayer(raster_layer)

        # 自动缩放到热力图范围
        canvas = self.iface.mapCanvas()
        canvas.setExtent(raster_layer.extent())
        canvas.refresh()

        self._log(f"热力图已添加: {len(data)}个点, 自动缩放到覆盖范围")

    def _export_pdf(self):
        """导出当前视图为图片"""
        if not self.generated_sites:
            QMessageBox.warning(self, "导出", "没有站点数据")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出图片", "基站设计图.png", "PNG (*.png);;JPEG (*.jpg)")
        if not fpath:
            return

        try:
            canvas = self.iface.mapCanvas()

            # 如果有框选区域，先缩放到该区域
            if self.selected_extent:
                lon_min, lat_min, lon_max, lat_max = self.selected_extent
                extent = QgsRectangle(lon_min, lat_min, lon_max, lat_max)
                canvas.setExtent(extent)
                canvas.refresh()

            # 截取当前地图画布
            canvas.saveAsImage(fpath, None, "PNG")

            QMessageBox.information(self, "导出成功", f"已导出到:\n{fpath}")
            self._log("图片已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", str(e))

    def _save_design(self):
        if not self.generated_sites:
            QMessageBox.warning(self, "保存", "没有站点数据")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "保存方案", f"design_{datetime.now().strftime('%Y%m%d')}.geojson",
            "GeoJSON (*.geojson)")
        if not fpath:
            return

        features = []
        for s in self.generated_sites:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s['longitude'], s['latitude']]},
                "properties": s
            })

        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "band": self.band_combo.currentText(),
                "tower_height": self.height_spin.value(),
                "saved_at": datetime.now().isoformat(),
            }
        }

        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        QMessageBox.information(self, "保存成功", f"已保存到:\n{fpath}")

    def _load_design(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self, "加载方案", "", "GeoJSON (*.geojson);;All (*)")
        if not fpath:
            return

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            sites = []
            for feat in data.get('features', []):
                props = feat.get('properties', {})
                coords = feat.get('geometry', {}).get('coordinates', [0, 0])
                props['longitude'] = coords[0]
                props['latitude'] = coords[1]
                sites.append(props)

            self.generated_sites = sites
            self._add_sites_to_map(sites)
            self._update_site_table()

            props = data.get('properties', {})
            if 'band' in props:
                self.band_combo.setCurrentText(props['band'])
            if 'tower_height' in props:
                self.height_spin.setValue(props['tower_height'])

            self._log(f"已加载 {len(sites)} 个站点")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _sync_to_backend(self):
        if not self.generated_sites:
            QMessageBox.warning(self, "同步", "没有站点数据")
            return

        project_id, ok = QInputDialog.getInt(self, "项目ID", "请输入M03后端项目ID:", 101, 1, 99999)
        if not ok:
            return

        try:
            import requests
            design_data = {
                "projectId": project_id,
                "schemeName": f"基站设计_{datetime.now().strftime('%Y%m%d')}",
                "frequencyBand": self.band_combo.currentText(),
                "towerHeight": self.height_spin.value(),
                "totalSites": len(self.generated_sites),
                "validSites": len([s for s in self.generated_sites if s.get('is_valid', True)]),
                "sites": self.generated_sites
            }
            resp = requests.post("http://localhost:8083/api/m03/design/upload",
                                 json=design_data, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                if result.get('code') == 200:
                    QMessageBox.information(self, "同步成功",
                                            f"项目ID: {project_id}\n方案ID: {result.get('data')}")
                else:
                    QMessageBox.warning(self, "同步失败", result.get('message', ''))
            else:
                QMessageBox.warning(self, "同步失败", f"HTTP {resp.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "同步错误", str(e))

    # =================================================================
    #  地图渲染
    # =================================================================

    def _add_sites_to_map(self, sites):
        layer_name = "基站设计"
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer = layers[0]
            layer.startEditing()
            layer.deleteFeatures(layer.allFeatureIds())
        else:
            from qgis.PyQt.QtCore import QVariant
            layer = QgsVectorLayer("Point?crs=EPSG:4326", layer_name, "memory")
            layer.dataProvider().addAttributes([
                QgsField("site_id", QVariant.String),
                QgsField("name", QVariant.String),
                QgsField("site_type", QVariant.String),
                QgsField("tower_height", QVariant.Double),
            ])
            layer.updateFields()

            symbol_macro = QgsMarkerSymbol.createSimple({
                'name': 'circle', 'color': '#0078ff', 'size': '8',
                'outline_color': 'white', 'outline_width': '1'})
            symbol_small = QgsMarkerSymbol.createSimple({
                'name': 'circle', 'color': '#00ccff', 'size': '6',
                'outline_color': 'white', 'outline_width': '0.5'})
            symbol_indoor = QgsMarkerSymbol.createSimple({
                'name': 'circle', 'color': '#66ccff', 'size': '5',
                'outline_color': 'white', 'outline_width': '0.5'})

            categories = [
                QgsRendererCategory("MACRO", symbol_macro, "宏站"),
                QgsRendererCategory("SMALL", symbol_small, "微站"),
                QgsRendererCategory("INDOOR", symbol_indoor, "室内站"),
            ]
            layer.setRenderer(QgsCategorizedSymbolRenderer("site_type", categories))
            QgsProject.instance().addMapLayer(layer)

        layer.startEditing()
        feats = []
        for s in sites:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(
                QgsPointXY(s['longitude'], s['latitude'])))
            feat.setAttributes([
                s['site_id'], s['name'], s['site_type'], s['tower_height']
            ])
            feats.append(feat)
        layer.addFeatures(feats)
        layer.commitChanges()
        layer.updateExtents()
        layer.triggerRepaint()

        canvas = self.iface.mapCanvas()
        canvas.setExtent(layer.extent())
        canvas.refresh()

    # =================================================================
    #  站点管理
    # =================================================================

    def _update_site_table(self):
        """更新站点统计（简化版，不使用表格）"""
        self._log(f"当前站点: {len(self.generated_sites)}个")

    def _fly_to_site(self):
        """定位到站点（简化版）"""
        pass

    def _delete_site(self):
        """删除站点（简化版）"""
        pass

    # =================================================================
    #  工具方法
    # =================================================================

    def _calc_area_km2(self, extent):
        x_min, y_min, x_max, y_max = extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()
        if abs(x_min) <= 180 and abs(x_max) <= 180 and abs(y_min) <= 90 and abs(y_max) <= 90:
            return (x_max - x_min) * 111 * (y_max - y_min) * 111
        else:
            return abs(x_max - x_min) * abs(y_max - y_min) / 1e6

    def _calc_area_km2_from_bbox(self, bbox):
        lon_min, lat_min, lon_max, lat_max = bbox
        return (lon_max - lon_min) * 111 * (lat_max - lat_min) * 111

    def _log(self, text):
        self.log_text.append(f"哥哥: {text}")

    def _show_progress(self, show, value=0):
        self.progress.setVisible(show)
        if show:
            self.progress.setValue(value)
        QApplication.processEvents()
