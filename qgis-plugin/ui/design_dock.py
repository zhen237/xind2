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
import subprocess
import json
from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QFileDialog, QMessageBox, QApplication,
    QTextEdit, QInputDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox,
    QDialog, QLineEdit, QMenu, QStackedWidget,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSortFilterProxyModel
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsProject, QgsRectangle, QgsPointXY, QgsWkbTypes,
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsField,
    QgsMarkerSymbol, QgsFillSymbol, QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
)
from qgis.gui import QgsRubberBand

from design_engine.rules import BAND_CONFIGS
from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
from design_engine.coverage_renderer import generate_raster_heatmap_data, export_heatmap_as_geotiff
from design_engine.avoidance import AvoidanceChecker

# ── 导入 UI 辅助模块 ─────────────────────────────────────────
from ui.styles import PluginTheme
from ui.guards import require_sites, require_extent, require_rooms, require_sites_count, safe_execute, log_call
from ui.enums import PIPELINE_TYPE_REVERSE_MAP as PT_REVERSE, PIPELINE_TYPE_CN_MAP as PT_CN
from design_engine.pipeline import (
    generate_pipelines_for_sites, calculate_total_engineering_volume,
    generate_shared_pipelines, calculate_shared_engineering_volume,
    calculate_pipeline_cost, calculate_total_cost,
    generate_pipeline_report_text, export_pipeline_report_csv,
    generate_direct_route, generate_manhattan_route,
    Pipeline, PipelineType, PipelineConfig,
    check_pipeline_ocean_conflict,
)
from layers.pipeline_layer import (
    create_pipeline_layer, create_connection_layer,
    get_pipeline_info, export_pipelines_to_geojson
)
from ui.basemap import add_gaode_satellite, add_osm
from tools.station_tool import AddStationTool
from ui.station_dialog import StationDialog
from tools.room_tool import AddRoomTool
from ui.room_dialog import RoomDialog
from models.machine_room import MachineRoom
from design_engine.layout_export import (
    create_design_layout, add_map_to_layout, add_title_to_layout,
    add_info_box_to_layout, add_legend_to_layout, add_scale_bar_to_layout,
    add_north_arrow_to_layout, export_layout_to_pdf,
    create_standard_design_drawing,
)
from design_engine.cad_export import export_design_to_cad
from design_engine.data_sync import DataSync
from design_engine.bom_extractor import BOMExtractor


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
        self.machine_rooms: list = []
        self.room_counter = 0
        self._pipeline_bands = []  # 管线标记

        # 数据同步 — 从环境变量或持久化配置获取后端地址
        import os
        backend_url = os.environ.get('XIND2_BACKEND_URL', 'http://localhost:8083')
        try:
            from config import get_setting
            backend_url = get_setting('backend_url', backend_url)
        except ImportError:
            self._log("无法导入config模块，使用默认后端地址", "WARN")
        self.sync_engine = DataSync(backend_url)

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
            btn.setStyleSheet(PluginTheme.STEP_BTN)
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
        self.log_text.setStyleSheet(PluginTheme.LOG_AREA)
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

        # 页面容器 — 使用 QStackedWidget 替代手动 hide/show
        self.page_stack = QStackedWidget()

        # 添加所有页面
        for i in range(len(steps)):
            self.page_stack.addWidget(self.step_pages[i])

        right_layout.addWidget(self.page_stack)

        # 进度条 + 取消按钮（可取消进度条）
        progress_container = QWidget()
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(6)

        self.progress = QProgressBar()
        self.progress.setStyleSheet(PluginTheme.PROGRESS_BAR)
        self.progress.setVisible(False)
        progress_layout.addWidget(self.progress, stretch=1)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(PluginTheme.CANCEL_BTN)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_progress)
        progress_layout.addWidget(self.cancel_btn)

        right_layout.addWidget(progress_container)

        self._cancel_requested = False

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(PluginTheme.STATUS_BAR)
        right_layout.addWidget(self.status_label)

        right_layout.addStretch()
        main_layout.addWidget(right_panel)

        self.setWidget(main)

        # 默认显示第一步
        self._switch_step(0)

        # 恢复上次的配置偏好
        try:
            from config import restore_config
            restore_config(self)
        except ImportError:
            self._log("无法导入config模块，跳过配置恢复", "DEBUG")

    def _switch_step(self, step_index):
        """切换步骤页面 — 使用 QStackedWidget"""
        # 切换页面
        self.page_stack.setCurrentIndex(step_index)

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

        # 站点列表
        layout.addWidget(self._build_site_table())

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

        # 方式1：在地图上点击添加
        btn_add_room = QPushButton("📍 在地图上点击添加机房")
        btn_add_room.setStyleSheet("padding: 10px; background-color: #9b59b6; color: white; font-weight: bold;")
        btn_add_room.clicked.connect(self._toggle_add_room)
        room_layout.addWidget(btn_add_room)

        # 分隔线
        sep = QLabel("─── 或者手动输入坐标 ───")
        sep.setStyleSheet("color: #95a5a6; font-size: 11px;")
        sep.setAlignment(Qt.AlignCenter)
        room_layout.addWidget(sep)

        # 方式2：手动输入坐标
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

        btn_add_by_coord = QPushButton("按坐标添加机房")
        btn_add_by_coord.setStyleSheet("padding: 8px; background-color: #8e44ad; color: white;")
        btn_add_by_coord.clicked.connect(self._add_room_by_coord)
        room_layout.addWidget(btn_add_by_coord)

        # 机房列表
        self.room_list_label = QLabel("已添加机房: 0个")
        self.room_list_label.setStyleSheet("color: #2c3e50; font-size: 11px; font-weight: bold;")
        room_layout.addWidget(self.room_list_label)

        room_group.setLayout(room_layout)
        layout.addWidget(room_group)

        # 管线类型选择
        type_group = QGroupBox("管线参数")
        type_layout = QFormLayout()

        self.pipeline_type_combo = QComboBox()
        self.pipeline_type_combo.addItems(["直埋光缆", "通信管道", "架空光缆"])
        self.pipeline_type_combo.currentTextChanged.connect(self._on_pipeline_type_changed)
        type_layout.addRow("管线类型:", self.pipeline_type_combo)

        # 每米价格
        self.price_per_meter_label = QLabel("15 元/米")
        self.price_per_meter_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        type_layout.addRow("每米价格:", self.price_per_meter_label)

        self.route_type_combo = QComboBox()
        self.route_type_combo.addItems(["直线路径", "曼哈顿路径"])
        type_layout.addRow("路由类型:", self.route_type_combo)

        # 共享路由选项
        self.share_route_check = QCheckBox("启用共享管线路由")
        self.share_route_check.setChecked(True)
        self.share_route_check.setToolTip("多基站到同一机房的管线共享重叠路段，减少总工程量")
        type_layout.addRow("", self.share_route_check)

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
        self.pipeline_stats_label = QLabel("管线: 0条")
        self.pipeline_stats_label.setStyleSheet("color: #2c3e50; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.pipeline_stats_label)

        self.volume_label = QLabel("")
        self.volume_label.setStyleSheet("color: #3498db; font-size: 11px;")
        layout.addWidget(self.volume_label)

        # 成本统计
        self.cost_stats_label = QLabel("总成本: 0元")
        self.cost_stats_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.cost_stats_label)

        # 图例
        legend_group = QGroupBox("图例")
        legend_layout = QVBoxLayout()

        legend_direct = QLabel("🟤 棕色 - 直埋光缆")
        legend_direct.setStyleSheet("font-size: 11px;")
        legend_layout.addWidget(legend_direct)

        legend_duct = QLabel("🔵 蓝色 - 通信管道")
        legend_duct.setStyleSheet("font-size: 11px;")
        legend_layout.addWidget(legend_duct)

        legend_aerial = QLabel("🟢 绿色 - 架空光缆")
        legend_aerial.setStyleSheet("font-size: 11px;")
        legend_layout.addWidget(legend_aerial)

        legend_group.setLayout(legend_layout)
        layout.addWidget(legend_group)

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

        # 工程量报表
        report_group = QGroupBox("工程量报表")
        report_layout = QVBoxLayout()

        btn_report_txt = QPushButton("导出工程量报表 (TXT)")
        btn_report_txt.setStyleSheet("padding: 10px; background-color: #e67e22; color: white;")
        btn_report_txt.clicked.connect(self._export_report_txt)
        report_layout.addWidget(btn_report_txt)

        btn_report_csv = QPushButton("导出工程量报表 (CSV)")
        btn_report_csv.setStyleSheet("padding: 10px; background-color: #e67e22; color: white;")
        btn_report_csv.clicked.connect(self._export_report_csv)
        report_layout.addWidget(btn_report_csv)

        report_group.setLayout(report_layout)
        layout.addWidget(report_group)

        # 导出行
        export_row = QHBoxLayout()

        btn_export = QPushButton("导出设计图纸")
        btn_export.setStyleSheet("padding: 10px; background-color: #3498db; color: white;")
        btn_export.clicked.connect(self._export_pdf)
        export_row.addWidget(btn_export)

        btn_bom = QPushButton("导出BOM清单")
        btn_bom.setStyleSheet("padding: 10px; background-color: #27ae60; color: white;")
        btn_bom.clicked.connect(self._export_bom)
        export_row.addWidget(btn_bom)

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
        group = QGroupBox("基站设计明细")
        layout = QVBoxLayout()

        # ── 搜索框 ────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        search_row.addWidget(search_label)

        self.site_search = QLineEdit()
        self.site_search.setPlaceholderText("输入站点ID、名称、类型、频段...")
        self.site_search.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #3498db;
                border-radius: 4px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #1abc9c;
            }
        """)
        self.site_search.textChanged.connect(self._filter_site_table)
        search_row.addWidget(self.site_search, stretch=1)

        clear_btn = QPushButton("清除")
        clear_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        clear_btn.clicked.connect(lambda: self.site_search.clear())
        search_row.addWidget(clear_btn)

        layout.addLayout(search_row)

        self.site_table = QTableWidget()
        self.site_table.setColumnCount(12)
        headers = [
            "站点ID", "名称", "站型", "场景", "塔高(m)",
            "频段", "频率(MHz)", "功率(W)", "方位角",
            "覆盖半径(km)", "站间距(km)", "坐标"
        ]
        self.site_table.setHorizontalHeaderLabels(headers)
        header = self.site_table.horizontalHeader()
        # 前11列固定宽度，最后一列自适应
        widths = [110, 90, 55, 55, 60, 55, 65, 50, 70, 75, 65, 0]
        for i, w in enumerate(widths[:-1]):
            header.setSectionResizeMode(i, QHeaderView.Fixed)
            self.site_table.setColumnWidth(i, w)
        header.setSectionResizeMode(11, QHeaderView.Stretch)

        self.site_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.site_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.site_table.setAlternatingRowColors(True)
        self.site_table.setSortingEnabled(True)  # 启用点击列头排序

        # ── 右键菜单 ──────────────────────────────────────────
        self.site_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.site_table.customContextMenuRequested.connect(self._show_site_context_menu)

        layout.addWidget(self.site_table)

        # 操作按钮行
        btn_row = QHBoxLayout()

        btn_fly = QPushButton("定位到选中站点")
        btn_fly.clicked.connect(self._fly_to_site)
        btn_row.addWidget(btn_fly)

        btn_delete = QPushButton("删除选中站点")
        btn_delete.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_delete.clicked.connect(self._delete_site)
        btn_row.addWidget(btn_delete)

        btn_compare = QPushButton("频段对比")
        btn_compare.setStyleSheet("background-color: #9b59b6; color: white;")
        btn_compare.clicked.connect(self._show_band_comparison)
        btn_row.addWidget(btn_compare)

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

    def _on_pipeline_type_changed(self, type_text):
        """管线类型变化时更新每米价格显示"""
        price_map = {
            "直埋光缆": 15,
            "通信管道": 45,
            "架空光缆": 18,
        }
        price = price_map.get(type_text, 15)
        self.price_per_meter_label.setText(f"{price} 元/米")

    # =================================================================
    #  第四步：生成基站
    # =================================================================

    @require_extent("请先在第二步选择设计区域")
    @safe_execute(show_errors=True)
    def _generate_hex_grid(self):
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

        centers = generate_hex_grid(bbox, isr_km)
        self._log(f"网格点: {len(centers)} 个")
        self._show_progress(True, 30)
        self._check_cancelled()

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
        self._check_cancelled()

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
                'beamwidth_h': 65.0,  # 默认水平波束宽度，用于热力图渲染
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
        self._current_band = band_key
        self._current_scenario = es.scenario  # from last site

        self._add_sites_to_map(sites)
        self._update_site_table()
        self._log(f"完成！生成 {len(sites)} 个基站")
        self._show_progress(False)
        self.design_completed.emit(sites)

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
        valid, msg = self._validate_coords(lon, lat)
        if not valid:
            QMessageBox.warning(self, "坐标无效", msg)
            self._log(f"手动添加站点失败: {msg}")
            return

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
        """地图点击添加机房 - 使用 RoomDialog 交互式输入"""
        # 转换坐标为WGS84经纬度
        canvas = self.iface.mapCanvas()
        project_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        if project_crs != wgs84:
            transform = QgsCoordinateTransform(project_crs, wgs84, QgsProject.instance())
            point = transform.transform(lon, lat)
            lon_wgs84 = point.x()
            lat_wgs84 = point.y()
        else:
            lon_wgs84 = lon
            lat_wgs84 = lat

        # 预生成默认编号
        self.room_counter += 1
        default_id = f"ROOM-{self.room_counter:03d}"
        default_name = f"汇聚机房{self.room_counter}"

        # 弹出 RoomDialog 进行交互式配置
        dialog = RoomDialog(lon_wgs84, lat_wgs84, parent=self)
        dialog.room_id_edit.setText(default_id)
        dialog.name_edit.setText(default_name)

        if dialog.exec_() != RoomDialog.Accepted:
            self.room_counter -= 1  # 用户取消了，回退计数器
            return

        room_data = dialog.get_room_data()
        lon_wgs84 = room_data['longitude']
        lat_wgs84 = room_data['latitude']

        # 机房数据
        data = MachineRoom(
            room_id=room_data['room_id'],
            name=room_data['name'],
            room_type=room_data['room_type'],
            longitude=lon_wgs84,
            latitude=lat_wgs84,
            capacity=room_data['capacity'],
        )

        # 保存机房数据
        self.machine_rooms.append(data)

        # 更新输入框（显示经纬度）
        self.room_lon_spin.setValue(lon_wgs84)
        self.room_lat_spin.setValue(lat_wgs84)

        # 添加机房标记到地图（使用原始坐标）
        self._add_room_marker(lon, lat, data.name)

        # 更新机房列表显示
        self.room_list_label.setText(f"已添加机房: {len(self.machine_rooms)}个")

        self._log(f"已添加机房: {data.name} ({lon_wgs84:.6f}, {lat_wgs84:.6f})")

        # 取消添加模式
        if hasattr(self, '_room_tool'):
            self.iface.mapCanvas().unsetMapTool(self._room_tool)

    def _add_room_by_coord(self):
        """按输入框坐标添加机房（含坐标验证）"""
        lon = self.room_lon_spin.value()
        lat = self.room_lat_spin.value()

        valid, msg = self._validate_coords(lon, lat)
        if not valid:
            QMessageBox.warning(self, "坐标无效", msg)
            self._log(f"添加机房失败: {msg}")
            return

        # 自动生成机房编号
        self.room_counter += 1
        room_id = f"ROOM-{self.room_counter:03d}"
        room_name = f"机房{self.room_counter}"

        # 机房数据
        data = MachineRoom(
            room_id=room_id,
            name=room_name,
            room_type='汇聚机房',
            longitude=lon,
            latitude=lat,
            capacity=10,
        )

        # 保存机房数据
        self.machine_rooms.append(data)

        # 添加机房标记到地图
        self._add_room_marker(lon, lat, room_name)

        # 更新机房列表显示
        self.room_list_label.setText(f"已添加机房: {len(self.machine_rooms)}个")

        self._log(f"已添加机房: {room_name} ({lon:.6f}, {lat:.6f})")

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
            dist = calc_distance(site_lon, site_lat, room.longitude, room.latitude)
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

    @require_sites("请先生成基站")
    @require_rooms("请至少添加一个机房！\n\n机房是管线生成的终点，必须先添加机房才能生成管线。\n\n添加方式：\n• 点击「在地图上点击添加机房」在地图上点击\n• 或输入坐标后点击「按坐标添加机房」")
    def _generate_pipelines(self):
        """生成管线 — 使用内存矢量图层渲染"""
        self._log(f"正在生成管线... (机房: {len(self.machine_rooms)}个)")
        self._show_progress(True, 10)

        try:
            # 获取管线类型 — 使用统一枚举映射
            pipeline_type = PT_REVERSE.get(
                self.pipeline_type_combo.currentText(),
                PipelineType.DIRECT_BURIED,  # 默认值
            )
            route_type = "direct" if self.route_type_combo.currentIndex() == 0 else "manhattan"

            self._show_progress(True, 20)

            # 获取机房坐标
            room = self.machine_rooms[0]
            room_lon = room.longitude
            room_lat = room.latitude

            # 为每个基站生成管线
            if self.share_route_check.isChecked():
                self._log("使用共享管线路由...")
                all_pipelines, shared_segments = generate_shared_pipelines(
                    sites=self.generated_sites,
                    room_lon=room_lon,
                    room_lat=room_lat,
                    pipeline_type=pipeline_type,
                    route_type=route_type,
                )
                volume = calculate_shared_engineering_volume(all_pipelines, shared_segments)
                self.volume_label.setText(
                    f"原始: {volume['原始总长度(m)']:.0f}m | 去重: {volume['去重后总长度(m)']:.0f}m | 节省: {volume['节省比例(%)']:.1f}%")
            else:
                self._log("生成管线...")
                all_pipelines = generate_pipelines_for_sites(
                    sites=self.generated_sites,
                    room_lon=room_lon,
                    room_lat=room_lat,
                    pipeline_type=pipeline_type,
                    route_type=route_type,
                )
                volume = calculate_total_engineering_volume(all_pipelines)
                self.volume_label.setText(
                    f"管线数: {volume['管线总数']} | 总长: {volume['总长度(m)']:.0f}m")

            # 保存数据
            self.generated_pipelines = all_pipelines

            # 修复5: 检查管线是否与海洋区域冲突
            ocean_warnings = []
            for pipeline in all_pipelines:
                conflict_result = check_pipeline_ocean_conflict(pipeline.coordinates)
                if conflict_result['has_conflict']:
                    ocean_warnings.append({
                        'pipeline_id': pipeline.pipeline_id,
                        'conflict_points': len(conflict_result['conflict_points']),
                        'ocean_ratio': conflict_result['ocean_length_ratio'],
                        'message': conflict_result['warning_message']
                    })
            
            # 如果有海洋冲突，显示警告
            if ocean_warnings:
                warning_msg = "检测到以下管线与海洋区域冲突:\n\n"
                for w in ocean_warnings[:5]:  # 只显示前5个
                    warning_msg += f"• {w['pipeline_id']}: {w['conflict_points']}个点在海洋区域 ({w['ocean_ratio']:.1f}%)\n"
                
                if len(ocean_warnings) > 5:
                    warning_msg += f"... 还有 {len(ocean_warnings) - 5} 个管线存在冲突\n"
                
                warning_msg += "\n建议: 请调整管线路由，避免穿越海洋区域。"
                
                QMessageBox.warning(
                    self,
                    "海洋区域冲突警告",
                    warning_msg
                )
                self._log(f"⚠ 检测到 {len(ocean_warnings)} 条管线与海洋区域冲突")

            # ---- 用内存矢量图层渲染管线 ----
            # BUG4修复增强: 重构路径类型共存逻辑 — 每种路径有独立的管线图层和关联线图层
            # 获取当前路由类型
            current_route_type = "direct" if self.route_type_combo.currentIndex() == 0 else "manhattan"
            current_route_cn = "直连" if current_route_type == "direct" else "曼哈顿"
            other_route_cn = "曼哈顿" if current_route_type == "direct" else "直连"

            # BUG4修复: 先检测已存在的另一种路由类型图层（在删除前检测！）
            other_layer_name = f"通信管线-{other_route_cn}"
            other_connection_name = f"基站-管线关联-{other_route_cn}"
            other_layers_exist = len(QgsProject.instance().mapLayersByName(other_layer_name)) > 0

            # BUG4修复增强: 只删除当前路由类型的旧图层 + 当前路由类型的关联线
            # 关键修复: 每种路由类型有独立的关联线图层，不互相覆盖
            current_layer_name = f"通信管线-{current_route_cn}"
            current_connection_name = f"基站-管线关联-{current_route_cn}"
            layers_to_remove = [current_layer_name, current_connection_name]
            for rm_name in layers_to_remove:
                for old_layer in QgsProject.instance().mapLayersByName(rm_name):
                    QgsProject.instance().removeMapLayer(old_layer.id())

            # 创建当前路由类型的管线图层
            create_pipeline_layer(all_pipelines, current_layer_name)

            if other_layers_exist:
                self._log(f"双路径共存: 当前 {current_route_cn} 路径 + 已有 {other_route_cn} 路径（各有独立关联线）")
            else:
                self._log(f"创建 {current_route_cn} 管线图层: {len(all_pipelines)}条")

            # 创建当前路由类型的基站-管线关联线（独立图层，不覆盖其他路由类型）
            create_connection_layer(self.generated_sites, all_pipelines, current_connection_name)

            # 刷新地图
            canvas = self.iface.mapCanvas()
            canvas.refresh()

            # 更新统计
            self.pipeline_stats_label.setText(f"管线: {len(all_pipelines)}条")

            # 计算成本
            cost_summary = calculate_total_cost(all_pipelines)
            self.cost_stats_label.setText(f"总成本: {cost_summary['总成本(元)']:,.0f}元")

            self._log(f"管线生成完成: {len(all_pipelines)}条 ({pipeline_type.value})")
            self._show_progress(False)

        except Exception as e:
            self._log(f"管线生成失败: {e}")
            self._show_progress(False)
            QMessageBox.critical(self, "错误", f"管线生成失败: {e}")

    def _clear_pipeline_bands(self):
        """清除管线标记"""
        canvas = self.iface.mapCanvas()
        for rb in self._pipeline_bands:
            canvas.scene().removeItem(rb)
        self._pipeline_bands.clear()

    def _detect_simple_sharing(self, pipelines):
        """简化的共享检测 - 只检测起终点相同的管线"""
        # 按起终点分组
        route_groups = {}
        for p in pipelines:
            key = f"{p.start_site_id}->{p.end_site_id}"
            if key not in route_groups:
                route_groups[key] = []
            route_groups[key].append(p)

        # 标记共享
        shared_count = 0
        for key, group in route_groups.items():
            if len(group) > 1:
                # 这些管线共享同一路径
                ids = [p.pipeline_id for p in group]
                for p in group:
                    p.is_shared = True
                    p.shared_with = [pid for pid in ids if pid != p.pipeline_id]
                    shared_count += 1

        if shared_count > 0:
            self._log(f"检测到 {shared_count} 条共享管线")

    def _clear_pipelines(self):
        """清除管线 — 清除所有路由类型的管线和关联线图层"""
        # 清除所有管线图层（直连、曼哈顿）和对应的关联线图层
        for layer_name in ["通信管线-直连", "通信管线-曼哈顿", "基站-管线关联-直连", "基站-管线关联-曼哈顿"]:
            for layer in QgsProject.instance().mapLayersByName(layer_name):
                QgsProject.instance().removeMapLayer(layer.id())

        # 清除 RubberBand 残留（旧版本管线）
        self._clear_pipeline_bands()

        # 清除数据
        self.generated_pipelines.clear()

        # 更新统计
        self.pipeline_stats_label.setText("管线: 0条, 总长度: 0m")
        self.cost_stats_label.setText("总成本: 0元")
        self.iface.mapCanvas().refresh()
        self._log("已清除所有管线")

    # =================================================================
    #  第六步：分析与导出
    # =================================================================

    @require_sites("请先生成基站")
    @safe_execute(show_errors=True)
    def _generate_heatmap(self):
        """生成GDAL栅格覆盖热力图 — P0修复: 使用连续渐变栅格替代点状热力图"""
        self._log("正在生成GDAL栅格覆盖热力图...")
        self._show_progress(True, 0)

        band_key = self.band_combo.currentText()
        config = BAND_CONFIGS[band_key]
        tower_height = self.height_spin.value()
        radius_km = config.ideal_isr_km * 1.5
        scenario = self.scenario_combo.currentText().split("(")[1].rstrip(")")

        # 环境类型：直接使用英文代码
        environment = scenario  # URBAN/SUBURBAN/RURAL 已从组合框解析

        self._log(f"频段: {band_key}, 半径: {radius_km:.1f}km, 基站数: {len(self.generated_sites)}")

        # 使用 GDAL raster 热力图替代点状渲染
        rsrp_grid, transform = generate_raster_heatmap_data(
            sites=self.generated_sites,
            frequency_mhz=config.frequency_mhz,
            tx_power_w=config.default_power_w,
            antenna_gain_dbi=config.default_gain_dbi,
            resolution_m=50,
            radius_km=radius_km,
            environment=environment,
        )

        if rsrp_grid.size == 0:
            QMessageBox.warning(self, "提示",
                f"覆盖数据为空！\n\n"
                f"可能原因：\n"
                f"- 基站功率太低\n"
                f"- 覆盖半径 {radius_km:.1f}km 太小\n"
                f"- 频率 {config.frequency_mhz}MHz 衰减过快\n"
                f"\n尝试降低频率或增大塔高。")
            self._log("覆盖数据为空，请调整参数")
            self._show_progress(False)
            return

        self._show_progress(True, 80)
        self._create_raster_heatmap_layer(rsrp_grid, transform)
        self._log(f"GDAL热力图已生成: {rsrp_grid.shape[0]}x{rsrp_grid.shape[1]} 栅格, {len(self.generated_sites)}个基站叠加")

        self._show_progress(False)

    def _create_raster_heatmap_layer(self, rsrp_grid, transform):
        """创建GDAL栅格热力图图层 — P0修复: GeoTIFF连续渐变渲染替代点状符号"""
        import tempfile
        import os
        from qgis.core import (
            QgsRasterLayer, QgsProject,
            QgsSingleBandPseudoColorRenderer, QgsColorRampShader,
            QgsStyle, QgsRasterShader,
        )
        from qgis.PyQt.QtGui import QColor
        import numpy as np

        layer_name = "覆盖热力图"

        # 移除旧图层
        layers = QgsProject.instance().mapLayersByName(layer_name)
        for old in layers:
            QgsProject.instance().removeMapLayer(old)

        # 导出 GeoTIFF 到临时文件（用完立即清理）
        import tempfile
        tmpdir = tempfile.gettempdir()
        tiff_path = os.path.join(tmpdir, f"qgis_heatmap_{id(self)}.tif")
        self._temp_tiff = tiff_path  # 记录以便后续清理

        success = export_heatmap_as_geotiff(
            rsrp_grid=rsrp_grid,
            transform=transform,
            output_path=tiff_path,
            crs_epsg=4326,
        )

        if not success:
            # GDAL 不可用时回退到点状渲染
            self._log("GDAL不可用，回退到原始热力图渲染")
            return

        # 添加栅格图层
        raster_layer = QgsRasterLayer(tiff_path, layer_name)
        if not raster_layer.isValid():
            self._log("栅格图层加载失败")
            os.remove(tiff_path)
            return

        # 配置伪彩色渲染（专业热力图配色: 蓝→青→绿→黄→红）
        color_ramp = [
            (-120, QColor(0, 0, 150, 180)),      # 很弱: 深蓝
            (-100, QColor(0, 100, 255, 200)),     # 较弱: 蓝
            (-90, QColor(0, 200, 100, 220)),      # 良好: 绿
            (-80, QColor(255, 200, 0, 230)),      # 强: 黄
            (-65, QColor(255, 50, 0, 240)),       # 极强: 红
            (-50, QColor(180, 0, 0, 240)),        # 最强: 深红
        ]

        color_ramp_items = []
        for value, color in color_ramp:
            item = QgsColorRampShader.ColorRampItem(value, color, f"{value} dBm")
            color_ramp_items.append(item)

        shader_func = QgsColorRampShader()
        shader_func.setColorRampType(QgsColorRampShader.Interpolated)
        shader_func.setColorRampItemList(color_ramp_items)
        shader_func.setClassificationMode(QgsColorRampShader.Continuous)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(shader_func)

        renderer = QgsSingleBandPseudoColorRenderer(
            raster_layer.dataProvider(), 1, raster_shader
        )
        renderer.setOpacity(0.75)

        raster_layer.setRenderer(renderer)
        raster_layer.setOpacity(0.75)

        # 插入到图层树顶层
        QgsProject.instance().addMapLayer(raster_layer, False)
        QgsProject.instance().layerTreeRoot().insertLayer(0, raster_layer)

        raster_layer.setVisible(True)
        raster_layer.triggerRepaint()

        # 缩放到热力图范围
        canvas = self.iface.mapCanvas()
        ext = raster_layer.extent()
        if not ext.isEmpty():
            canvas.setExtent(ext)
            canvas.refreshAllLayers()
            canvas.refresh()

        # 计算覆盖统计 (基于 numpy 数组)
        valid_mask = rsrp_grid > -900
        valid_rsrp = rsrp_grid[valid_mask]
        if len(valid_rsrp) > 0:
            excellent = int(np.sum(valid_rsrp >= -65))
            good = int(np.sum((valid_rsrp >= -80) & (valid_rsrp < -65)))
            fair = int(np.sum((valid_rsrp >= -90) & (valid_rsrp < -80)))
            poor = int(np.sum((valid_rsrp >= -100) & (valid_rsrp < -90)))
            very_poor = int(np.sum(valid_rsrp < -100))
            total_points = len(valid_rsrp)
            avg_rsrp = round(float(np.mean(valid_rsrp)), 1)
            coverage_rate = round((excellent + good) / total_points * 100, 1) if total_points > 0 else 0
        else:
            excellent = good = fair = poor = very_poor = 0
            total_points = avg_rsrp = coverage_rate = 0

        # 清理临时文件
        try:
            os.remove(tiff_path)
        except OSError:
            self._log("清理临时GeoTIFF文件失败", "DEBUG")

        self._show_coverage_stats(
            total_sites=len(self.generated_sites),
            total_points=total_points,
            avg_rsrp=avg_rsrp,
            coverage_rate=coverage_rate,
            excellent=excellent, good=good, fair=fair, poor=poor, very_poor=very_poor,
        )

        self._log(f"热力图已生成: {total_points}个点, {len(self.generated_sites)}个基站叠加")

    def _show_coverage_stats(self, total_sites, total_points, avg_rsrp,
                             coverage_rate, excellent, good, fair, poor, very_poor):
        """显示覆盖统计对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("覆盖分析报告")
        dialog.setMinimumSize(420, 400)
        dialog.setStyleSheet("""
            QDialog { background: #fafafa; }
            QGroupBox { font-weight: bold; border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

        layout = QVBoxLayout(dialog)

        # 总览
        overview = QGroupBox("总览")
        form = QFormLayout()
        form.addRow("基站数量:", f"{total_sites} 个")
        form.addRow("有效覆盖点:", f"{total_points:,} 个")
        form.addRow("平均 RSRP:", f"{avg_rsrp} dBm")
        form.addRow("覆盖率(≥-80dBm):", f"<b>{coverage_rate:.1f}%</b>")
        overview.setLayout(form)
        layout.addWidget(overview)

        # 分级统计
        grade = QGroupBox("覆盖分级")
        grade_form = QFormLayout()
        grade_form.addRow("<span style='color:#ff0000'>●</span> 很强(≥-65dBm):", f"<b>{excellent}</b> 点")
        grade_form.addRow("<span style='color:#00ff00'>●</span> 良好(-80~-65dBm):", f"<b>{good}</b> 点")
        grade_form.addRow("<span style='color:#ffff00'>●</span> 一般(-90~-80dBm):", f"<b>{fair}</b> 点")
        grade_form.addRow("<span style='color:#ff8c00'>●</span> 较差(-100~-90dBm):", f"<b>{poor}</b> 点")
        grade_form.addRow("<span style='color:#1a1a7a'>●</span> 很差(<-100dBm):", f"<b>{very_poor}</b> 点")
        grade.setLayout(grade_form)
        layout.addWidget(grade)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("padding: 8px; background: #3498db; color: white; border-radius: 4px;")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def _export_report_txt(self):
        """导出工程量报表为TXT格式"""
        if not self.generated_pipelines:
            QMessageBox.warning(self, "导出", "没有管线数据，请先生成管线")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出工程量报表",
            f"管线工程量报表_{datetime.now().strftime('%Y%m%d')}.txt",
            "文本文件 (*.txt)")
        if not fpath:
            return

        try:
            report_text = generate_pipeline_report_text(self.generated_pipelines)

            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(report_text)

            QMessageBox.information(self, "导出成功",
                                    f"工程量报表已导出到:\n{fpath}")
            self._log("工程量报表已导出 (TXT)")

        except Exception as e:
            QMessageBox.critical(self, "导出错误", str(e))
            self._log(f"报表导出失败: {e}")

    def _export_report_csv(self):
        """导出工程量报表为CSV格式"""
        if not self.generated_pipelines:
            QMessageBox.warning(self, "导出", "没有管线数据，请先生成管线")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出工程量报表",
            f"管线工程量报表_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV文件 (*.csv)")
        if not fpath:
            return

        try:
            success = export_pipeline_report_csv(self.generated_pipelines, fpath)

            if success:
                QMessageBox.information(self, "导出成功",
                                        f"工程量报表已导出到:\n{fpath}\n\n"
                                        f"包含4个文件:\n"
                                        f"- 明细表\n"
                                        f"- 工程量表\n"
                                        f"- 成本表\n"
                                        f"- 汇总表")
                self._log("工程量报表已导出 (CSV)")
            else:
                QMessageBox.warning(self, "导出失败", "CSV导出失败，请检查文件路径")

        except Exception as e:
            QMessageBox.critical(self, "导出错误", str(e))
            self._log(f"报表导出失败: {e}")

    def _export_pdf(self):
        """导出标准图纸（PDF/PNG）- 修复: 包含框选区域边界、仅导出框选区域内的站点"""
        if not self.generated_sites:
            QMessageBox.warning(self, "导出", "没有站点数据")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出标准图纸", "基站设计方案.pdf",
            "PDF (*.pdf);;PNG (*.png);;DXF (*.dxf);;DWG (*.dwg)")
        if not fpath:
            return

        # 临时图层引用，用于导出后清理
        temp_extent_layer = None

        try:
            canvas = self.iface.mapCanvas()
            
            # 获取用户框选范围或当前视图范围
            if self.selected_extent:
                if isinstance(self.selected_extent, QgsRectangle):
                    export_extent = self.selected_extent
                    extent_coords = [
                        (export_extent.xMinimum(), export_extent.yMinimum()),
                        (export_extent.xMaximum(), export_extent.yMinimum()),
                        (export_extent.xMaximum(), export_extent.yMaximum()),
                        (export_extent.xMinimum(), export_extent.yMaximum()),
                    ]
                else:
                    lon_min, lat_min, lon_max, lat_max = self.selected_extent
                    export_extent = QgsRectangle(lon_min, lat_min, lon_max, lat_max)
                    extent_coords = [
                        (lon_min, lat_min), (lon_max, lat_min),
                        (lon_max, lat_max), (lon_min, lat_max),
                    ]
                
                # 修复: 创建临时框选区域边界图层（RubberBand是画布覆盖层，Layout不会渲染）
                extent_layer_name = "_框选区域边界(临时)"
                # 先清除旧的临时图层
                for old in QgsProject.instance().mapLayersByName(extent_layer_name):
                    QgsProject.instance().removeMapLayer(old.id())
                
                temp_extent_layer = QgsVectorLayer(
                    "Polygon?crs=EPSG:4326", extent_layer_name, "memory"
                )
                provider = temp_extent_layer.dataProvider()
                # 闭合多边形
                wkt_coords = ", ".join([f"{lon} {lat}" for lon, lat in extent_coords])
                wkt_coords += f", {extent_coords[0][0]} {extent_coords[0][1]}"  # 闭合
                poly_geom = QgsGeometry.fromWkt(f"POLYGON(({wkt_coords}))")
                feat = QgsFeature()
                feat.setGeometry(poly_geom)
                provider.addFeatures([feat])
                temp_extent_layer.updateExtents()
                
                # 设置红色虚线边框 + 透明填充
                extent_symbol = QgsFillSymbol.createSimple({
                    'color': '255,0,0,30',       # 半透明红色填充
                    'outline_color': '255,0,0',   # 红色边框
                    'outline_width': '1.5',
                    'outline_style': 'dash',
                })
                temp_extent_layer.setRenderer(QgsSingleSymbolRenderer(extent_symbol))
                QgsProject.instance().addMapLayer(temp_extent_layer)
            else:
                export_extent = canvas.extent()
                extent_coords = None
            
            # 筛选在框选范围内的站点
            sites_to_export = []
            for site in self.generated_sites:
                site_point = QgsPointXY(site['longitude'], site['latitude'])
                if export_extent.contains(site_point):
                    sites_to_export.append(site)
            
            if not sites_to_export:
                QMessageBox.warning(
                    self, 
                    "导出失败", 
                    f"框选范围内没有找到站点！\n\n"
                    f"当前范围: {export_extent.xMinimum():.4f}, {export_extent.yMinimum():.4f} 至\n"
                    f"        {export_extent.xMaximum():.4f}, {export_extent.yMaximum():.4f}\n\n"
                    f"请调整选择范围或取消选择以导出所有站点。"
                )
                # 清理临时图层
                if temp_extent_layer:
                    QgsProject.instance().removeMapLayer(temp_extent_layer.id())
                return
            
            self._log(f"导出筛选后的 {len(sites_to_export)}/{len(self.generated_sites)} 个站点")

            # ============================================================
            #  T7: DXF / DWG 导出（CAD 标准格式）
            # ============================================================
            lower_path = fpath.lower()
            if lower_path.endswith(".dxf") or lower_path.endswith(".dwg"):
                cad_fmt = "dwg" if lower_path.endswith(".dwg") else "dxf"
                res = export_design_to_cad(
                    sites=sites_to_export,
                    pipelines=getattr(self, "generated_pipelines", []),
                    rooms=getattr(self, "machine_rooms", []),
                    path=fpath,
                    fmt=cad_fmt,
                )
                # 清理临时框选图层
                if temp_extent_layer:
                    try:
                        QgsProject.instance().removeMapLayer(temp_extent_layer.id())
                    except Exception:
                        pass
                if res.get("dwg_created"):
                    QMessageBox.information(
                        self, "导出成功",
                        f"已导出 DWG:\n{res['dwg_path']}\n\n{res['note']}"
                    )
                else:
                    QMessageBox.information(
                        self, "导出成功",
                        f"已导出 CAD 图纸:\n{res['dxf_path']}\n\n{res['note']}"
                    )
                self._log(f"CAD 图纸已导出: {res['dxf_path']}")
                return

            paper_size = "A3" if fpath.endswith(".pdf") else "A4"
            export_fmt = "PDF" if fpath.endswith(".pdf") else "PNG"

            # 修复: 确保所有图层在导出前可见（包括新的关联线图层名）
            visible_layers = []
            for name in ["基站设计", "通信管线-直连", "通信管线-曼哈顿",
                         "基站-管线关联-直连", "基站-管线关联-曼哈顿",
                         "覆盖热力图", "_框选区域边界(临时)"]:
                layers = QgsProject.instance().mapLayersByName(name)
                for layer in layers:
                    layer.setVisible(True)
                    visible_layers.append(layer.id())

            scheme_params = {
                'frequency_band': getattr(self, '_current_band', '3.5GHz'),
                'scenario': getattr(self, '_current_scenario', 'URBAN'),
                'tower_height': float(self.height_spin.value()) if hasattr(self, 'height_spin') else 35,
                'band': getattr(self, '_current_band', '3.5GHz'),
            }
            result = create_standard_design_drawing(
                project=QgsProject.instance(),
                sites=sites_to_export,  # 使用筛选后的站点
                map_extent=export_extent,
                title="通信基站设计方案",
                output_path=fpath,
                paper_size=paper_size,
                export_format=export_fmt,
                scheme_params=scheme_params,
            )
            
            # 清理临时框选图层
            if temp_extent_layer:
                QgsProject.instance().removeMapLayer(temp_extent_layer.id())
            
            # 恢复图层可见性状态
            for layer_id in visible_layers:
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer:
                    layer.setVisible(True)
            
            if result:
                QMessageBox.information(
                    self, 
                    "导出成功", 
                    f"已导出到:\n{result}\n\n"
                    f"站点数量: {len(sites_to_export)}/{len(self.generated_sites)}"
                )
                self._log(f"标准图纸已导出 ({len(sites_to_export)}个站点)")
            else:
                QMessageBox.warning(self, "导出失败", "导出失败，请检查QGIS Print Layout支持")
        except Exception as e:
            # 确保异常时也清理临时图层
            if temp_extent_layer:
                try:
                    QgsProject.instance().removeMapLayer(temp_extent_layer.id())
                except Exception:
                    self._log(f"清理临时图层失败: {e}", "WARN")
            QMessageBox.critical(self, "导出错误", str(e))

    def _export_bom(self):
        """导出BOM物料清单"""
        if not self.generated_sites:
            QMessageBox.warning(self, "导出BOM", "没有站点数据，请先生成基站方案")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出BOM物料清单",
            f"BOM_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV (*.csv)")
        if not fpath:
            return

        try:
            report = BOMExtractor.extract(
                sites=self.generated_sites,
                pipelines=self.generated_pipelines,
                machine_rooms=getattr(self, 'machine_rooms', []),
                project_name="通信基建工程设计",
                scheme_name=f"基站方案_{datetime.now().strftime('%Y%m%d')}",
            )

            if report.to_csv(fpath):
                QMessageBox.information(
                    self, "BOM导出成功",
                    f"BOM清单已导出：\n{fpath}\n\n"
                    f"总物料项：{len(report.items)}\n"
                    f"总预算：¥{report.total_cost:,.2f}"
                )
                self._log(f"BOM导出成功：{len(report.items)} 项，¥{report.total_cost:,.2f}")
            else:
                QMessageBox.critical(self, "BOM导出失败", "CSV 文件写入失败")
        except Exception as e:
            QMessageBox.critical(self, "BOM导出错误", str(e))

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

        params = {
            "scheme_name": f"基站设计_{datetime.now().strftime('%Y%m%d')}",
            "band": self.band_combo.currentText(),
            "tower_height": self.height_spin.value(),
        }

        success, msg = self.sync_engine.upload_design(
            project_id=project_id,
            sites=self.generated_sites,
            params=params,
        )
        if success:
            QMessageBox.information(self, "同步成功", f"方案ID: {msg}")
        else:
            QMessageBox.warning(self, "同步失败", msg)

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

        # 只在有有效extent时缩放，保持当前视图不变
        if layer.extent().isNull() or layer.extent().isEmpty():
            return
        # 不再自动缩放，保持用户当前视图

    # =================================================================
    #  站点管理
    # =================================================================

    def _update_site_table(self):
        """更新站点表格 — 12列专业字段"""
        sites = self.generated_sites
        self.site_table.setRowCount(len(sites))

        type_map = {'MACRO': '宏站', 'SMALL': '微站', 'INDOOR': '室分'}
        scenario_map = {'URBAN': '城市', 'SUBURBAN': '郊区', 'RURAL': '农村'}

        # 从当前频段配置获取站间距
        band_key = self.band_combo.currentText() if hasattr(self, 'band_combo') else "3.5GHz"
        isr_km = BAND_CONFIGS.get(band_key, BAND_CONFIGS["3.5GHz"]).ideal_isr_km

        for i, s in enumerate(sites):
            def item(text):
                return QTableWidgetItem(str(text))

            st = s.get('site_type', '')
            site_type_cn = type_map.get(st, st)
            scenario_cn = scenario_map.get(s.get('scenario', ''), s.get('scenario', ''))
            tower_h = s.get('tower_height', '')
            band = s.get('band', band_key)
            freq = s.get('frequency', '')
            power = s.get('power', '')

            # 方位角
            ns = s.get('num_sectors', 3)
            if ns == 0:
                az_str = '全向'
            elif ns > 0:
                az_str = '/'.join(str(int(360 / ns * j)) for j in range(ns))
            else:
                az_str = str(s.get('azimuth', 0))

            # 覆盖半径 = 站间距 * 1.5
            cov_radius = round(isr_km * 1.5, 2)

            # 坐标
            lon = s.get('longitude', 0)
            lat = s.get('latitude', 0)
            coord_str = f"{lon:.5f},{lat:.5f}"

            self.site_table.setItem(i, 0, item(s.get('site_id', '')))
            self.site_table.setItem(i, 1, item(s.get('name', '')))
            self.site_table.setItem(i, 2, item(site_type_cn))
            self.site_table.setItem(i, 3, item(scenario_cn))
            self.site_table.setItem(i, 4, item(tower_h))
            self.site_table.setItem(i, 5, item(band))
            self.site_table.setItem(i, 6, item(freq))
            self.site_table.setItem(i, 7, item(power))
            self.site_table.setItem(i, 8, item(az_str))
            self.site_table.setItem(i, 9, item(cov_radius))
            self.site_table.setItem(i, 10, item(isr_km))
            self.site_table.setItem(i, 11, item(coord_str))

        self.stats_label.setText(f"站点: {len(sites)}")

    def _filter_site_table(self, text):
        """搜索过滤站点表格 — 隐藏不匹配的行"""
        text_lower = text.strip().lower()
        for row in range(self.site_table.rowCount()):
            match = False
            if not text_lower:
                match = True
            else:
                # 检查所有列
                for col in range(self.site_table.columnCount()):
                    item = self.site_table.item(row, col)
                    if item and text_lower in item.text().lower():
                        match = True
                        break
            self.site_table.setRowHidden(row, not match)

    def _show_site_context_menu(self, pos):
        """右键菜单 — 定位、删除、复制坐标"""
        row = self.site_table.rowAt(pos.y())
        if row < 0 or row >= len(self.generated_sites):
            return

        self.site_table.selectRow(row)
        menu = QMenu(self)

        fly_action = menu.addAction("🔍 定位到站点")
        fly_action.triggered.connect(self._fly_to_site)

        menu.addSeparator()

        copy_id = menu.addAction("📋 复制站点ID")
        copy_coord = menu.addAction("📋 复制坐标")
        copy_all = menu.addAction("📋 复制全部信息")

        menu.addSeparator()

        delete_action = menu.addAction("🗑 删除站点")
        delete_action.setStyleSheet("color: #e74c3c;")

        # 连接信号
        site = self.generated_sites[row]
        copy_id.triggered.connect(
            lambda: QApplication.clipboard().setText(str(site.get('site_id', ''))))
        copy_coord.triggered.connect(
            lambda: QApplication.clipboard().setText(
                f"{site.get('longitude', 0):.6f}, {site.get('latitude', 0):.6f}"))
        copy_all.triggered.connect(
            lambda: QApplication.clipboard().setText(
                f"站点ID: {site.get('site_id', '')}\n"
                f"名称: {site.get('name', '')}\n"
                f"坐标: {site.get('longitude', 0):.6f}, {site.get('latitude', 0):.6f}\n"
                f"站型: {site.get('site_type', '')}\n"
                f"频段: {site.get('band', '')}\n"
                f"塔高: {site.get('tower_height', '')}m"))
        delete_action.triggered.connect(self._delete_site)

        menu.exec_(self.site_table.viewport().mapToGlobal(pos))

    def _validate_coords(self, lon, lat):
        """校验坐标是否在中国大陆范围内

        返回: (bool, str) — (是否有效, 错误消息)
        """
        if not (70.0 <= lon <= 140.0):
            return False, f"经度 {lon:.4f} 超出中国范围 (70-140)"
        if not (20.0 <= lat <= 50.0):
            return False, f"纬度 {lat:.4f} 超出中国范围 (20-50)"
        return True, ""

    def _fly_to_site(self):
        """定位到选中站点 - 修复: 放大并高亮显示，确保同步完成"""
        row = self.site_table.currentRow()
        if row < 0 or row >= len(self.generated_sites):
            QMessageBox.warning(self, "提示", "请先选择一个站点")
            return
        site = self.generated_sites[row]
        lon = site.get('longitude')
        lat = site.get('latitude')
        if lon is None or lat is None:
            QMessageBox.warning(self, "提示", "站点坐标缺失")
            return

        canvas = self.iface.mapCanvas()
        center = QgsPointXY(float(lon), float(lat))

        # BUG1修复: 先设置中心点（确保地图立即平移）
        canvas.setCenter(center)

        # BUG1修复: 使用 setExtent 进行精确缩放 (0.005度 ≈ 500米)
        zoom_extent = QgsRectangle(
            float(lon) - 0.005, float(lat) - 0.005,
            float(lon) + 0.005, float(lat) + 0.005
        )
        canvas.setExtent(zoom_extent)

        # BUG1修复: 先创建高亮，再统一刷新 — 避免两次 refresh 导致闪烁/高亮丢失
        self._highlight_site(row)

        # BUG1修复: 仅在全部操作完成后刷新一次
        canvas.refresh()

        self._log(f"已定位到站点: {site.get('name', site.get('site_id', ''))}")

    def _highlight_site(self, row):
        """高亮显示选中的站点 — BUG1修复: 不再独立调用 refresh，由 _fly_to_site 统一刷新"""
        if row < 0 or row >= len(self.generated_sites):
            return

        site = self.generated_sites[row]
        lon = site.get('longitude')
        lat = site.get('latitude')
        if lon is None or lat is None:
            return

        canvas = self.iface.mapCanvas()

        # 清除之前的高亮
        if hasattr(self, '_highlight_bands'):
            for old_rb in self._highlight_bands:
                try:
                    canvas.scene().removeItem(old_rb)
                except Exception:
                    self._log("清理高亮标记失败(可能已被自动清除)", "DEBUG")
            self._highlight_bands.clear()
        else:
            self._highlight_bands = []

        # 创建高亮标记 (黄色大圆 + 外圈闪烁效果)
        # 外层大圆 - 脉冲效果
        rb_outer = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_outer.setColor(QColor(255, 255, 0, 180))
        rb_outer.setFillColor(QColor(255, 255, 0, 40))
        rb_outer.setIconSize(30)
        rb_outer.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_outer.addPoint(QgsPointXY(float(lon), float(lat)))

        # 内层小圆 - 实心高亮
        rb_inner = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_inner.setColor(QColor(255, 200, 0))
        rb_inner.setFillColor(QColor(255, 200, 0, 120))
        rb_inner.setIconSize(14)
        rb_inner.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_inner.addPoint(QgsPointXY(float(lon), float(lat)))

        self._highlight_bands = [rb_outer, rb_inner]
        # BUG1修复: 不在此处调用 refresh，由 _fly_to_site 统一调用

    def _delete_site(self):
        """删除选中站点 - BUG2修复: 同步删除地图上所有关联图层的标记并强制重绘"""
        row = self.site_table.currentRow()
        if row < 0 or row >= len(self.generated_sites):
            QMessageBox.warning(self, "提示", "请先选择一个站点")
            return
        reply = QMessageBox.question(self, "确认",
                                     f"确定删除站点 '{self.generated_sites[row].get('name', '')}'？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 删除站点数据
        deleted_site = self.generated_sites.pop(row)
        site_id = deleted_site.get('site_id', '')

        # BUG2修复: 立即刷新站点表格
        self._update_site_table()

        # BUG2修复: 从所有关联图层中删除该站点
        affected_layers = []

        # 1. 从"基站设计"图层删除站点标记
        design_layers = QgsProject.instance().mapLayersByName("基站设计")
        for layer in design_layers:
            layer.startEditing()
            features_to_delete = []
            for feat in layer.getFeatures():
                if feat.attribute('site_id') == site_id:
                    features_to_delete.append(feat.id())
            if features_to_delete:
                layer.deleteFeatures(features_to_delete)
            layer.commitChanges()
            layer.updateExtents()
            layer.triggerRepaint()  # BUG2修复: 强制触发重绘
            affected_layers.append("基站设计")

        # 2. 从"覆盖热力图"图层删除该站点对应的热力点（按属性粗略匹配）
        heatmap_layers = QgsProject.instance().mapLayersByName("覆盖热力图")
        if heatmap_layers:
            # 热力图是全量叠加生成的，单站点删除无法精确定位 -> 提示用户重新生成
            pass

        # 3. 从管线图层删除该站点的管线
        for pipeline_layer_name in ["通信管线-直连", "通信管线-曼哈顿"]:
            pl_layers = QgsProject.instance().mapLayersByName(pipeline_layer_name)
            for pl_layer in pl_layers:
                pl_layer.startEditing()
                pipe_ids_to_delete = []
                for feat in pl_layer.getFeatures():
                    if feat.attribute('start_site_id') == site_id:
                        pipe_ids_to_delete.append(feat.id())
                if pipe_ids_to_delete:
                    pl_layer.deleteFeatures(pipe_ids_to_delete)
                pl_layer.commitChanges()
                pl_layer.updateExtents()
                pl_layer.triggerRepaint()
                affected_layers.append(pipeline_layer_name)

        # 4. 从关联线图层删除
        conn_layers = QgsProject.instance().mapLayersByName("基站-管线关联")
        for conn_layer in conn_layers:
            conn_layer.startEditing()
            conn_ids_to_delete = []
            for feat in conn_layer.getFeatures():
                if feat.attribute('site_id') == site_id:
                    conn_ids_to_delete.append(feat.id())
            if conn_ids_to_delete:
                conn_layer.deleteFeatures(conn_ids_to_delete)
            conn_layer.commitChanges()
            conn_layer.updateExtents()
            conn_layer.triggerRepaint()
            affected_layers.append("基站-管线关联")

        # BUG2修复: 统一刷新地图显示
        canvas = self.iface.mapCanvas()
        canvas.refreshAllLayers()  # 强制刷新所有图层
        canvas.refresh()

        self._log(f"已删除站点: {site_id} (同步清理 {len(affected_layers)} 个图层)")
        QMessageBox.information(self, "删除成功", f"站点 {site_id} 已删除，相关图层已同步更新")

    @require_extent("请先在第二步选择设计区域")
    @require_sites_count(1, "请先生成基站方案")
    @safe_execute(show_errors=True)
    def _show_band_comparison(self):
        """频段对比：在同一区域叠加显示不同频段的基站布局"""
        current_band = self.band_combo.currentText()
        compare_band = "700MHz" if current_band != "700MHz" else "3.5GHz"
        config_current = BAND_CONFIGS[current_band]
        config_compare = BAND_CONFIGS[compare_band]

        reply = QMessageBox.question(
            self, "频段对比",
            f"将在当前 {current_band} 方案基础上，叠加显示 {compare_band} 方案。\n\n"
            f"{current_band}: 站间距 {config_current.ideal_isr_km}km, 频率 {config_current.frequency_mhz}MHz\n"
            f"{compare_band}: 站间距 {config_compare.ideal_isr_km}km, 频率 {config_compare.frequency_mhz}MHz\n\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self._log(f"开始频段对比: {current_band} vs {compare_band}")
        self._show_progress(True, 0)

        bbox = self.selected_extent
        centers = generate_hex_grid(bbox, config_compare.ideal_isr_km)
        if len(centers) > 200:
            centers = centers[:200]

        from design_engine.hex_grid import generate_sites_from_grid
        engine_sites = generate_sites_from_grid(
            centers, config_compare,
            site_type=self.type_combo.currentText().split("(")[1].rstrip(")"),
            tower_height=float(self.height_spin.value()),
            num_sectors=self.sector_spin.value(),
            bbox=bbox,
        )

        compare_sites = []
        for es in engine_sites:
            compare_sites.append({
                'site_id': es.site_id, 'name': es.name,
                'longitude': round(es.longitude, 7),
                'latitude': round(es.latitude, 7),
                'tower_height': es.tower_height,
                'site_type': es.site_type,
                'band': compare_band,
                'frequency': config_compare.frequency_mhz,
                'power': config_compare.default_power_w,
                'gain': config_compare.default_gain_dbi,
            })

        self._log(f"{compare_band}: 生成 {len(compare_sites)} 个站点")
        self._add_comparison_markers(compare_sites, compare_band)

        # 弹出对比报告对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("频段对比报告")
        dialog.setMinimumSize(450, 300)
        dialog.setStyleSheet("""
            QDialog { background: #fafafa; }
            QGroupBox { font-weight: bold; border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

        layout = QVBoxLayout(dialog)
        overview = QGroupBox("对比总览")
        form = QFormLayout()
        form.addRow(f"{current_band} 站点数:", f"<b>{len(self.generated_sites)}</b> 个")
        form.addRow(f"{compare_band} 站点数:", f"<b>{len(compare_sites)}</b> 个")
        form.addRow("站间距差异:", f"{config_current.ideal_isr_km}km vs {config_compare.ideal_isr_km}km")
        form.addRow("频率差异:", f"{config_current.frequency_mhz}MHz vs {config_compare.frequency_mhz}MHz")
        overview.setLayout(form)
        layout.addWidget(overview)

        coverage = QGroupBox("覆盖能力对比")
        cov_form = QFormLayout()
        cov_form.addRow(f"{current_band} 覆盖半径:", f"{config_current.max_radius_km} km")
        cov_form.addRow(f"{compare_band} 覆盖半径:", f"{config_compare.max_radius_km} km")
        ratio = len(compare_sites) / len(self.generated_sites) * 100 if self.generated_sites else 0
        cov_form.addRow("站点数差异:", f"{compare_band} 比 {current_band} {'多' if ratio > 100 else '少'} {abs(ratio - 100):.0f}%")
        coverage.setLayout(cov_form)
        layout.addWidget(coverage)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("padding: 8px; background: #3498db; color: white; border-radius: 4px;")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec_()

        self._log("频段对比完成")
        self._show_progress(False)

    def _add_comparison_markers(self, sites, band_name):
        """在地图上叠加显示对比频段的站点标记"""
        canvas = self.iface.mapCanvas()
        color_map = {
            "700MHz": QColor(255, 165, 0),   # 橙色
            "3.5GHz": QColor(0, 191, 255),   # 天蓝色
        }
        color = color_map.get(band_name, QColor(128, 128, 128))

        for site in sites:
            lon = site['longitude']
            lat = site['latitude']

            # 外圈白色边框
            rb_outer = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
            rb_outer.setColor(QColor(255, 255, 255))
            rb_outer.setFillColor(QColor(255, 255, 255))
            rb_outer.setIconSize(12)
            rb_outer.setIcon(QgsRubberBand.ICON_CIRCLE)
            rb_outer.addPoint(QgsPointXY(lon, lat))

            # 内圈对比频段颜色
            rb_inner = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
            rb_inner.setColor(color)
            rb_inner.setFillColor(color)
            rb_inner.setIconSize(8)
            rb_inner.setIcon(QgsRubberBand.ICON_CIRCLE)
            rb_inner.addPoint(QgsPointXY(lon, lat))

            self._marker_bands.extend([rb_outer, rb_inner])

        canvas.refresh()
        self._log(f"{band_name}: 叠加显示 {len(sites)} 个站点")

    def _show_efficiency_comparison(self):
        """显示效率对比数据 — 不同频段的站点密度、覆盖面积、生成效率"""
        if not self.generated_sites:
            QMessageBox.warning(self, "提示", "请先生成基站方案")
            return

        band_stats = {}
        for site in self.generated_sites:
            band = site.get('band', '未知')
            if band not in band_stats:
                band_stats[band] = {
                    'count': 0, 'total_power': 0, 'total_gain': 0,
                    'frequencies': set()
                }
            band_stats[band]['count'] += 1
            band_stats[band]['total_power'] += site.get('power', 0)
            band_stats[band]['total_gain'] += site.get('gain', 0)
            band_stats[band]['frequencies'].add(site.get('frequency', 0))

        stats_lines = []
        stats_lines.append("频段效率对比报告")
        stats_lines.append("=" * 50)
        area_km2 = self._calc_area_km2()
        stats_lines.append(f"设计区域: {self.selected_extent}")
        stats_lines.append(f"区域面积: {area_km2:.2f} km²")
        stats_lines.append("")

        for band, stats in band_stats.items():
            config = BAND_CONFIGS.get(band, BAND_CONFIGS["3.5GHz"])
            density = stats['count'] / area_km2 if area_km2 > 0 else 0
            stats_lines.append(f"--- {band} ---")
            stats_lines.append(f"  站点数: {stats['count']}")
            stats_lines.append(f"  站密度: {density:.2f} 站/km²")
            stats_lines.append(f"  理想站间距: {config.ideal_isr_km} km")
            stats_lines.append(f"  覆盖半径: {config.max_radius_km} km")
            stats_lines.append(f"  频率: {config.frequency_mhz} MHz")
            stats_lines.append(f"  默认功率: {config.default_power_w} W")
            stats_lines.append("")

        QMessageBox.information(self, "效率对比", "\n".join(stats_lines))

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

    def _log(self, text, level="INFO"):
        """增强日志 — 带时间戳和级别

        级别: INFO, WARN, ERROR, SUCCESS
        """
        from datetime import datetime as dt
        ts = dt.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}][{level}] {text}")

    def _show_export_success(self, filepath, title="导出成功"):
        """导出成功提示 — 含"打开文件夹"按钮"""
        import sys
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(f"文件已保存到:\n{filepath}")

        open_btn = msg_box.addButton("打开文件夹", QMessageBox.ActionRole)
        msg_box.addButton("关闭", QMessageBox.RejectRole)
        msg_box.exec_()

        if msg_box.clickedButton() == open_btn:
            folder = os.path.dirname(os.path.abspath(filepath))
            try:
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["xdg-open", folder])
            except Exception as e:
                self._log(f"无法打开文件夹: {e}", "ERROR")

    def _add_heatmap_legend(self):
        """为热力图图层添加图例 — 颜色 → RSRP 映射"""
        from qgis.core import (
            QgsLayerTree, QgsLayoutItemLabel, QgsLayoutItemLegend,
            QgsLayout, QgsLayoutItemShape, QgsTextFormat,
        )
        from qgis.PyQt.QtGui import QColor, QFont

        # 检查是否已存在图例层
        legend_name = "RSRP覆盖图例"
        existing = QgsProject.instance().mapLayersByName(legend_name)
        if existing:
            return  # 已存在，不重复添加

        self._log("添加热力图图例", "INFO")

        # 创建图例的注释图层（使用 QgsLayout 专业图例不支持简单叠加，
        # 这里用内存多边形 + 标签方式在画布上绘制图例条）
        from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsProject
        from qgis.PyQt.QtCore import QVariant
        from qgis.PyQt.QtGui import QColor

        # 色带定义（与 _create_raster_heatmap_layer 保持一致）
        legend_colors = [
            (-120, QColor(0, 0, 150, 180), "很弱 < -110 dBm"),
            (-100, QColor(0, 100, 255, 200), "较弱 -110 ~ -95"),
            (-90, QColor(0, 200, 100, 220), "良好 -95 ~ -85"),
            (-80, QColor(255, 200, 0, 230), "强 -85 ~ -72"),
            (-65, QColor(255, 50, 0, 240), "极强 -72 ~ -57"),
            (-50, QColor(180, 0, 0, 240), "最强 > -57"),
        ]

        # 图例位置：画布右下角 (用屏幕坐标估算地理范围)
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        bar_x = extent.xMaximum() - (extent.width() * 0.18)
        bar_y = extent.yMinimum() + (extent.height() * 0.06)
        bar_h = extent.height() * 0.028
        bar_w = extent.width() * 0.14
        segment_w = bar_w / len(legend_colors)

        self.legend_annotations = []
        for i, (dbm, color, label) in enumerate(legend_colors):
            seg_x = bar_x + i * segment_w
            rect_geom = QgsGeometry.fromRect(
                QgsRectangle(seg_x, bar_y, seg_x + segment_w, bar_y + bar_h)
            )
            item = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
            item.setColor(color)
            item.setWidth(1)
            item.setToGeometry(rect_geom, None)
            self.legend_annotations.append(item)

        # 标题组落在第一个色块上方
        from qgis.core import QgsTextAnnotationItem
        from qgis.PyQt.QtCore import QSizeF
        from qgis.PyQt.QtGui import QTextDocument
        from qgis.core import QgsPointXY as QgsPt

        title_item = QgsTextAnnotationItem(canvas)
        title_item.setMapPosition(QgsPt(bar_x, bar_y + bar_h * 1.3))
        title_item.setFrameSize(QSizeF(bar_w, bar_h))
        title_item.setDocument(
            QTextDocument(
                f"<span style='color:#0f0;font-size:9px;font-weight:bold;'>RSRP 覆盖强度</span>"
            )
        )
        self.legend_annotations.append(title_item)

        self._log(f"图例已添加到画布 ({len(legend_colors)} 色阶)", "SUCCESS")

    def _cleanup_legend(self):
        """移除画布上的图例注解"""
        if not hasattr(self, 'legend_annotations'):
            return
        canvas = self.iface.mapCanvas()
        for item in self.legend_annotations:
            if hasattr(item, 'hide'):
                item.hide()
            canvas.scene().removeItem(item)
        self.legend_annotations = []
        self._log("图例已清除")

    def closeEvent(self, event):
        """面板关闭时清理资源"""
        # 清理热力图临时 GeoTIFF
        if hasattr(self, '_temp_tiff') and os.path.exists(self._temp_tiff):
            try:
                os.remove(self._temp_tiff)
            except Exception:
                self._log("清理临时文件失败(closeEvent)", "DEBUG")
        # 清理画布注解
        self._cleanup_legend()
        # 保存当前配置
        try:
            from config import save_current_config
            save_current_config(self)
        except ImportError:
            self._log("无法导入config模块，跳过配置保存", "DEBUG")
        super().closeEvent(event)

    def _show_progress(self, show, value=0):
        """显示/隐藏进度条（含取消按钮联动）

        参数:
            show: True=显示, False=隐藏
            value: 进度值 (0-100)

        返回:
            bool: False 表示用户已点击取消（调用方应立即 return）
        """
        self.progress.setVisible(show)
        self.cancel_btn.setVisible(show)
        if show:
            self.progress.setValue(value)
        # 减少 processEvents 调用，避免闪回
        if value % 20 == 0 or value >= 95:
            QApplication.processEvents()
        return not self._cancel_requested

    def _check_cancelled(self):
        """检查是否已取消，若已取消则抛出 InterruptedError"""
        if self._cancel_requested:
            raise InterruptedError("用户取消了操作")

    def _cancel_progress(self):
        """取消按钮回调"""
        self._cancel_requested = True
        self._log("⚠ 用户请求取消操作...")
        self.status_label.setText("正在取消...")
        # 禁用取消按钮防止重复点击
        self.cancel_btn.setEnabled(False)
