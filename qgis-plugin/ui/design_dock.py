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
from typing import List, Optional, Dict

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QFileDialog, QMessageBox, QApplication,
    QTextEdit, QInputDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox,
    QDialog,
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
    generate_shared_pipelines, calculate_shared_engineering_volume,
    calculate_pipeline_cost, calculate_total_cost, calculate_total_cost_with_price,
    generate_pipeline_report_text, export_pipeline_report_csv,
    generate_direct_route, generate_manhattan_route,
    Pipeline, PipelineType, PipelineConfig
)
from layers.pipeline_layer import (
    create_pipeline_layer, create_connection_layer,
    get_pipeline_info, export_pipelines_to_geojson
)
from ui.basemap import add_gaode_satellite, add_osm
from tools.station_tool import AddStationTool
from ui.station_dialog import StationDialog
from tools.room_tool import AddRoomTool
from tools.extent_tool import ExtentSelectTool
from ui.room_dialog import RoomDialog
from models.machine_room import MachineRoom
from design_engine.layout_export import (
    create_design_layout, add_map_to_layout, add_title_to_layout,
    add_info_box_to_layout, add_legend_to_layout, add_scale_bar_to_layout,
    add_north_arrow_to_layout, export_layout_to_pdf,
    create_standard_design_drawing,
)
from design_engine.data_sync import DataSync


# ==================== 统一视觉样式 ====================
# 语义化按钮配色：(常规背景, 悬停背景)
_PALETTE = {
    "primary": ("#2f6df6", "#1d4fd0"),   # 主操作 · 蓝
    "accent":  ("#7c4dff", "#6234d6"),   # 强调 · 紫
    "success": ("#16a34a", "#11853b"),   # 成功 · 绿
    "danger":  ("#dc2626", "#b51c1c"),   # 危险/删除 · 红
    "warn":    ("#ea580c", "#c2410c"),   # 生成/导出 · 橙
    "teal":    ("#0d9488", "#0b7a70"),   # 同步 · 青
    "default": ("#475569", "#334155"),   # 次级 · 灰
    "group_style": "QGroupBox{font-size:12px;font-weight:bold;color:#e2e8f0;border:1px solid #334155;border-radius:8px;margin-top:10px;padding-top:8px;}QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 4px;}",
}


def btn_qss(kind="default", *, checkable=False):
    """生成语义化按钮样式表（主操作/强调/危险/成功/警告/同步/次级）。"""
    bg, hover = _PALETTE.get(kind, _PALETTE["default"])
    checked = "QPushButton:checked{background-color:%s;}" % hover if checkable else ""
    return (
        "QPushButton{background-color:%s;color:#ffffff;border:none;border-radius:6px;"
        "padding:9px 12px;font-size:12px;font-weight:600;}"
        "QPushButton:hover{background-color:%s;}"
        "QPushButton:disabled{background-color:#334155;color:#94a3b8;}" % (bg, hover)
        + checked
    )


GLOBAL_STYLE = """
QWidget{font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;}
QLabel{color:#1e293b;}
QGroupBox{font-weight:700;color:#0f172a;border:1px solid #e2e8f0;border-radius:8px;
  margin-top:12px;padding-top:8px;}
QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 4px;}
QComboBox,QSpinBox,QDoubleSpinBox{border:1px solid #cbd5e1;border-radius:6px;
  padding:5px 8px;background:#ffffff;min-height:22px;}
QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus{border-color:#2f6df6;}
QTableWidget{border:1px solid #e2e8f0;border-radius:8px;gridline-color:#eef2f7;}
QHeaderView::section{background:#f1f5f9;color:#334155;font-weight:600;border:none;padding:5px;}
QTextEdit{border:1px solid #e2e8f0;border-radius:6px;}
QProgressBar{border:1px solid #e2e8f0;border-radius:6px;text-align:center;
  background:#eef2f7;color:#0f172a;}
QProgressBar::chunk{background:#2f6df6;border-radius:5px;}
"""


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

        # 导出视图范围（独立于设计区域，用于“框选导出区域”）
        self.export_view_extent = None
        self._export_extent_tool = None
        self._export_extent_bands = []
        self._avoidance_features = []

        # 管线设计相关
        self.generated_pipelines = []
        self.machine_rooms: list = []
        self.room_counter = 0
        self._room_markers: dict = {}  # room_id -> [rb_outer, rb_inner]
        self._pipeline_bands = []  # 管线标记

        # 数据同步（URL 与 API Key 从环境变量 M03_API_URL / M03_API_KEY 读取，支持 HTTPS 与内部鉴权）
        self.sync_engine = DataSync(
            api_url=os.environ.get("M03_API_URL"),
            api_key=os.environ.get("M03_API_KEY"),
        )

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
        main.setStyleSheet(GLOBAL_STYLE)

        # 左侧菜单栏 —— 步骤指示器（高对比度：每步都是独立卡片）
        left_panel = QWidget()
        left_panel.setFixedWidth(124)
        left_panel.setStyleSheet(
            "background-color:#0f172a;"
            # 未选中步骤：浅灰卡片底 + 纯白粗体高亮文字
            "QPushButton{"
            "  color:#ffffff;text-align:left;font-size:13px;border:none;"
            "  padding:10px 12px;border-radius:6px;"
            "  background-color:#1e293b;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover{"
            "  background-color:#334155;color:#ffffff;"
            "}"
            # 选中步骤：亮蓝底 + 白字 + 加粗
            "QPushButton:checked{"
            "  background-color:#3b82f6;color:#ffffff;font-weight:700;"
            "}"
        )
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(6)
        left_layout.setContentsMargins(8, 12, 8, 12)

        # 标题 + 进度条
        title = QLabel("通信设施\n智能设计")
        title.setStyleSheet("color:#ffffff;font-size:13px;font-weight:800;padding:2px 6px;line-height:1.35;")
        left_layout.addWidget(title)

        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 6)
        self.step_progress.setValue(1)
        self.step_progress.setTextVisible(False)
        self.step_progress.setFixedHeight(4)
        self.step_progress.setStyleSheet(
            "QProgressBar{background:#1e293b;border:none;border-radius:3px;}"
            "QProgressBar::chunk{background:#2f6df6;border-radius:3px;}"
        )
        left_layout.addWidget(self.step_progress)

        # 步骤按钮
        self.step_buttons = []
        steps = ["底图", "区域", "参数", "基站", "管线", "导出"]
        for i, step_name in enumerate(steps):
            btn = QPushButton(f"{i+1}  {step_name}")
            btn.setCheckable(True)
            # 强制直接设置按钮样式（不依赖父级级联，覆盖 QGIS 全局主题）
            btn.setStyleSheet(
                "QPushButton{"
                "  color:#ffffff;font-size:13px;font-weight:600;"
                "  border:none;padding:10px 12px;border-radius:6px;"
                "  background-color:#1e293b;"
                "}"
                "QPushButton:hover{background-color:#334155;color:#ffffff;}"
                "QPushButton:checked{background-color:#3b82f6;color:#ffffff;font-weight:700;}"
            )
            btn.clicked.connect(lambda checked, idx=i: self._switch_step(idx))
            left_layout.addWidget(btn)
            self.step_buttons.append(btn)

        left_layout.addStretch()

        # 日志区域
        log_label = QLabel("运行日志")
        log_label.setStyleSheet("color:#94a3b8;font-size:10px;padding-left:6px;")
        left_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(160)
        self.log_text.setMaximumHeight(260)
        self.log_text.setStyleSheet(
            "background-color:#1e293b;color:#cbd5e1;font-size:10px;border-radius:6px;"
        )
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
        self.step_progress.setValue(step_index + 1)

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
        btn_gaode.setStyleSheet(btn_qss("success"))
        btn_gaode.clicked.connect(self._add_gaode_basemap)
        btn_row.addWidget(btn_gaode)

        btn_osm = QPushButton("OSM地图")
        btn_osm.setStyleSheet(btn_qss("primary"))
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
        desc = QLabel("按住左键拖拽框选任意区域（无需先缩放）")
        desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(desc)

        # 按钮行
        btn_row = QHBoxLayout()

        self.select_btn = QPushButton("自由框选区域")
        self.select_btn.setStyleSheet(btn_qss("primary"))
        self.select_btn.clicked.connect(self._select_extent)
        btn_row.addWidget(self.select_btn)

        clear_btn = QPushButton("清除")
        clear_btn.setStyleSheet(btn_qss("danger"))
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

        # ── 预设方案快捷选择 ──
        preset_group = QGroupBox("预设方案")
        preset_group.setStyleSheet(_PALETTE["group_style"])
        preset_layout = QVBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "自定义（手动配置）",
            "城市密集覆盖",
            "郊区广域覆盖",
            "高速沿线覆盖",
            "室内深度覆盖",
            "校园/园区微站",
        ])
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preset_combo.setToolTip("选择一个预设方案会自动填入下方所有参数，也可手动调整")
        preset_layout.addWidget(self.preset_combo)

        desc_label = QLabel("选择方案后可继续微调各参数")
        desc_label.setStyleSheet("color: #64748b; font-size: 11px;")
        preset_layout.addWidget(desc_label)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

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

        # ── AI 大模型辅助 ──
        ai_group = QGroupBox("AI 智能辅助")
        ai_group.setStyleSheet(_PALETTE["group_style"])
        ai_layout = QVBoxLayout()
        btn_ai_parse = QPushButton("AI 解析需求（自然语言）")
        btn_ai_parse.setStyleSheet(btn_qss("accent"))
        btn_ai_parse.clicked.connect(self._open_ai_parse_dialog)
        ai_layout.addWidget(btn_ai_parse)
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)

        layout.addStretch()

        return page

    # ── 预设方案定义 ──
    _PRESETS = {
        "城市密集覆盖":    {"band": "3.5GHz",   "height": 35,  "type": "宏站(MACRO)",     "sectors": 3, "scenario": "城市(URBAN)"},
        "郊区广域覆盖":    {"band": "700MHz",   "height": 50,  "type": "宏站(MACRO)",     "sectors": 3, "scenario": "郊区(SUBURBAN)"},
        "高速沿线覆盖":    {"band": "3.5GHz",   "height": 40,  "type": "宏站(MACRO)",     "sectors": 2, "scenario": "农村(RURAL)"},
        "室内深度覆盖":    {"band": "2.6GHz",   "height": 3,   "type": "室内站(INDOOR)",  "sectors": 0, "scenario": "城市(URBAN)"},
        "校园/园区微站":   {"band": "2.6GHz",   "height": 15,  "type": "微站(SMALL)",     "sectors": 3, "scenario": "城市(URBAN)"},
    }

    def _on_preset_changed(self, index):
        """预设方案切换 → 自动填充参数"""
        name = self.preset_combo.currentText()
        if name not in self._PRESETS:
            return  # "自定义" 不自动填充

        p = self._PRESETS[name]
        # 暂时断开信号避免循环触发
        self.band_combo.blockSignals(True)
        self.type_combo.blockSignals(True)
        self.scenario_combo.blockSignals(True)

        try:
            self.band_combo.setCurrentText(p["band"])
            self.height_spin.setValue(p["height"])
            self.type_combo.setCurrentText(p["type"])
            self.sector_spin.setValue(p["sectors"])
            self.scenario_combo.setCurrentText(p["scenario"])
            # 触发频段变化更新站间距标签
            self._on_band_changed(p["band"])
        finally:
            self.band_combo.blockSignals(False)
            self.type_combo.blockSignals(False)
            self.scenario_combo.blockSignals(False)

        self._log(f"已应用预设方案「{name}」")

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
        btn_generate.setStyleSheet(btn_qss("warn"))
        btn_generate.clicked.connect(self._generate_hex_grid)
        layout.addWidget(btn_generate)

        # 手动添加
        btn_row = QHBoxLayout()

        self.add_station_btn = QPushButton("手动添加基站")
        self.add_station_btn.setCheckable(True)
        self.add_station_btn.setStyleSheet(btn_qss("default"))
        self.add_station_btn.clicked.connect(self._toggle_add_station)
        btn_row.addWidget(self.add_station_btn)

        btn_clear = QPushButton("清除所有站点")
        btn_clear.setStyleSheet(btn_qss("danger"))
        btn_clear.clicked.connect(self._clear_all_sites)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)

        # 避让
        avoid_row = QHBoxLayout()
        btn_avoid = QPushButton("加载避让数据")
        btn_avoid.setStyleSheet(btn_qss("default"))
        btn_avoid.clicked.connect(self._load_avoidance)
        avoid_row.addWidget(btn_avoid)

        btn_clear_avoid = QPushButton("清除避让")
        btn_clear_avoid.setStyleSheet(btn_qss("default"))
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
        room_btn_row = QHBoxLayout()
        btn_add_room = QPushButton("在地图上点击添加机房")
        btn_add_room.setStyleSheet(btn_qss("accent"))
        btn_add_room.clicked.connect(self._toggle_add_room)
        room_btn_row.addWidget(btn_add_room)

        btn_del_room = QPushButton("删除机房")
        btn_del_room.setStyleSheet(btn_qss("danger"))
        btn_del_room.clicked.connect(self._delete_last_room)
        room_btn_row.addWidget(btn_del_room)
        room_layout.addLayout(room_btn_row)

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
        btn_add_by_coord.setStyleSheet(btn_qss("accent"))
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

        # 每米价格（可编辑 — 改后点「生成管线」自动用新价格计算）
        self.price_per_meter_spin = QDoubleSpinBox()
        self.price_per_meter_spin.setRange(1.0, 999.0)
        self.price_per_meter_spin.setValue(15.0)
        self.price_per_meter_spin.setDecimals(2)
        self.price_per_meter_spin.setSuffix(" 元/米")
        self.price_per_meter_spin.setStyleSheet(
            "QDoubleSpinBox { color: #e74c3c; font-weight: bold; padding: 4px; }"
        )
        self.price_per_meter_spin.setToolTip("输入每米管线的基础单价（元），将按此价格计算总成本")
        type_layout.addRow("每米价格:", self.price_per_meter_spin)

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
        btn_generate.setStyleSheet(btn_qss("warn"))
        btn_generate.clicked.connect(self._generate_pipelines)
        btn_row.addWidget(btn_generate)

        btn_clear = QPushButton("清除管线")
        btn_clear.setStyleSheet(btn_qss("danger"))
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
        legend_layout.setSpacing(6)

        def _swatch(color, text):
            row = QHBoxLayout()
            chip = QLabel()
            chip.setFixedSize(14, 14)
            chip.setStyleSheet(f"background:{color};border-radius:3px;")
            row.addWidget(chip)
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 11px;color:#475569;")
            row.addWidget(lbl)
            row.addStretch()
            wrap = QWidget()
            wrap.setLayout(row)
            return wrap

        legend_layout.addWidget(_swatch("#8B5A2B", "直埋光缆"))
        legend_layout.addWidget(_swatch("#2563eb", "通信管道"))
        legend_layout.addWidget(_swatch("#16a34a", "架空光缆"))
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
        btn_heatmap.setStyleSheet(btn_qss("accent"))
        btn_heatmap.clicked.connect(self._generate_heatmap)
        layout.addWidget(btn_heatmap)

        # 工程量报表
        report_group = QGroupBox("工程量报表")
        report_layout = QVBoxLayout()

        btn_report_txt = QPushButton("导出工程量报表 (TXT)")
        btn_report_txt.setStyleSheet(btn_qss("warn"))
        btn_report_txt.clicked.connect(self._export_report_txt)
        report_layout.addWidget(btn_report_txt)

        btn_report_csv = QPushButton("导出工程量报表 (CSV)")
        btn_report_csv.setStyleSheet(btn_qss("warn"))
        btn_report_csv.clicked.connect(self._export_report_csv)
        report_layout.addWidget(btn_report_csv)

        report_group.setLayout(report_layout)
        layout.addWidget(report_group)

        # ── 导出视图范围选择 ──
        export_view_group = QGroupBox("导出视图范围")
        export_view_group.setStyleSheet(_PALETTE["group_style"])
        ev_layout = QVBoxLayout()

        ev_desc = QLabel("先在地图上平移/缩放框定范围，选择“当前地图视图”即可导出所见即所得；\n或点“框选导出区域”拖拽矩形精确选择位置与大小。")
        ev_desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        ev_layout.addWidget(ev_desc)

        ev_mode_row = QHBoxLayout()
        ev_mode_row.addWidget(QLabel("范围来源:"))
        self.export_mode_combo = QComboBox()
        self.export_mode_combo.addItems(["当前地图视图", "框选区域"])
        self.export_mode_combo.setCurrentIndex(0)
        self.export_mode_combo.currentIndexChanged.connect(self._on_export_mode_changed)
        ev_mode_row.addWidget(self.export_mode_combo)
        ev_layout.addLayout(ev_mode_row)

        ev_btn_row = QHBoxLayout()
        self.export_select_btn = QPushButton("框选导出区域")
        self.export_select_btn.setStyleSheet(btn_qss("primary"))
        self.export_select_btn.clicked.connect(self._select_export_view)
        self.export_select_btn.setEnabled(False)
        ev_btn_row.addWidget(self.export_select_btn)

        self.export_clear_btn = QPushButton("清除")
        self.export_clear_btn.setStyleSheet(btn_qss("danger"))
        self.export_clear_btn.clicked.connect(self._clear_export_view)
        self.export_clear_btn.setEnabled(False)
        ev_btn_row.addWidget(self.export_clear_btn)
        ev_layout.addLayout(ev_btn_row)

        self.export_extent_label = QLabel("使用当前地图视图（平移/缩放地图后导出）")
        self.export_extent_label.setStyleSheet("color: gray; font-size: 12px;")
        self.export_extent_label.setWordWrap(True)
        ev_layout.addWidget(self.export_extent_label)

        ev_scale_row = QHBoxLayout()
        ev_scale_row.addWidget(QLabel("比例尺:"))
        self.export_scale_combo = QComboBox()
        self.export_scale_combo.addItems(["跟随视图", "1:1000", "1:2000", "1:5000", "1:10000", "1:25000", "1:50000"])
        self.export_scale_combo.setCurrentIndex(0)
        ev_scale_row.addWidget(self.export_scale_combo)
        ev_layout.addLayout(ev_scale_row)

        export_view_group.setLayout(ev_layout)
        layout.addWidget(export_view_group)

        # 导出行
        export_row = QHBoxLayout()

        btn_export = QPushButton("导出当前视图")
        btn_export.setStyleSheet(btn_qss("primary"))
        btn_export.clicked.connect(self._export_pdf)
        export_row.addWidget(btn_export)

        layout.addLayout(export_row)

        # 保存加载行
        file_row = QHBoxLayout()

        btn_save = QPushButton("保存方案")
        btn_save.setStyleSheet(btn_qss("default"))
        btn_save.clicked.connect(self._save_design)
        file_row.addWidget(btn_save)

        btn_load = QPushButton("加载方案")
        btn_load.setStyleSheet(btn_qss("default"))
        btn_load.clicked.connect(self._load_design)
        file_row.addWidget(btn_load)
        layout.addLayout(file_row)

        # 后端同步
        btn_sync = QPushButton("同步到M03后端")
        btn_sync.setStyleSheet(btn_qss("teal"))
        btn_sync.clicked.connect(self._sync_to_backend)
        layout.addWidget(btn_sync)

        # AI 生成报告
        btn_ai_report = QPushButton("AI 生成设计报告")
        btn_ai_report.setStyleSheet(btn_qss("accent"))
        btn_ai_report.clicked.connect(self._open_ai_report_dialog)
        layout.addWidget(btn_ai_report)

        layout.addStretch()

        return page

    def _build_site_table(self):
        group = QGroupBox("基站设计明细")
        layout = QVBoxLayout()

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
        layout.addWidget(self.site_table)

        # 操作按钮行
        btn_row = QHBoxLayout()

        btn_fly = QPushButton("定位到选中站点")
        btn_fly.setStyleSheet(btn_qss("default"))
        btn_fly.clicked.connect(self._fly_to_site)
        btn_row.addWidget(btn_fly)

        btn_delete = QPushButton("删除选中站点")
        btn_delete.setStyleSheet(btn_qss("danger"))
        btn_delete.clicked.connect(self._delete_site)
        btn_row.addWidget(btn_delete)

        btn_compare = QPushButton("频段对比")
        btn_compare.setStyleSheet(btn_qss("accent"))
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
        """激活自由框选工具：在地图上按住左键拖拽出任意矩形作为设计区域
        （替代旧逻辑：旧逻辑直接取当前整个视图范围，无法自由框选）
        """
        canvas = self.iface.mapCanvas()
        if not hasattr(self, '_extent_tool') or self._extent_tool is None:
            self._extent_tool = ExtentSelectTool(canvas)
            self._extent_tool.extent_selected.connect(self._on_extent_selected)
        canvas.setMapTool(self._extent_tool)
        self._log("自由框选：在地图上按住左键拖拽选择区域")

    def _on_extent_selected(self, rect):
        """ExtentSelectTool 拖拽结束回调：把自由框选的矩形设为设计区域"""
        canvas = self.iface.mapCanvas()

        # rect 是 project CRS 下的 QgsRectangle，转换到 WGS84
        project_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        if project_crs != wgs84:
            transform = QgsCoordinateTransform(project_crs, wgs84, QgsProject.instance())
            extent_wgs84 = transform.transform(rect)
        else:
            extent_wgs84 = rect

        area_km2 = self._calc_area_km2(extent_wgs84)

        self.selected_extent = (extent_wgs84.xMinimum(), extent_wgs84.yMinimum(),
                                extent_wgs84.xMaximum(), extent_wgs84.yMaximum())

        self.extent_label.setText(
            f"已选择: [{self.selected_extent[0]:.4f}, {self.selected_extent[1]:.4f}] "
            f"→ [{self.selected_extent[2]:.4f}, {self.selected_extent[3]:.4f}]\n"
            f"面积约 {area_km2:.1f} km²"
        )
        self.extent_label.setStyleSheet("color: #27ae60;")
        self._add_extent_rubber(rect)
        self._log(f"已选择区域: {area_km2:.1f} km²")

        # 拖拽完成后归还地图默认工具（平移/缩放），避免一直卡在框选模式
        try:
            canvas.unsetMapTool(self._extent_tool)
        except Exception:
            pass

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
    #  导出视图范围选择（独立于设计区域）
    # =================================================================

    def _on_export_mode_changed(self, idx):
        """切换“当前地图视图 / 框选区域”时更新提示与按钮可用性"""
        is_select = (idx == 1)
        self.export_select_btn.setEnabled(is_select)
        self.export_clear_btn.setEnabled(is_select)
        if is_select:
            if self.export_view_extent:
                self._show_export_extent_text()
            else:
                self.export_extent_label.setText("请点“框选导出区域”在地图上拖拽矩形")
                self.export_extent_label.setStyleSheet("color: gray;")
        else:
            self.export_extent_label.setText("使用当前地图视图（平移/缩放地图后导出）")
            self.export_extent_label.setStyleSheet("color: gray;")

    def _select_export_view(self):
        """激活框选工具，拖拽矩形作为导出视图范围"""
        canvas = self.iface.mapCanvas()
        if self._export_extent_tool is None:
            self._export_extent_tool = ExtentSelectTool(canvas)
            self._export_extent_tool.extent_selected.connect(self._on_export_view_selected)
        canvas.setMapTool(self._export_extent_tool)
        self._log("框选导出区域：在地图上按住左键拖拽选择导出范围")

    def _on_export_view_selected(self, rect):
        """框选结束：记录导出范围（转 WGS84）并绘制蓝色边框标记"""
        canvas = self.iface.mapCanvas()
        project_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        if project_crs != wgs84:
            transform = QgsCoordinateTransform(project_crs, wgs84, QgsProject.instance())
            extent_wgs84 = transform.transform(rect)
        else:
            extent_wgs84 = rect

        self.export_view_extent = extent_wgs84
        self._show_export_extent_text()

        for rb in self._export_extent_bands:
            canvas.scene().removeItem(rb)
        self._export_extent_bands.clear()
        rb = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
        rb.setColor(QColor(0, 120, 255))
        rb.setWidth(3)
        rb.addPoint(QgsPointXY(extent_wgs84.xMinimum(), extent_wgs84.yMinimum()), False)
        rb.addPoint(QgsPointXY(extent_wgs84.xMaximum(), extent_wgs84.yMinimum()), False)
        rb.addPoint(QgsPointXY(extent_wgs84.xMaximum(), extent_wgs84.yMaximum()), False)
        rb.addPoint(QgsPointXY(extent_wgs84.xMinimum(), extent_wgs84.yMaximum()), False)
        rb.addPoint(QgsPointXY(extent_wgs84.xMinimum(), extent_wgs84.yMinimum()), True)
        self._export_extent_bands.append(rb)
        canvas.refresh()

        try:
            canvas.unsetMapTool(self._export_extent_tool)
        except Exception:
            pass
        self._log("已框选导出区域")

    def _show_export_extent_text(self):
        if not self.export_view_extent:
            return
        e = self.export_view_extent
        self.export_extent_label.setText(
            f"已框选范围: [{e.xMinimum():.4f}, {e.yMinimum():.4f}] "
            f"→ [{e.xMaximum():.4f}, {e.yMaximum():.4f}]"
        )
        self.export_extent_label.setStyleSheet("color: #2980b9;")

    def _clear_export_view(self):
        canvas = self.iface.mapCanvas()
        for rb in self._export_extent_bands:
            canvas.scene().removeItem(rb)
        self._export_extent_bands.clear()
        self.export_view_extent = None
        if self.export_mode_combo.currentIndex() == 0:
            self.export_extent_label.setText("使用当前地图视图（平移/缩放地图后导出）")
        else:
            self.export_extent_label.setText("请点“框选导出区域”在地图上拖拽矩形")
        self.export_extent_label.setStyleSheet("color: gray;")
        canvas.refresh()

    # =================================================================
    #  第三步：参数
    # =================================================================

    def _on_band_changed(self, band):
        if band in BAND_CONFIGS:
            self.isr_label.setText(f"站间距: {BAND_CONFIGS[band].ideal_isr_km} km")

    def _on_pipeline_type_changed(self, type_text):
        """管线类型变化时更新每米价格默认值"""
        price_map = {
            "直埋光缆": 15,
            "通信管道": 45,
            "架空光缆": 18,
        }
        price = price_map.get(type_text, 15)
        self.price_per_meter_spin.setValue(price)

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
        """地图点击添加机房 - 转换为WGS84经纬度"""
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

        # 自动生成机房编号
        self.room_counter += 1
        room_id = f"ROOM-{self.room_counter:03d}"
        room_name = f"机房{self.room_counter}"

        # 机房数据（使用WGS84经纬度）
        data = MachineRoom(
            room_id=room_id,
            name=room_name,
            room_type='汇聚机房',
            longitude=lon_wgs84,
            latitude=lat_wgs84,
            capacity=10,
        )

        # 保存机房数据
        self.machine_rooms.append(data)

        # 更新输入框（显示经纬度）
        self.room_lon_spin.setValue(lon_wgs84)
        self.room_lat_spin.setValue(lat_wgs84)

        # 添加机房标记到地图（使用原始坐标）
        self._add_room_marker(lon, lat, room_name, room_id)

        # 更新机房列表显示
        self.room_list_label.setText(f"已添加机房: {len(self.machine_rooms)}个")

        self._log(f"已添加机房: {room_name} ({lon_wgs84:.6f}, {lat_wgs84:.6f})")

        # 取消添加模式
        if hasattr(self, '_room_tool'):
            self.iface.mapCanvas().unsetMapTool(self._room_tool)

    def _add_room_by_coord(self):
        """按输入框坐标添加机房"""
        lon = self.room_lon_spin.value()
        lat = self.room_lat_spin.value()

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
        self._add_room_marker(lon, lat, room_name, room_id)

        # 更新机房列表显示
        self.room_list_label.setText(f"已添加机房: {len(self.machine_rooms)}个")

        self._log(f"已添加机房: {room_name} ({lon:.6f}, {lat:.6f})")

    def _delete_last_room(self):
        """删除最后一个添加的机房（含地图标记）"""
        if not self.machine_rooms:
            QMessageBox.information(self, "提示", "当前没有可删除的机房")
            return

        last_room = self.machine_rooms[-1]
        room_id = last_room.room_id
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除最后一个机房吗？\n\n• {last_room.name} ({room_id})\n"
            f"经度: {last_room.longitude:.6f}, 纬度: {last_room.latitude:.6f}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 移除地图标记
        bands = self._room_markers.pop(room_id, [])
        canvas = self.iface.mapCanvas()
        for rb in bands:
            if rb in self._marker_bands:
                self._marker_bands.remove(rb)
            canvas.scene().removeItem(rb)
        canvas.refresh()

        # 移除数据
        self.machine_rooms.pop()
        self.room_list_label.setText(f"已添加机房: {len(self.machine_rooms)}个")
        self._log(f"已删除机房: {last_room.name} ({room_id})")

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

    def _add_room_marker(self, lon, lat, name, room_id=None):
        """添加机房标记到地图，并按 room_id 记录以便删除"""
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
        if room_id is not None:
            self._room_markers[room_id] = [rb_outer, rb_inner]
        canvas.refresh()

    def _generate_pipelines(self):
        """生成管线 — 使用内存矢量图层渲染"""
        if not self.generated_sites:
            QMessageBox.warning(self, "提示", "请先生成基站")
            return

        # 如果没有机房，使用输入框的坐标创建一个
        if not self.machine_rooms:
            self.machine_rooms.append(MachineRoom(
                room_id='ROOM-001',
                name='默认机房',
                room_type='汇聚机房',
                longitude=self.room_lon_spin.value(),
                latitude=self.room_lat_spin.value(),
                capacity=10,
            ))

        self._log("正在生成管线...")
        self._show_progress(True, 10)
        QApplication.processEvents()

        try:
            # 获取管线类型
            type_map = {
                "直埋光缆": PipelineType.DIRECT_BURIED,
                "通信管道": PipelineType.DUCT,
                "架空光缆": PipelineType.AERIAL,
            }
            pipeline_type = type_map[self.pipeline_type_combo.currentText()]
            route_type = "direct" if self.route_type_combo.currentIndex() == 0 else "manhattan"

            self._show_progress(True, 20)
            QApplication.processEvents()

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

            # ---- 用内存矢量图层渲染管线 ----
            # 清除旧管线图层
            for old_name in ["通信管线", "基站-管线关联"]:
                for old_layer in QgsProject.instance().mapLayersByName(old_name):
                    QgsProject.instance().removeMapLayer(old_layer.id())

            # 创建管线图层
            create_pipeline_layer(all_pipelines, "通信管线")

            # 创建基站-管线关联线
            create_connection_layer(self.generated_sites, all_pipelines, "基站-管线关联")

            # 刷新地图
            canvas = self.iface.mapCanvas()
            canvas.refresh()

            # 更新统计
            self.pipeline_stats_label.setText(f"管线: {len(all_pipelines)}条")

            # 计算成本（使用用户自定义的每米价格）
            custom_price = self.price_per_meter_spin.value()
            cost_summary = calculate_total_cost_with_price(all_pipelines, custom_price)
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
        """清除管线"""
        # 清除管线图层和关联线图层
        for layer_name in ["通信管线", "基站-管线关联"]:
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

            self._log(f"频段: {band_key}, 半径: {radius_km:.1f}km, 基站数: {len(self.generated_sites)}")

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
                self._log(f"  站点 {i+1}/{total}: {len(data)} 个覆盖点")
                self._show_progress(True, int((i + 1) / total * 80))

            self._log(f"总计覆盖点数: {len(all_data)}")

            if not all_data:
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

            self._create_heatmap_layer(all_data)
            self._log(f"热力图已生成: {len(all_data)}个点, {total}个基站叠加")

            self._show_progress(False)

        except Exception as e:
            self._log(f"热力图生成失败: {e}")
            self._show_progress(False)

    def _create_heatmap_layer(self, data, site_lon=None, site_lat=None):
        """创建覆盖热力图 — 内存点图层 + 分级符号（QGIS 3.44兼容）"""
        from qgis.core import (
            QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
            QgsField, QgsProject,
            QgsGraduatedSymbolRenderer, QgsRendererRange,
            QgsCoordinateReferenceSystem,
        )
        from qgis.PyQt.QtCore import QVariant
        from qgis.PyQt.QtGui import QColor

        layer_name = "覆盖热力图"
        # 移除旧图层
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            QgsProject.instance().removeMapLayer(layers[0])

        # 创建内存点图层
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326", layer_name, "memory"
        )
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("rsrp", QVariant.Double),
        ])
        layer.updateFields()

        # 添加要素
        features = []
        for d in data:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(
                QgsPointXY(d['longitude'], d['latitude'])
            ))
            feat.setAttributes([d['rsrp']])
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()

        # 分级符号渲染：按RSRP范围不同大小和颜色
        # 注意：QgsRendererRange 要求 lower < upper，所以按数值升序排列
        # size 用毫米单位，调小避免点互相重叠、遮挡底图
        ranges = [
            (-120, -100, QColor(25, 25, 150, 60), 1.0, "很弱"),
            (-100, -90, QColor(0, 100, 255, 90), 1.3, "较弱"),
            (-90, -80, QColor(0, 200, 100, 120), 1.6, "良好"),
            (-80, -65, QColor(255, 200, 0, 150), 2.0, "强"),
            (-65, -50, QColor(255, 50, 50, 180), 2.5, "极强"),
        ]

        render_ranges = []
        for bottom, top, color, size, label in ranges:
            sym = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': color.name(QColor.HexArgb),
                'size': str(size),
                'outline_color': '0,0,0,0',
            })
            rng = QgsRendererRange(bottom, top, sym, label)
            render_ranges.append(rng)

        renderer = QgsGraduatedSymbolRenderer('rsrp', render_ranges)
        renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
        layer.setRenderer(renderer)
        layer.setOpacity(0.85)

        QgsProject.instance().addMapLayer(layer)

        # 缩放到热力图范围
        canvas = self.iface.mapCanvas()
        ext = layer.extent()
        if not ext.isEmpty():
            canvas.setExtent(ext)
        canvas.refresh()

        # 计算覆盖统计
        rsrp_values = [d['rsrp'] for d in data]
        if rsrp_values:
            excellent = len([r for r in rsrp_values if r >= -65])
            good = len([r for r in rsrp_values if -80 <= r < -65])
            fair = len([r for r in rsrp_values if -90 <= r < -80])
            poor = len([r for r in rsrp_values if -100 <= r < -90])
            very_poor = len([r for r in rsrp_values if r < -100])
            total_points = len(data)
            avg_rsrp = round(sum(rsrp_values) / len(rsrp_values), 1)
            coverage_rate = round((excellent + good) / total_points * 100, 1) if total_points > 0 else 0
        else:
            excellent = good = fair = poor = very_poor = 0
            total_points = avg_rsrp = coverage_rate = 0

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
        form.addRow("基站数量:", QLabel(f"{total_sites} 个"))
        form.addRow("有效覆盖点:", QLabel(f"{total_points:,} 个"))
        form.addRow("平均 RSRP:", QLabel(f"{avg_rsrp} dBm"))
        form.addRow("覆盖率(≥-80dBm):", QLabel(f"<b>{coverage_rate:.1f}%</b>"))
        overview.setLayout(form)
        layout.addWidget(overview)

        # 分级统计
        grade = QGroupBox("覆盖分级")
        grade_form = QFormLayout()
        grade_form.addRow("<span style='color:#ff0000'>●</span> 很强(≥-65dBm):", QLabel(f"<b>{excellent}</b> 点"))
        grade_form.addRow("<span style='color:#00ff00'>●</span> 良好(-80~-65dBm):", QLabel(f"<b>{good}</b> 点"))
        grade_form.addRow("<span style='color:#ffff00'>●</span> 一般(-90~-80dBm):", QLabel(f"<b>{fair}</b> 点"))
        grade_form.addRow("<span style='color:#ff8c00'>●</span> 较差(-100~-90dBm):", QLabel(f"<b>{poor}</b> 点"))
        grade_form.addRow("<span style='color:#1a1a7a'>●</span> 很差(<-100dBm):", QLabel(f"<b>{very_poor}</b> 点"))
        grade.setLayout(grade_form)
        layout.addWidget(grade)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(btn_qss("primary"))
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
        """导出标准图纸（PDF/PNG）"""
        if not self.generated_sites:
            QMessageBox.warning(self, "导出", "没有站点数据")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出标准图纸", "基站设计方案.pdf",
            "PDF (*.pdf);;PNG (*.png)")
        if not fpath:
            return

        try:
            canvas = self.iface.mapCanvas()
            # 导出范围：优先“框选区域”模式下用户拖拽的矩形；否则用当前地图视图
            # （用户已自行平移/缩放 = 自己选择了位置与比例），做到所见即所得。
            if self.export_mode_combo.currentIndex() == 1 and self.export_view_extent:
                e = self.export_view_extent
                extent = QgsRectangle(e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum())
            else:
                extent = canvas.extent()

            # 比例尺：默认跟随视图，也可在下拉框指定固定比例（位置=范围中心）
            scale_text = self.export_scale_combo.currentText()
            scale = None
            if scale_text != "跟随视图":
                try:
                    scale = float(scale_text.split(":")[1])
                except Exception:
                    scale = None

            paper_size = "A3" if fpath.endswith(".pdf") else "A4"
            export_fmt = "PDF" if fpath.endswith(".pdf") else "PNG"

            result = create_standard_design_drawing(
                project=QgsProject.instance(),
                sites=self.generated_sites,
                map_extent=extent,
                title="基站设计方案",
                output_path=fpath,
                paper_size=paper_size,
                export_format=export_fmt,
                scale=scale,
            )
            if result:
                QMessageBox.information(self, "导出成功", f"已导出到:\n{result}")
                self._log("标准图纸已导出")
            else:
                QMessageBox.warning(self, "导出失败", "导出失败，请检查QGIS Print Layout支持")
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

        # 机房列表（真实坐标，QGIS 中由用户添加或默认生成）
        rooms = []
        for r in self.machine_rooms:
            rooms.append({
                "room_id": getattr(r, "room_id", ""),
                "name": getattr(r, "name", "机房"),
                "room_type": getattr(r, "room_type", "汇聚机房"),
                "longitude": float(getattr(r, "longitude", 0)),
                "latitude": float(getattr(r, "latitude", 0)),
                "capacity": getattr(r, "capacity", 0),
            })
        # 路由类型：direct=直线, manhattan=曼哈顿(L型)
        route_type = "direct" if self.route_type_combo.currentIndex() == 0 else "manhattan"

        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "band": self.band_combo.currentText(),
                "tower_height": self.height_spin.value(),
                "route_type": route_type,
                "machine_rooms": rooms,
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
            if 'route_type' in props:
                self.route_type_combo.setCurrentIndex(0 if props['route_type'] == 'direct' else 1)

            # 恢复机房列表（真实坐标）
            self.machine_rooms = []
            for r in props.get('machine_rooms', []):
                self.machine_rooms.append(MachineRoom(
                    room_id=r.get('room_id', 'ROOM-001'),
                    name=r.get('name', '机房'),
                    room_type=r.get('room_type', '汇聚机房'),
                    longitude=float(r.get('longitude', 0)),
                    latitude=float(r.get('latitude', 0)),
                    capacity=r.get('capacity', 0),
                ))
            if self.machine_rooms:
                last_room = self.machine_rooms[-1]
                self._log(f"已恢复机房: {last_room.name}({last_room.longitude:.4f},{last_room.latitude:.4f})")
                self.room_list_label.setText(f"已添加机房: {len(self.machine_rooms)}个")

            self._log(f"已加载 {len(sites)} 个站点")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _show_project_select_dialog(self, projects: List[Dict]) -> Optional[Dict]:
        """
        显示项目选择弹窗：列出服务器已有项目 / 本地保存 / 新建选项

        Args:
            projects: 从后端拉取的项目列表

        Returns:
            选择结果字典，取消返回 None
            - {'mode': 'server', 'project_id': int}
            - {'mode': 'local'}
        """
        from qgis.PyQt.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
            QPushButton, QButtonGroup, QLabel, QLineEdit, QSpinBox,
            QGroupBox, QScrollArea
        )
        from qgis.PyQt.QtCore import Qt

        dlg = QDialog(self)
        dlg.setWindowTitle("选择目标项目")
        dlg.setMinimumWidth(460)

        layout = QVBoxLayout(dlg)

        # 上传摘要
        summary = QLabel(
            f"将同步数据:\n"
            f"  • 基站: {len(self.generated_sites)} 个\n"
            f"  • 机房: {len(self.machine_rooms)} 个\n"
            f"  • 路由: {self.route_type_combo.currentText()} | "
            f"频段: {self.band_combo.currentText()}"
        )
        summary.setStyleSheet("font-size: 12px; color: #555; padding: 4px;")
        layout.addWidget(summary)

        # 目标类型选择
        type_group = QButtonGroup(dlg)

        # ---- 1. 服务器已有项目 ----
        server_radio = QRadioButton("同步到服务器已有项目")
        type_group.addButton(server_radio)
        layout.addWidget(server_radio)

        server_group = QGroupBox(f"服务器已有项目 ({len(projects)} 个)")
        server_layout = QVBoxLayout(server_group)

        project_group = QButtonGroup(dlg)
        radio_list = []

        if projects:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_inner = QWidget()
            scroll_layout = QVBoxLayout(scroll_inner)
            scroll_layout.setSpacing(4)

            for p in projects:
                pid = p.get('id', '?')
                pname = p.get('projectName', f'项目{pid}')
                pcode = p.get('projectCode', '')
                status = p.get('status', '')
                status_tag = '[运行]' if status == 'active' else '[停止]'

                rb = QRadioButton(
                    f"{status_tag} [{pid}] {pname}"
                    + (f" ({pcode})" if pcode else "")
                )
                rb.setProperty("project_id", int(pid))
                project_group.addButton(rb)
                scroll_layout.addWidget(rb)
                radio_list.append(rb)

            scroll_layout.addStretch()
            scroll.setWidget(scroll_inner)
            server_layout.addWidget(scroll)

            if radio_list:
                radio_list[0].setChecked(True)
        else:
            server_layout.addWidget(QLabel("  (暂无项目)"))

        layout.addWidget(server_group)

        # ---- 2. 本地保存 ----
        local_radio = QRadioButton("保存到本地文件（不上传服务器）")
        type_group.addButton(local_radio)
        layout.addWidget(local_radio)

        local_note = QLabel("  数据将导出为 GeoJSON 文件，可在本机通过「加载方案」恢复")
        local_note.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(local_note)

        # ---- 3. 新建服务器项目 ----
        new_radio = QRadioButton("同步到新建服务器项目")
        type_group.addButton(new_radio)
        layout.addWidget(new_radio)

        new_group = QGroupBox("新建项目（输入新 ID）")
        new_layout = QHBoxLayout(new_group)

        new_id_spin = QSpinBox()
        new_id_spin.setRange(1, 99999)
        new_id_spin.setValue(max((p.get('id', 0) for p in projects), default=0) + 1)
        new_layout.addWidget(QLabel("项目ID:"))
        new_layout.addWidget(new_id_spin)

        new_name_edit = QLineEdit()
        new_name_edit.setPlaceholderText("项目名称(可选)")
        new_layout.addWidget(new_name_edit)
        new_layout.addStretch()

        layout.addWidget(new_group)

        # 默认选中
        if projects:
            server_radio.setChecked(True)
        else:
            local_radio.setChecked(True)

        # 按钮
        btn_box = QHBoxLayout()
        ok_btn = QPushButton("确认")
        ok_btn.setStyleSheet("background-color: #409eff; color: white; font-weight: bold; padding: 6px;")
        cancel_btn = QPushButton("取消")
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(ok_btn)
        layout.addLayout(btn_box)

        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)

        result = dlg.exec_()
        if result != QDialog.Accepted:
            return None

        # 取值
        if server_radio.isChecked():
            checked = project_group.checkedButton()
            if checked is None:
                return None
            pid = checked.property("project_id")
            return {"mode": "server", "project_id": int(pid)}

        if local_radio.isChecked():
            return {"mode": "local"}

        if new_radio.isChecked():
            return {
                "mode": "server",
                "project_id": int(new_id_spin.value()),
                "project_name": new_name_edit.text().strip(),
            }

        return None

    def _sync_to_backend(self):
        """同步设计数据：可选上传到 M03 后端或保存到本地 GeoJSON"""
        if not self.generated_sites:
            QMessageBox.warning(self, "同步失败", "没有站点数据，请先生成基站")
            return

        # 确保有机房数据（与生成管线逻辑一致：无机房时自动创建默认机房）
        if not self.machine_rooms:
            self.machine_rooms.append(MachineRoom(
                room_id='ROOM-001',
                name='默认机房',
                room_type='汇聚机房',
                longitude=self.room_lon_spin.value(),
                latitude=self.room_lat_spin.value(),
                capacity=10,
            ))
            self._log(f"自动创建默认机房: ({self.room_lon_spin.value():.4f}, {self.room_lat_spin.value():.4f})")

        # ---- 从服务器拉取已有项目列表，让用户选择目标 ----
        projects = self.sync_engine.fetch_projects()
        choice = self._show_project_select_dialog(projects)
        if choice is None:
            return

        # ---- 本地保存模式 ----
        if choice.get("mode") == "local":
            self._save_design()
            return

        # ---- 服务器同步模式 ----
        project_id = choice.get("project_id")
        if project_id is None:
            return

        params = {
            "scheme_name": f"基站设计_{datetime.now().strftime('%Y%m%d_%H%M')}",
            "band": self.band_combo.currentText(),
            "tower_height": self.height_spin.value(),
        }

        route_type = "direct" if self.route_type_combo.currentIndex() == 0 else "manhattan"
        room = self.machine_rooms[0]

        self._log(f"开始同步 → 项目{project_id}...")
        self._log(f"  站点数: {len(self.generated_sites)}, 机房: {room.name}({room.longitude:.4f},{room.latitude:.4f}), 路由: {route_type}")

        try:
            success, msg = self.sync_engine.upload_design(
                project_id=project_id,
                sites=self.generated_sites,
                params=params,
                machine_rooms=self.machine_rooms,
                route_type=route_type,
            )

            if success:
                detail = msg if isinstance(msg, dict) else {"scheme_id": msg}
                scheme_id = detail.get("scheme_id", "?")
                verified = detail.get("verified")
                verify_note = " (校验回环通过)" if verified else " (校验回环未确认)"
                self._log(f"同步成功! 方案ID={scheme_id}{verify_note}")
                QMessageBox.information(
                    self, "同步成功",
                    f"设计方案已同步到S1后端!\n\n"
                    f"方案ID: {scheme_id}\n"
                    f"项目ID: {project_id}\n"
                    f"基站数: {len(self.generated_sites)}\n"
                    f"机房: {room.name} ({room.longitude:.4f}, {room.latitude:.4f})\n"
                    f"路由类型: {self.route_type_combo.currentText()}\n"
                    f"校验回环: {'已通过' if verified else '未确认'}\n\n"
                    f"请在S1门户刷新页面查看效果。"
                )
            else:
                self._log(f"同步失败: {msg}")
                # 提供更详细的错误诊断
                detail_msg = msg
                if "未运行" in msg or "ConnectionError" in msg:
                    detail_msg = f"{msg}\n\n请确认:\n1. M03后端已启动 (端口8083)\n2. 后端地址: {self.sync_engine.api_url}"
                elif "HTTP" in msg:
                    detail_msg = f"{msg}\n\n可能原因:\n1. 后端接口路径变更\n2. 后端内部错误 (检查后端日志)"
                QMessageBox.warning(self, "同步失败", detail_msg)

        except Exception as e:
            self._log(f"同步异常: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "同步异常", f"发生未知错误:\n{e}")

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
    #  AI 大模型辅助（对接 M03 /api/m03/llm/**，经 X-API-Key 内部鉴权）
    # =================================================================

    def _open_ai_parse_dialog(self):
        """AI 解析需求：自然语言 → 结构化参数，回填到左侧参数控件。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("AI 解析设计需求")
        dlg.setMinimumSize(460, 360)
        dlg.setStyleSheet("QDialog{background:#fafafa;}QLabel{color:#334155;}")

        layout = QVBoxLayout(dlg)
        tip = QLabel("用一句话描述设计需求，AI 将解析为结构化参数并回填：")
        tip.setStyleSheet("font-size:12px;padding:4px;")
        layout.addWidget(tip)

        input_edit = QTextEdit()
        input_edit.setPlaceholderText(
            "例：在运城学院建一个宏基站，站高30米，覆盖半径500米，频段FDD-LTE-1800，三扇区，城区")
        input_edit.setMaximumHeight(90)
        layout.addWidget(input_edit)

        btn_row = QHBoxLayout()
        parse_btn = QPushButton("AI 解析")
        parse_btn.setStyleSheet(btn_qss("primary"))
        cancel_btn = QPushButton("关闭")
        cancel_btn.setStyleSheet(btn_qss("default"))
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(parse_btn)
        layout.addLayout(btn_row)

        result_edit = QTextEdit()
        result_edit.setReadOnly(True)
        result_edit.setPlaceholderText("解析结果将显示在此，并自动回填到参数控件")
        layout.addWidget(result_edit)

        def do_parse():
            text = input_edit.toPlainText().strip()
            if not text:
                QMessageBox.warning(dlg, "提示", "请输入设计需求描述")
                return
            result_edit.setPlainText("解析中…")
            QApplication.processEvents()
            params = self.sync_engine.parse_design_params(text)
            if not params:
                result_edit.setPlainText(
                    "解析失败：请确认 M03 后端与 llm-service 已启动，"
                    "且 QGIS 环境变量 M03_API_KEY 已正确配置。")
                return
            applied = self._apply_ai_params(params)
            result_edit.setPlainText(
                "解析成功，已回填参数：\n" + json.dumps(applied, ensure_ascii=False, indent=2))

        parse_btn.clicked.connect(do_parse)
        cancel_btn.clicked.connect(dlg.accept)
        dlg.exec_()

    def _apply_ai_params(self, params: dict) -> dict:
        """将 LLM 解析结果映射到左侧控件（仅回填通用字段，频段需人工确认）。"""
        applied = {}
        # 基站类型
        tt = (params.get("template_type") or "").lower()
        type_map = {"macro": "宏站(MACRO)", "micro": "微站(SMALL)", "indoor": "室内站(INDOOR)"}
        if tt in type_map:
            self.type_combo.setCurrentText(type_map[tt])
            applied["基站类型"] = type_map[tt]
        # 场景
        sc = (params.get("scenario") or "").lower()
        sc_map = {"urban": "城市(URBAN)", "suburban": "郊区(SUBURBAN)",
                  "rural": "农村(RURAL)", "indoor": "城市(URBAN)"}
        if sc in sc_map:
            self.scenario_combo.setCurrentText(sc_map[sc])
            applied["场景"] = sc_map[sc]
        # 塔高
        if params.get("tower_height") is not None:
            h = int(params["tower_height"])
            h = max(3, min(60, h))
            self.height_spin.setValue(h)
            applied["塔高(米)"] = h
        # 扇区数
        if params.get("sector_count") is not None:
            s = int(params["sector_count"])
            s = max(0, min(6, s))
            self.sector_spin.setValue(s)
            applied["扇区数"] = s
        # 频率（band_combo 为频段显示名，LLM 返回标准频段，展示供参考不强行切换）
        fb = params.get("frequency_band")
        if fb:
            applied["频段(参考)"] = fb
        cr = params.get("coverage_radius")
        if cr is not None:
            applied["覆盖半径(米,参考)"] = cr
        lon = params.get("center_longitude")
        lat = params.get("center_latitude")
        if lon is not None and lat is not None:
            applied["中心坐标(参考)"] = f"{lon:.4f}, {lat:.4f}"
        self._log("AI 解析需求已回填参数")
        return applied

    def _open_ai_report_dialog(self):
        """AI 生成报告：当前设计方案 → Markdown 评审/交付报告。"""
        if not self.generated_sites:
            QMessageBox.warning(self, "提示", "请先生成基站方案")
            return
        scheme = self._build_scheme_for_report()
        if scheme is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("AI 生成设计报告")
        dlg.setMinimumSize(640, 520)
        dlg.setStyleSheet("QDialog{background:#fafafa;}")
        layout = QVBoxLayout(dlg)
        status = QLabel("生成中，请稍候…")
        status.setStyleSheet("color:#64748b;font-size:12px;padding:4px;")
        layout.addWidget(status)
        md_view = QTextEdit()
        md_view.setReadOnly(True)
        layout.addWidget(md_view)
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(btn_qss("default"))
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)

        QApplication.processEvents()
        markdown = self.sync_engine.generate_report(scheme)
        if not markdown:
            status.setText(
                "生成失败：请确认 M03 后端与 llm-service 已启动，"
                "且 QGIS 环境变量 M03_API_KEY 已正确配置。")
            md_view.setPlainText("(无报告内容)")
        else:
            status.setText("生成完成")
            # QGIS 内置 Qt 5.15 的 QTextEdit 支持 Markdown 渲染
            if hasattr(md_view, "setMarkdown"):
                md_view.setMarkdown(markdown)
            else:
                md_view.setPlainText(markdown)

        dlg.exec_()

    def _build_scheme_for_report(self) -> Optional[dict]:
        """组装传给 /generate-report 的 scheme（站点 + 机房 + 参数）。"""
        try:
            cur_sc = self.scenario_combo.currentText()
            scenario = cur_sc.split("(")[1].rstrip(")") if "(" in cur_sc else "URBAN"
            sites = []
            for s in self.generated_sites:
                sites.append({
                    "siteId": s.get("site_id"),
                    "name": s.get("name"),
                    "longitude": s.get("longitude"),
                    "latitude": s.get("latitude"),
                    "towerHeight": s.get("tower_height"),
                    "siteType": s.get("site_type"),
                    "scenario": s.get("scenario", scenario),
                    "frequencyBand": s.get("band"),
                    "frequencyMHz": s.get("frequency"),
                    "powerW": s.get("power"),
                    "gainDbi": s.get("gain"),
                    "numSectors": s.get("num_sectors"),
                })
            rooms = []
            for r in self.machine_rooms:
                if isinstance(r, dict):
                    rooms.append(r)
                else:
                    rooms.append({
                        "roomId": r.room_id, "name": r.name,
                        "longitude": r.longitude, "latitude": r.latitude,
                        "roomType": r.room_type,
                    })
            return {
                "projectName": "通信基站设计方案",
                "band": self.band_combo.currentText(),
                "towerHeight": self.height_spin.value(),
                "scenario": scenario,
                "siteCount": len(sites),
                "sites": sites,
                "machineRooms": rooms,
            }
        except Exception as e:
            QMessageBox.critical(self, "组装失败", str(e))
            return None

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

    def _fly_to_site(self):
        """定位到选中站点"""
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
        canvas.setCenter(center)
        canvas.refresh()
        self._log(f"已定位到站点: {site.get('name', site.get('site_id', ''))}")

    def _delete_site(self):
        """删除选中站点"""
        row = self.site_table.currentRow()
        if row < 0 or row >= len(self.generated_sites):
            QMessageBox.warning(self, "提示", "请先选择一个站点")
            return
        reply = QMessageBox.question(self, "确认",
                                     f"确定删除站点 '{self.generated_sites[row].get('name', '')}'？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.generated_sites.pop(row)
        self._update_site_table()
        self._log(f"已删除站点: {row}")

    def _show_band_comparison(self):
        """频段对比：在同一区域叠加显示不同频段的基站布局"""
        if not self.selected_extent:
            QMessageBox.warning(self, "提示", "请先在第二步选择设计区域")
            return
        if len(self.generated_sites) == 0:
            QMessageBox.warning(self, "提示", "请先生成基站方案")
            return

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

        try:
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
            close_btn.setStyleSheet(btn_qss("primary"))
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            dialog.exec_()

            self._log("频段对比完成")
            self._show_progress(False)

        except Exception as e:
            self._log(f"频段对比失败: {e}")
            QMessageBox.critical(self, "错误", f"频段对比失败: {e}")
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

    def _log(self, text):
        self.log_text.append(f"[设计] {text}")

    def _show_progress(self, show, value=0):
        self.progress.setVisible(show)
        if show:
            self.progress.setValue(value)
        # 减少processEvents调用，避免闪回
        if value % 20 == 0 or value >= 95:
            QApplication.processEvents()
