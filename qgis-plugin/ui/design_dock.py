# -*- coding: utf-8 -*-
"""通信设施智能设计面板 — 基站+管线+机房

功能：
1. 加载底图（Esri 卫星、OSM）
2. 选择设计区域（缩放+点击）
3. 设置基站参数
4. 生成蜂窝拓扑 / 手动添加
5. 覆盖分析 / 导出
6. 管线设计（路由规划、工程量计算）
7. 机房设计（选址、容量规划）
"""

import os
import json
import math
from datetime import datetime
from typing import List, Optional, Dict

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QFileDialog, QMessageBox, QApplication,
    QTextEdit, QInputDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox,
    QDialog, QScrollArea, QShortcut, QLineEdit, QSlider, QMenu,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSettings, QVariant
from qgis.PyQt.QtGui import QColor, QFont, QKeySequence, QIntValidator
from qgis.core import (
    Qgis,
    QgsProject, QgsRectangle, QgsPointXY, QgsWkbTypes,
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsField,
    QgsMarkerSymbol, QgsLineSymbol, QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
    QgsRendererCategory, QgsRendererRange, QgsGraduatedSymbolRenderer,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsRasterLayer, QgsMapLayer,
)
from qgis.gui import QgsRubberBand

from design_engine.rules import BAND_CONFIGS
from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
from design_engine.coverage import generate_coverage_raster, rsrp_to_color
from design_engine.coverage_heatmap import generate_coverage_heatmap_data
from design_engine.avoidance import AvoidanceChecker
from design_engine.pipeline import (
    generate_pipeline_to_room,
    generate_pipelines_for_sites, calculate_total_engineering_volume,
    generate_shared_pipelines, calculate_shared_engineering_volume,
    calculate_pipeline_cost, calculate_total_cost, calculate_total_cost_with_price,
    generate_pipeline_report_text, export_pipeline_report_csv,
    generate_direct_route, generate_manhattan_route,
    Pipeline, PipelineType, PipelineConfig, FiberType
)
from layers.pipeline_layer import (
    create_pipeline_layer, create_connection_layer,
    get_pipeline_info, export_pipelines_to_geojson
)
# #5 Phase B：greenfield FTTH 设计生成器（纯 Python，无 QGIS 依赖，可离线自测）
from ftth.design_generator import generate_ftth_design
from ui.basemap import add_osm, add_esri_imagery, add_tianditu_imagery, add_tianditu_labels
from tools.station_tool import AddStationTool
from ui.station_dialog import StationDialog
from tools.room_tool import AddRoomTool
from tools.extent_tool import ExtentSelectTool
from tools.linkage_tool import LinkageQueryTool
from ui.room_dialog import RoomDialog
from ui.design_constants import (
    BASEMAP_SOURCES, DRAWING_TYPES, REPORT_SAVE_FILTER, REPORT_DEFAULT_NAME
)
from ui.design_logic import (
    resolve_report_target, drawing_type_for_index, should_fallback_local,
    CSV, TXT, DRAWING_PDF, DRAWING_FTTH
)
from models.machine_room import MachineRoom
from models.tech import get_baseline, default_band_for
from design_engine.layout_export import (
    create_design_layout, add_map_to_layout, add_title_to_layout,
    add_info_box_to_layout, add_legend_to_layout, add_scale_bar_to_layout,
    add_north_arrow_to_layout, export_layout_to_pdf,
    create_standard_design_drawing,
)
from design_engine.data_sync import DataSync
from report_docx import markdown_to_docx

# =================================================================
#  专业名词通俗解释（鼠标悬停显示，见 apply_glossary_tips）
#  说明：挑战杯演示面向非专业评委，给每个专业名词加一句大白话。
#  键为术语（尽量具体，避免被更短的词误匹配），值为通俗解释。
# =================================================================
GLOSSARY = {
    "FTTH": "光纤到户（Fiber To The Home）：把光纤直接拉进每家每户，实现千兆级高速上网。",
    "OLT": "光线路终端：接入网的“总入口”，所有用户的光信号都汇聚到这里再上联骨干网。",
    "ONU": "光网络单元：用户端的光猫设备，把光信号转成网线/WiFi 给家里用。",
    "FD": "光分纤箱（含分光器）：像“分光插座”，把一根主干光纤分成多路分给不同楼栋。",
    "光交箱": "光缆交接箱：各路光缆在这里汇接、跳线，相当于光缆的“配电箱”。",
    "IMB": "楼栋（法式数据 Immeuble）：覆盖设计的基本单元，一栋楼算一个覆盖对象。",
    "ZNRO": "机房（法式 Zone Réseau Optique）：放 OLT 等设备的房间，光信号的起点。",
    "ZPM": "人手孔：地下管线的检修与转接井，方便穿线和维护。",
    "机房": "放通信设备的房间（含 OLT），光信号从这里出发去往各楼栋。",
    "管线": "埋在地下的通信管道/光缆，基站、机房之间靠它连通。",
    "主干": "从机房到各光交箱的主光缆，容量大、距离长，是网络的“主干道”。",
    "入户": "从光交箱到每户家的最后一段光缆，即“最后一公里”。",
    "扇区": "一个基站天线能覆盖的扇形区域，通常 3 个扇区拼成 360° 全覆盖。",
    "覆盖缺口": "信号弱或没信号的区域（楼栋/路段），需要补基站来填补。",
    "缺口楼栋": "没被任何基站良好覆盖的楼，是补盲的优先目标。",
    "投诉密度": "某区域用户投诉信号差的数量多少，代表真实需求强弱。",
    "路测弱覆盖": "开车/步行实测发现信号差的地段，比投诉更客观。",
    "站间距": "相邻两个基站之间的距离，越小覆盖越好但成本越高。",
    "宏站": "大功率室外基站，覆盖几百米到几公里，是覆盖主力。",
    "微站": "小功率补盲基站，覆盖几十到几百米，专填宏站缝隙。",
    "室分": "室内分布系统：在商场/地铁等室内布天线，解决建筑内部信号差。",
    "频段": "电磁波的工作频率（如 2.6/3.5/4.9GHz），低频绕得远、高频容量大。",
    "制式": "通信技术标准代际，如 4G(LTE)、5G(NR)，覆盖与容量特性不同。",
    "AAU": "有源天线单元：5G 基站的集成化天线+射频设备。",
    "RRU": "远端射频单元：4G 基站的射频设备，配合天线一起用。",
    "容量": "一个基站能同时服务多少用户、提供多少流量。",
    "BOM": "物料清单（Bill of Materials）：建这个站要买哪些设备、各多少，用于采购和算钱。",
    "工程量": "实际要干多少活：挖多少米管道、放多少光缆、立多少塔。",
    "造价": "工程总成本（材料+施工+管理），用来做预算。",
    "CRS": "坐标参考系：告诉软件经纬度怎么投影到平面，不同 CRS 不能混用。",
    "投影": "把地球曲面展成平面地图的方法，国内常用 CGCS2000/高斯投影。",
    "拓扑": "网络里谁连谁的结构（基站-管线-机房怎么接）。",
    "蜂窝": "基站按六边形格状排布像蜂巢，是移动通信的经典布局方式。",
    "避让": "建站时要绕开的区域（文物、机场、高压线等），这些地方不能立塔。",
    "自检": "自动检查设计成果有没有明显错误（如异常要素、越界）。",
    "联动": "把现网数据和新建方案关联，点地图就能查某处属于哪类要素。",
    "GeoJSON": "一种用文本存地理坐标的格式，方便在不同软件间交换地图数据。",
    "M03后端": "本项目的服务端程序，负责存方案、跑 AI 报告等。",
    "出图": "把设计方案导出成标准图纸（PDF/图片），用于汇报或施工。",
    "RSRP": "参考信号接收功率：衡量手机收到信号强弱的指标(dBm)，数值越大信号越好。",
    "覆盖": "信号能到达、能正常上网的范围。",
    "矢量": "用点线面坐标表达的地图数据，放大不模糊。",
    "栅格": "用像素网格表达的地图数据（如卫星影像），放大后会糊。",
    "路测": "开车/步行用专业设备实地测量信号质量。",
    "演示投诉": "为演示“按需求选址”而合成的假投诉数据，真数据到位后替换即可。",
    "光路由": "光路由表：记录每根光缆从哪到哪的“走线清单”，施工与验收必备。",
    "光交箱汇总": "光交箱汇总：把所有光交箱的位置、容量列成一张表，方便清点。",
    "工程量报表": "把本次设计用到的所有材料数量、规格、造价汇总成表，用于采购与预算。",
    "基站设计": "基站设计：确定每个基站在哪、用什么塔型/天线/制式，是方案的核心成果。",
    "设计区域": "你在地图上框选的待建设范围，所有新建设施都落在这个矩形里。",
    "现网": "现网：已经建成在用的网络（FTTH 管线、机房等），补盲就是在此基础上补缺。",
    "缺口": "缺口：覆盖不到或信号差的地方，需要补设施来填补。",
    "基站": "基站：发射手机信号的铁塔/天线设备，是移动通信网络的“发射台”。",
    "蜂窝拓扑": "蜂窝拓扑：基站按六边形格状排布（像蜂巢），是经典覆盖布局方式。",
    "方案": "方案：一套完整的建设设计（建哪几个站、铺哪些管线、放哪些机房）。",
    "底图": "底图：地图上的背景影像/街道图，用来对照着摆放设施位置。",
    "运行环境": "运行环境：本插件依赖的后端服务与端口（拓扑引擎/LLM/地图源），用于排错。",
    "建设模式": "建设模式：两种打法——现网补盲（在已有网络上补缺）或新区新建（从零铺网）。",
    "生成布局": "生成布局：按算法自动排布一批基站的位置与参数，省去手工逐个摆。",
    "AI 报告": "AI 报告：让大模型读懂你的设计方案，自动写出一份带数据统计与建议的说明文档。",
    "自由框选": "自由框选：用鼠标在地图上拖一个矩形，框出你想建设的区域范围。",
    "解析需求": "解析需求：把老板/客户的一句话要求（如“某小区信号差”）自动转成可执行的参数。",
    "AI": "AI（人工智能）：这里指用大模型帮你解析需求、自动写设计报告。",
    "M03": "M03：本项目的服务端程序，负责存方案、跑 AI 报告等。",
}


def _build_term_tip(text):
    """从控件文本里找出所有命中的专业名词，拼成多行 tooltip。

    优先匹配更长的词（如“覆盖缺口”先于“覆盖”），避免被短词误伤。
    """
    if not text:
        return None
    found = []
    for key in sorted(GLOSSARY, key=len, reverse=True):
        if key in text and not any(key in f for f in found):
            found.append(key)
    if not found:
        return None
    return "\n".join("【%s】%s" % (k, GLOSSARY[k]) for k in found)


def apply_glossary_tips(root):
    """遍历 root 下所有文本类控件，凡含专业名词则挂上通俗解释 tooltip。

    仅在控件自身没有手动 tooltip 时生效，避免覆盖既有说明。
    """
    from qgis.PyQt.QtWidgets import (QLabel, QGroupBox, QPushButton,
                                     QRadioButton, QCheckBox)
    for w in root.findChildren((QLabel, QGroupBox, QPushButton,
                                QRadioButton, QCheckBox)):
        try:
            existing = w.toolTip()
        except Exception:
            continue
        if existing and existing.strip():
            continue  # 已有手动说明，跳过
        text = w.title() if isinstance(w, QGroupBox) else w.text()
        tip = _build_term_tip(text)
        if tip:
            try:
                w.setToolTip(tip)
            except Exception:
                pass

# 缩放滑块的尺度映射边界（比例尺分母）
ZOOM_SCALE_OUT = 5_000_000   # 滑块最左：最大缩小（看全局）
ZOOM_SCALE_IN = 100          # 滑块最右：最大放大（看细节）
ZOOM_SLIDER_MAX = 1000       # 滑块分辨率


def _new_qgs_field(name, qtype):
    """创建 QgsField，规避 QgsField(name, type) 旧构造在 QGIS 3.30+ 的弃用告警。

    旧写法 QgsField(name, QVariant.String) 在 QGIS 3.34 LTR 会打印 DeprecationWarning；
    改用默认构造 + setName/setType 的写法既不告警、也跨版本稳定。
    """
    f = QgsField()
    f.setName(name)
    f.setType(qtype)
    return f


# ==================== 统一视觉样式 ====================
# 颜色/字体统一抽离到 ui/dock_tokens.py（双主题 Token，根治左右面板级联污染）。
# 业务代码只调用 btn_qss() / group_style() / dark_panel_style() / light_panel_style()。
from ui.dock_tokens import (
    btn_qss, dark_panel_style, light_panel_style, group_style, LIGHT,
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
        self.ftth_design = None     # #5 Phase B：greenfield 合成 FTTH 设计产物

        # FTTH 画布符号化 / 异常高亮 / PDF 出图 状态
        self._ftth_layers = {}        # {层名: QgsVectorLayer}
        self._ftth_shape_dir = None   # 最近一次加载的 Shape 目录
        self._ftth_rubberbands = []   # 当前高亮 RubberBand 列表

        # S1 增强：覆盖缺口识别 + 智能建议站点（真实数据→设计输入）
        self._gap_rubberbands = []        # 缺口楼栋红框
        self._suggested_sites_layer = None  # 建议站点内存图层

        # 联动查询（FTTH ↔ 基站/管线/机房）状态
        self._linkage_tool = None
        self._linkage_rubberbands = []  # 联动高亮 RubberBand 列表
        self._linkage_active = False

        # 建设模式（③→① 增强）：现网补盲(brownfield) / 新区新建(greenfield)
        # brownfield = 插件默认，FTTH 为固定现网基线；greenfield = FTTH 变为可设计输出
        self._build_mode = "brownfield"
        self._mode_combo = None
        self._ftth_load_btn = None
        self._mode_note_label = None
        # ② 增强：FTTH 锚点 ↔ 机房 硬关联映射（served_room_id）
        # key = FTTH 锚点 id（SITE 的 CODE / PM 引用），value = MachineRoom.room_id
        self._assoc_mode = "label"  # label=标注机房名(默认) / line=橙色关联线
        self._ftth_room_map = {}

        # 首次使用引导 + 步骤完成态（P0-#3 / P1-#6）
        self._step_states = ["pending"] * 9   # pending / active / done
        # 撤销/重做栈（P2-#9）：每个元素是一个可执行的「撤销」闭包
        self._undo_stack = []

        # 布局结果来源标记（引擎 / 本地兜底），用于向用户透明展示
        self._layout_source = None

        # 模式持久化（P2-#10）：记住上次选择的建设模式
        self._qsettings = QSettings("xind2", "qgis-plugin-design")

        # 数据同步（URL 与 API Key 从环境变量 M03_API_URL / M03_API_KEY 读取，支持 HTTPS 与内部鉴权）
        self.sync_engine = DataSync(
            api_url=os.environ.get("M03_API_URL"),
            api_key=os.environ.get("M03_API_KEY"),
        )
        # 拓扑引擎设备清单（第六步生成，第九步报表复用）
        self._device_layout = []

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
        main.setStyleSheet("")  # 全局样式不再挂到最外层，改由左右面板各自作用域样式接管

        # 左侧菜单栏 —— 步骤指示器（高对比度：每步都是独立卡片）
        left_panel = QWidget()
        left_panel.setFixedWidth(124)
        left_panel.setStyleSheet(dark_panel_style())
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(6)
        left_layout.setContentsMargins(8, 12, 8, 12)

        # 标题 + 进度条
        title = QLabel("通信设施\n智能设计")
        title.setStyleSheet("color:#ffffff;font-size:13px;font-weight:800;padding:2px 6px;line-height:1.35;")
        left_layout.addWidget(title)

        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 9)
        self.step_progress.setValue(1)
        self.step_progress.setTextVisible(False)
        self.step_progress.setFixedHeight(4)
        self.step_progress.setStyleSheet(
            "QProgressBar{background:#1e293b;border:none;border-radius:3px;}"
            "QProgressBar::chunk{background:#2f6df6;border-radius:3px;}"
        )
        left_layout.addWidget(self.step_progress)

        # 建设模式开关（① 增强）：现网补盲 / 新区新建
        mode_group = QGroupBox("建设模式")
        mode_group.setStyleSheet(
            "QGroupBox{font-size:13px;font-weight:700;color:#f1f5f9;"
            "border:1px solid #475569;border-radius:8px;margin-top:12px;padding-top:8px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;color:#f1f5f9;}"
        )
        mode_layout = QVBoxLayout()
        mode_layout.setSpacing(8)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["现网补盲（固定 FTTH）", "新区新建（规划中）"])
        self._mode_combo.setMinimumHeight(36)
        self._mode_combo.setStyleSheet(
            "QComboBox{font-size:13px;font-weight:600;padding:4px 8px;}"
            "QComboBox::drop-down{border:none;width:24px;}"
            "QComboBox QAbstractItemView{font-size:12px;}"
        )
        self._mode_combo.setToolTip(
            "现网补盲：区域已有 FTTH 竣工数据，先加载找缺口再补建设施；\n"
            "新区新建：目标区为空地，先建机房→铺管线→再生成 FTTH 设计（机房先行）"
        )
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self._mode_combo)
        # 标签文字用 HTML 内联 color 显式白色——在深色左面板下始终可读，
        # 不再依赖 ID 选择器 / QPalette 双重保险（双主题作用域已根治级联问题）。
        mode_tip = QLabel(
            "<p style='margin:0;color:#ffffff;font-size:14px;'>"
            "<b style='color:#ffffff;'>● 现网补盲：</b>"
            "<span style='color:#ffffff;'>加载FTTH → 找缺口 → 补设施</span></p>"
            "<p style='margin:4px 0 0 0;color:#ffffff;font-size:14px;'>"
            "<b style='color:#ffffff;'>● 新区新建：</b>"
            "<span style='color:#ffffff;'>建机房 → 铺管线 → 生成FTTH</span></p>"
        )
        mode_tip.setWordWrap(True)
        mode_layout.addWidget(mode_tip)
        mode_group.setLayout(mode_layout)
        left_layout.addWidget(mode_group)

        # ① 增强：新区新建模式标注横幅（#5 Phase B 已实现由机房+管线自动生成 FTTH 设计）
        self._greenfield_banner = QLabel(
            "新区新建：先布置机房(OLT 锚点) + 框选设计区域 + 铺管线，"
            "再点下方『生成 FTTH 设计』自动合成 OLT→分光→入户 设计（示意）。第②/③步已禁用。"
        )
        self._greenfield_banner.setWordWrap(True)
        self._greenfield_banner.setStyleSheet(
            "background-color:#fff7ed;border:1px solid #fdba74;border-radius:6px;"
            "color:#9a3412;font-size:11px;padding:8px 10px;line-height:1.5;"
        )
        self._greenfield_banner.setVisible(False)
        left_layout.addWidget(self._greenfield_banner)

        # #5 Phase B：greenfield 专用「生成 FTTH 设计」按钮（brownfield 隐藏）
        self._gen_ftth_btn = QPushButton("生成 FTTH 设计（机房+管线）")
        self._gen_ftth_btn.setStyleSheet(btn_qss("accent"))
        self._gen_ftth_btn.setToolTip(
            "greenfield 模式：先布置机房（OLT 锚点）并框选设计区域、铺管线，"
            "再点此自动合成 OLT→分光→入户 的 FTTH 设计（示意性产物，非竣工依据）。"
        )
        self._gen_ftth_btn.clicked.connect(self._on_generate_ftth_design)
        self._gen_ftth_btn.setVisible(False)
        left_layout.addWidget(self._gen_ftth_btn)

        # 步骤按钮（严格按 S1 操作流程 9 步，从上到下）
        self.step_buttons = []
        steps = ["环境·底图", "FTTH现网", "覆盖缺口", "设计区域", "基站参数",
                 "生成布局", "管线·场景", "自检·联动", "出图·交付"]
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

        # 右侧内容区（可滚动）—— 浅色主题作用域样式，仅作用于本面板
        right_panel = QWidget()
        right_panel.setStyleSheet(light_panel_style())
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # 地图缩放控制（常驻，任何步骤可用）：放大 / 缩小 / 全图 + 精确比例尺输入
        self._zoom_group = self._build_zoom_control()
        right_layout.addWidget(self._zoom_group)

        # 首次使用引导条（P0-#3）：常驻于当前步骤上方，给出下一步建议
        self._guidance_label = QLabel("")
        self._guidance_label.setWordWrap(True)
        self._guidance_label.setStyleSheet(
            "background-color:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;"
            "color:#1e40af;font-size:12px;padding:8px 10px;line-height:1.5;"
        )
        right_layout.addWidget(self._guidance_label)

        # 创建各个步骤页面（严格对应 S1 操作流程 9 步）
        self.step_pages = {
            0: self._build_step1(),   # ① 环境·底图
            1: self._build_step2(),   # ② FTTH 现网
            2: self._build_step3(),   # ③ 覆盖缺口
            3: self._build_step4(),   # ④ 设计区域
            4: self._build_step5(),   # ⑤ 基站参数
            5: self._build_step6(),   # ⑥ 生成布局
            6: self._build_step7(),   # ⑦ 管线·场景
            7: self._build_step8(),   # ⑧ 自检·联动
            8: self._build_step9(),   # ⑨ 出图·交付
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

        # 用 QScrollArea 包裹右侧面板，解决内容过长时底部按钮被截断的问题
        scroll_area = QScrollArea()
        self.scroll_area = scroll_area
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(right_panel)
        # 去掉滚动区域的边框，与左侧菜单视觉统一
        scroll_area.setStyleSheet("QScrollArea{border:none;background-color:transparent;}")
        # 水平滚动条：内容超出时自动出现（避免右侧文字/按钮被截断）
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_layout.addWidget(scroll_area)

        self.setWidget(main)

        # 面板最小宽度，避免窄屏下按钮文字被截断（P2-#11）
        self.setMinimumWidth(380)

        # 恢复上次选择的建设模式（P2-#10）
        saved_mode = self._qsettings.value("build_mode", 0, type=int)
        if saved_mode in (0, 1) and saved_mode != self._mode_combo.currentIndex():
            self._mode_combo.setCurrentIndex(saved_mode)

        # 撤销快捷键 Ctrl+Z（P2-#9）
        self._undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self._undo_shortcut.activated.connect(self._undo)

        # 给所有含专业名词的控件挂上通俗解释（鼠标悬停显示）
        apply_glossary_tips(self)

        # 默认显示第一步
        self._switch_step(0)

    # ────────────────────────────────────────────────
    #  地图缩放控制（常驻右侧顶部，任何步骤可用）
    # ────────────────────────────────────────────────
    def _build_zoom_control(self):
        """构建地图缩放控制组：滚动条式滑块（拖拽即缩放）+ 放大/缩小/全图 + 精确比例尺输入。"""
        self._zoom_suppress = False  # 防止「地图→滑块」反向同步触发再缩放

        group = QGroupBox("地图缩放")
        group.setStyleSheet(group_style())
        layout = QVBoxLayout()

        # 第一行：缩小 −  [====滑块====]  + 放大（滚动条样式）
        slider_row = QHBoxLayout()
        btn_out = QPushButton("−")
        btn_out.setFixedWidth(28)
        btn_out.setStyleSheet(btn_qss("default"))
        btn_out.setToolTip("缩小地图（相当于鼠标滚轮向后）")
        btn_out.clicked.connect(self._zoom_out)
        slider_row.addWidget(btn_out)

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(0, ZOOM_SLIDER_MAX)
        self._zoom_slider.setTickPosition(QSlider.TicksBelow)
        self._zoom_slider.setTickInterval(ZOOM_SLIDER_MAX // 10)
        self._zoom_slider.setToolTip(
            "拖动滑块缩放地图：向右拖 = 放大（看细节），向左拖 = 缩小（看全局）。\n"
            "也可用鼠标滚轮或在地图上框选缩放。"
        )
        self._zoom_slider.valueChanged.connect(self._on_slider_value_changed)
        slider_row.addWidget(self._zoom_slider, 1)

        btn_in = QPushButton("+")
        btn_in.setFixedWidth(28)
        btn_in.setStyleSheet(btn_qss("primary"))
        btn_in.setToolTip("放大地图（相当于鼠标滚轮向前）")
        btn_in.clicked.connect(self._zoom_in)
        slider_row.addWidget(btn_in)
        layout.addLayout(slider_row)

        # 第二行：全图 + 精确比例尺输入 + 跳转
        precise_row = QHBoxLayout()
        btn_full = QPushButton("全图")
        btn_full.setStyleSheet(btn_qss("teal"))
        btn_full.setToolTip("缩放到所有图层的整体范围")
        btn_full.clicked.connect(self._zoom_full)
        precise_row.addWidget(btn_full)

        precise_row.addWidget(QLabel("精确:"))
        self._scale_edit = QLineEdit()
        self._scale_edit.setPlaceholderText("如 5000 = 1:5000")
        self._scale_edit.setFixedWidth(72)
        self._scale_edit.setValidator(QIntValidator(1, 100000000))
        self._scale_edit.setToolTip(
            "输入比例尺分母（整数）后点「跳转」，地图将精确缩放到该比例尺。\n"
            "例如输入 5000 即 1:5000，输入 50000 即 1:50000。"
        )
        precise_row.addWidget(self._scale_edit)
        btn_go = QPushButton("跳转")
        btn_go.setStyleSheet(btn_qss("accent"))
        btn_go.clicked.connect(self._zoom_to_scale)
        precise_row.addWidget(btn_go)
        layout.addLayout(precise_row)

        # 当前比例尺显示（随地图缩放实时更新）
        self._scale_label = QLabel("当前比例尺: —")
        self._scale_label.setStyleSheet("color:#64748b;font-size:11px;")
        layout.addWidget(self._scale_label)

        group.setLayout(layout)

        # 监听画布比例尺变化（滚轮/拖拽/跳转缩放时也同步滑块与文字）
        try:
            self.iface.mapCanvas().scaleChanged.connect(
                lambda *_: self._sync_zoom_from_map()
            )
        except Exception:
            pass
        self._sync_zoom_from_map()
        return group

    # —— 滑块 ↔ 比例尺 的映射（对数尺度，拖拽手感线性）——
    def _slider_to_scale(self, pos):
        t = pos / ZOOM_SLIDER_MAX
        log_s = (math.log10(ZOOM_SCALE_OUT)
                 + (math.log10(ZOOM_SCALE_IN) - math.log10(ZOOM_SCALE_OUT)) * t)
        return 10 ** log_s

    def _scale_to_slider(self, scale):
        if not scale or scale <= 0:
            return 0
        t = ((math.log10(scale) - math.log10(ZOOM_SCALE_OUT))
             / (math.log10(ZOOM_SCALE_IN) - math.log10(ZOOM_SCALE_OUT)))
        return int(round(max(0.0, min(1.0, t)) * ZOOM_SLIDER_MAX))

    def _apply_slider_zoom(self, pos):
        canvas = self.iface.mapCanvas()
        canvas.zoomScale(float(self._slider_to_scale(pos)))
        canvas.refresh()
        self._update_scale_label()

    def _on_slider_value_changed(self, pos):
        # 程序反向同步地图→滑块时（_zoom_suppress=True）不触发缩放，只更新文字
        if self._zoom_suppress:
            self._update_scale_label()
            return
        self._apply_slider_zoom(pos)

    def _sync_zoom_from_map(self):
        """地图被其他方式缩放后，把滑块位置同步过去（不触发再缩放）。"""
        canvas = self.iface.mapCanvas()
        scale = canvas.scale()
        if not scale or scale <= 0:
            self._update_scale_label()
            return
        pos = self._scale_to_slider(scale)
        self._zoom_suppress = True
        try:
            self._zoom_slider.setValue(pos)
        finally:
            self._zoom_suppress = False
        self._update_scale_label()

    def _zoom_in(self):
        canvas = self.iface.mapCanvas()
        canvas.zoomIn()
        canvas.refresh()

    def _zoom_out(self):
        canvas = self.iface.mapCanvas()
        canvas.zoomOut()
        canvas.refresh()

    def _zoom_full(self):
        canvas = self.iface.mapCanvas()
        canvas.zoomToFullExtent()
        canvas.refresh()

    def _zoom_to_scale(self):
        """按输入框中的比例尺分母精确缩放（如 5000 → 1:5000）。"""
        canvas = self.iface.mapCanvas()
        try:
            denom = int(self._scale_edit.text().strip())
        except ValueError:
            self._log("请输入有效的整数比例尺（如 5000）")
            return
        if denom <= 0:
            self._log("比例尺必须大于 0")
            return
        # zoomScale 接受的是分母；避免极端值导致画布崩溃
        canvas.zoomScale(float(denom))
        canvas.refresh()
        self._update_scale_label()
        self._log(f"已精确缩放到 1:{denom:,}")

    def _update_scale_label(self):
        canvas = self.iface.mapCanvas()
        try:
            scale = canvas.scale()
            if scale and scale > 0:
                self._scale_label.setText(f"当前比例尺: 1:{scale:,.0f}")
            else:
                self._scale_label.setText("当前比例尺: —")
        except Exception:
            pass

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

        # 标记当前步为「进行中」（尚未完成才改）
        if self._step_states[step_index] == "pending":
            self._step_states[step_index] = "active"
        self._refresh_step_nav()

        # 切换后滚动回顶部，保证每一步都从标题开始看
        sa = getattr(self, "scroll_area", None)
        if sa is not None:
            try:
                sa.verticalScrollBar().setValue(0)
            except Exception:
                pass


    def _refresh_step_nav(self):
        """根据步骤完成态启用/禁用步骤按钮，并刷新引导条文案。"""
        green = self._build_mode == "greenfield"
        for i, btn in enumerate(self.step_buttons):
            if green and i in (1, 2):
                btn.setEnabled(False)        # 新区新建下 FTTH 加载/缺口分析无意义
                continue
            if i == 0:
                btn.setEnabled(True)
                continue
            prev_done = self._step_states[i - 1] in ("done", "active")
            btn.setEnabled(prev_done or self._step_states[i] == "done")
        self._update_guidance()

    def _mark_step_done(self, idx):
        """标记某步为已完成，并刷新导航/引导。"""
        if 0 <= idx < len(self._step_states):
            self._step_states[idx] = "done"
        self._refresh_step_nav()

    def _update_guidance(self):
        """根据步骤完成态 + 建设模式给出『下一步建议』引导文案。"""
        if self._guidance_label is None:
            return
        green = self._build_mode == "greenfield"
        # brownfield：现网补盲流程（FTTH 先加载为基线）
        tips_brownfield = {
            0: "第一步：添加底图（天地图影像/注记 / Esri 卫星 / OSM），确定设计区域范围。",
            1: "已就绪 → 加载 FTTH 现网数据作为设计底数。",
            2: "已加载现网 → 运行「覆盖缺口识别」找出需补盲的楼栋。",
            3: "已识别缺口 → 在第④步框选设计区域。",
            4: "已框选区域 → 设置基站参数并生成布局。",
            5: "已生成布局 → 在第⑥步布置管线与场景。",
            6: "已布置管线 → 在自检步骤做 FTTH ↔ 新建设施联动查询。",
            7: "已联动核查 → 进入出图·交付导出交付物。",
            8: "全部完成，可导出 PDF / 光路由表 / 工程量报表。",
        }
        # greenfield：新区新建流程（FTTH 为设计产物，第②③步跳过）
        tips_greenfield = {
            0: "第一步：添加底图（天地图影像/注记 / Esri 卫星 / OSM），确定设计区域范围。",
            1: "（新区新建模式下，本步已禁用）→ 请直接进入第三步框选区域。",
            2: "（新区新建模式下，本步已禁用）→ FTTH 将由后续步骤自动生成。",
            3: "已就绪 → 在第④步框选设计区域（新区新建的画布）。",
            4: "已框选区域 → 先添加机房（OLT 锚点），再设置基站参数并生成布局。",
            5: "已生成布局 → 布置管线，然后点击「生成 FTTH 设计」合成光接入网络。",
            6: "已布置管线 + FTTH 已生成 → 自检步骤做联动核查。",
            7: "已联动核查 → 进入出图·交付导出交付物。",
            8: "全部完成，可导出 PDF / 光路由表 / 工程量报表 / FTTH 竣工图。",
        }
        tips = tips_greenfield if green else tips_brownfield
        next_idx = next((i for i, s in enumerate(self._step_states) if s != "done"), None)
        if next_idx is None:
            self._guidance_label.setText("全流程已完成，可进入第⑨步导出交付物。")
        else:
            self._guidance_label.setText("下一步建议：" + tips.get(next_idx, "继续下一步操作。"))

    def _set_status(self, text, busy=False):
        """统一更新状态栏 + 进度条（P1-#4 加载/错误反馈）。"""
        if hasattr(self, "status_label"):
            self.status_label.setText(text)
        if hasattr(self, "progress"):
            if busy:
                self.progress.setVisible(True)
                self.progress.setRange(0, 0)      # 不确定进度（忙指示）
            else:
                self.progress.setVisible(False)
                self.progress.setRange(0, 1)
                self.progress.setValue(1)

    # ────────────────────────────────────────────────
    #  9 步向导：通用小组件
    # ────────────────────────────────────────────────
    _STEP_TITLES = [
    "环境·底图", "FTTH 现网", "覆盖缺口识别", "设计区域", "基站参数",
    "生成布局", "管线·场景", "自检·联动", "出图·交付",
]


    def _step_header(self, layout, idx, desc):
        """统一的步骤标题 + 说明（idx 从 0 开始）"""
        title = QLabel(f"第 {idx + 1} 步 · {self._STEP_TITLES[idx]}")
        title.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{LIGHT['text_title']};"
            f"padding:6px 4px;border-left:4px solid {LIGHT['header_border']};"
        )
        layout.addWidget(title)

        if desc:
            lbl = QLabel(desc)
            lbl.setStyleSheet(f"color:{LIGHT['text_muted']};font-size:11px;padding-left:6px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

    def _nav_row(self, layout, idx):
        """页面底部的『上一步 / 下一步』导航"""
        row = QHBoxLayout()
        if idx > 0:
            prev_btn = QPushButton("← 上一步")
            prev_btn.setStyleSheet(btn_qss("default"))
            prev_btn.setToolTip(f"返回第 {idx} 步 · {self._STEP_TITLES[idx - 1]}")
            prev_btn.clicked.connect(lambda: self._switch_step(idx - 1))
            row.addWidget(prev_btn)
        row.addStretch()
        if idx < len(self._STEP_TITLES) - 1:
            next_btn = QPushButton("下一步 →")
            next_btn.setStyleSheet(btn_qss("primary"))
            next_btn.setToolTip(f"进入第 {idx + 2} 步 · {self._STEP_TITLES[idx + 1]}")
            next_btn.clicked.connect(lambda: self._switch_step(idx + 1))
            row.addWidget(next_btn)
        layout.addLayout(row)

    # ────────────────────────────────────────────────
    #  ① 环境·底图
    # ────────────────────────────────────────────────
    def _build_step1(self):
        """① 起环境 + 加载底图"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 0,
            "先确认后端服务已启动（M03 :8083 / 拓扑引擎 :9001 / LLM :9002），"
            "再选择一张底图。国内数据推荐「天地图影像」，摩洛哥真实数据可用 Esri 卫星图。"
        )

        # 底图按钮
        base_group = QGroupBox("底图源")
        base_group.setStyleSheet(group_style())
        base_layout = QVBoxLayout()

        # 底图源：下拉选择 + 一个“添加底图”按钮（合并原 4 个独立按钮）
        base_row = QHBoxLayout()
        self.basemap_combo = QComboBox()
        self.basemap_combo.addItems(BASEMAP_SOURCES)
        saved_basemap = self._qsettings.value("basemap_index", 0, type=int)
        if 0 <= saved_basemap < len(BASEMAP_SOURCES):
            self.basemap_combo.setCurrentIndex(saved_basemap)
        else:
            self.basemap_combo.setCurrentIndex(0)
        base_row.addWidget(self.basemap_combo, 1)

        btn_add_base = QPushButton("添加底图")
        btn_add_base.setStyleSheet(btn_qss("primary"))
        btn_add_base.setToolTip("在下拉中选择底图源（国内推荐天地图影像，全球可用 Esri），点击加载到地图。")
        btn_add_base.clicked.connect(self._add_selected_basemap)
        base_row.addWidget(btn_add_base)
        base_layout.addLayout(base_row)

        base_group.setLayout(base_layout)
        layout.addWidget(base_group)

        # 环境检查提示
        env_group = QGroupBox("运行环境")
        env_group.setStyleSheet(group_style())
        env_layout = QVBoxLayout()
        env_tip = QLabel(
            "· M03 后端      http://localhost:8083   （方案保存 / 同步）\n"
            "· 拓扑引擎      http://localhost:9001   （扇区覆盖 + 设备清单）\n"
            "· LLM 服务      http://localhost:9002   （AI 解析 / AI 报告）\n"
            "未启动也可用：插件会自动回落到本地算法，仅 AI 相关功能不可用。"
        )
        env_tip.setStyleSheet("color:#475569;font-size:11px;")
        env_tip.setWordWrap(True)
        env_layout.addWidget(env_tip)
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)

        layout.addStretch()
        self._nav_row(layout, 0)

        return page

    # ────────────────────────────────────────────────
    #  ② FTTH 现网
    # ────────────────────────────────────────────────
    def _build_step2(self):
        """② 加载真实 FTTH 现网数据"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 1,
            "加载主办方提供的摩洛哥 FTTH 竣工数据（Plan de récolement），"
            "按官方图例符号化后作为本次设计的『现网底数』。"
        )

        # ① 增强：模式切换提示标签
        self._mode_note_label = QLabel("")
        self._mode_note_label.setStyleSheet(
            "background-color:#ecfeff;border:1px solid #7dd3fc;border-radius:6px;"
            "color:#0c4a6e;font-size:13px;padding:10px 12px;line-height:1.5;"
        )
        self._mode_note_label.setWordWrap(True)
        layout.addWidget(self._mode_note_label)
        self._update_mode_note()

        ftth_group = QGroupBox("现网数据")
        ftth_group.setStyleSheet(group_style())
        ftth_layout = QVBoxLayout()

        btn_ftth_load = QPushButton("加载并符号化 FTTH 图层")
        btn_ftth_load.setStyleSheet(btn_qss("teal"))
        btn_ftth_load.setToolTip("读取 IMB / SITE / BOITE / CABLE / PTECH / "
                                 "INFRASTRUCTURE / ZNRO / ZPM 共 8 类图层并套用官方符号")
        btn_ftth_load.clicked.connect(self._load_ftth_layers)
        self._ftth_load_btn = btn_ftth_load
        ftth_layout.addWidget(btn_ftth_load)

        legend = QLabel(
            "图层含义：\n"
            "· IMB    需要接入光纤的楼栋（设计目标）\n"
            "· SITE   NRO / 局端站点\n"
            "· BOITE  光交箱 / 分纤箱\n"
            "· CABLE  已敷设光缆路由\n"
            "· PTECH  技术点位（人手孔、杆路等）\n"
            "· ZNRO / ZPM  NRO、PM 的服务覆盖区（缺口分析的依据）"
        )
        legend.setStyleSheet("color:#475569;font-size:11px;")
        legend.setWordWrap(True)
        legend.setToolTip(
            "术语对照（法语缩写）：\n"
            "IMB = Immeuble（楼栋，待接入光纤的设计目标）\n"
            "SITE = 局端 / NRO 站点\n"
            "NRO = Nœud de Raccordement Optique（光分配节点）\n"
            "BOITE = 光交箱 / 分纤箱\n"
            "CABLE = 已敷设光缆路由\n"
            "PTECH = Point Technique（技术点位：人手孔、杆路等）\n"
            "ZNRO = Zone NRO（NRO 服务覆盖区）\n"
            "ZPM = Zone PM（Point de Mutualisation 共享点覆盖区）\n"
            "PBO = Point de Branchement Optique（光分纤点）\n"
            "BPE = Boîtier de Points d'Entrée（入户光终端箱）"
        )
        ftth_layout.addWidget(legend)

        ftth_group.setLayout(ftth_layout)
        layout.addWidget(ftth_group)

        layout.addStretch()
        self._nav_row(layout, 1)

        return page

    # ────────────────────────────────────────────────
    #  ③ 覆盖缺口识别
    # ────────────────────────────────────────────────
    def _build_step3(self):
        """③ 覆盖缺口识别 → 智能建议站点"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 2,
            "把 ZNRO ∪ ZPM 合成现网覆盖面，逐个判断 IMB 楼栋是否落在覆盖内；"
            "未覆盖的楼栋会被红圈标出，并按 400m 网格聚类成建议新建站点。"
        )

        gap_group = QGroupBox("缺口分析")
        gap_group.setStyleSheet(group_style())
        gap_layout = QVBoxLayout()

        btn_gap = QPushButton("覆盖缺口识别 · 智能建议站点")
        btn_gap.setStyleSheet(btn_qss("accent"))
        btn_gap.setToolTip("读取 ZNRO/ZPM 覆盖区，找出未覆盖的 IMB 楼栋，"
                           "并智能建议在缺口处新增 NRO 候选站点")
        btn_gap.clicked.connect(self._on_coverage_gap)
        gap_layout.addWidget(btn_gap)

        btn_gap_clear = QPushButton("清除本步成果(缺口)")
        btn_gap_clear.setStyleSheet(btn_qss("danger"))
        btn_gap_clear.setToolTip("清除覆盖缺口标记与建议站点图层（本步成果）。")
        btn_gap_clear.clicked.connect(self._on_clear_gap)
        gap_layout.addWidget(btn_gap_clear)

        # ── S1 #1：需求加权（结合投诉/路测，可选）──
        fb_label = QLabel("需求加权（结合投诉/路测，可选）：")
        fb_label.setStyleSheet("color:#0f766e;font-size:12px;font-weight:bold;")
        gap_layout.addWidget(fb_label)

        w_row = QHBoxLayout()
        w_row.addWidget(QLabel("w1 缺口楼栋"))
        self.w1_spin = QDoubleSpinBox()
        self.w1_spin.setRange(0.0, 1.0)
        self.w1_spin.setSingleStep(0.05)
        self.w1_spin.setValue(0.5)
        self.w1_spin.setDecimals(2)
        w_row.addWidget(self.w1_spin)
        w_row.addWidget(QLabel("w2 投诉密度"))
        self.w2_spin = QDoubleSpinBox()
        self.w2_spin.setRange(0.0, 1.0)
        self.w2_spin.setSingleStep(0.05)
        self.w2_spin.setValue(0.3)
        self.w2_spin.setDecimals(2)
        w_row.addWidget(self.w2_spin)
        w_row.addWidget(QLabel("w3 路测弱覆盖"))
        self.w3_spin = QDoubleSpinBox()
        self.w3_spin.setRange(0.0, 1.0)
        self.w3_spin.setSingleStep(0.05)
        self.w3_spin.setValue(0.2)
        self.w3_spin.setDecimals(2)
        w_row.addWidget(self.w3_spin)
        w_row.addStretch()
        gap_layout.addLayout(w_row)

        # ── 高级 / 演示（评委演示用，默认折叠，移出主流程）──
        demo_group = QGroupBox("高级 / 演示（评委演示用）")
        demo_group.setCheckable(True)
        demo_group.setChecked(False)
        demo_group.setStyleSheet(group_style())
        demo_layout = QVBoxLayout()
        demo_tip = QLabel(
            "以下为挑战杯演示辅助功能：在已加载的 IMB 楼栋坐标系内\n"
            "合成『投诉点』与『路测弱覆盖』图层，用于演示「需求评分选址」。\n"
            "真实数据到位后替换即可，不影响正式设计流程。")
        demo_tip.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        demo_tip.setWordWrap(True)
        demo_layout.addWidget(demo_tip)
        btn_gen_fb = QPushButton("生成演示投诉/路测数据")
        btn_gen_fb.setStyleSheet(btn_qss("default"))
        btn_gen_fb.setToolTip("在 IMB 楼栋坐标系内合成『投诉点』与『路测弱覆盖』图层，"
                               "用于演示「需求评分选址」。若第②步未加载 IMB，会自动生成"
                               "虚拟楼栋兜底；真实数据到位后替换 COMPLAINT/ROADTEST 即可。")
        btn_gen_fb.clicked.connect(self._on_gen_demo_feedback)
        demo_layout.addWidget(btn_gen_fb)
        demo_group.setLayout(demo_layout)
        gap_layout.addWidget(demo_group)

        gap_tip = QLabel(
            "输出：① 红圈标出的未覆盖 IMB；② 内存图层「建议新建站点」，\n"
            "含 id / 经纬度 / 关联楼栋数 / 需求容量，可直接作为第 4~6 步的设计输入。"
        )
        gap_tip.setStyleSheet("color:#475569;font-size:11px;")
        gap_tip.setWordWrap(True)
        gap_layout.addWidget(gap_tip)

        gap_group.setLayout(gap_layout)
        layout.addWidget(gap_group)

        layout.addStretch()
        self._nav_row(layout, 2)

        return page

    # ────────────────────────────────────────────────
    #  ④ 设计区域
    # ────────────────────────────────────────────────
    def _build_step4(self):
        """④ 框选本次设计区域"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 3,
            "按住左键拖拽框选任意区域（无需先缩放）。建议直接框住第 3 步"
            "红圈聚集的缺口区，让设计范围对准真实需求。"
        )

        # ③ 增强：机房先行原则 UI 引导横幅
        room_first = QLabel(
            "机房先行提示：完成本步框选后，请先到第 ⑦ 步「管线·场景」布置机房，"
            "再生成管线与基站。机房是供电/设备/回传的共同落点，FTTH 与基站都挂在机房锚点上——"
            "真实建设里通常先在目标区域建机房，再想其他的。"
        )
        room_first.setStyleSheet(
            "background-color:#fff7ed;border:1px solid #fdba74;border-radius:6px;"
            "color:#9a3412;font-size:13px;padding:10px 12px;line-height:1.5;"
        )
        room_first.setWordWrap(True)
        layout.addWidget(room_first)

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
        self._nav_row(layout, 3)

        return page

    # ────────────────────────────────────────────────
    #  ⑤ 基站参数
    # ────────────────────────────────────────────────
    def _build_step5(self):
        """⑤ 设置基站参数（含 AI 自然语言解析）"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 4,
            "选一个预设方案自动填参，或用 AI 解析一句话需求；也可逐项手动微调。"
        )

        # ── 预设方案快捷选择 ──
        preset_group = QGroupBox("预设方案")
        preset_group.setStyleSheet(group_style())
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

        # ── #5 技术轴：通信技术制式（4G/5G）──
        self.tech_combo = QComboBox()
        self.tech_combo.addItems([
            "4G LTE", "5G NR(Sub-6)", "5G NR(mmWave)", "4G+5G协同",
        ])
        self.tech_combo.setCurrentText("4G+5G协同")  # 默认 = 与现状一致，零破坏
        self.tech_combo.setToolTip(
            "通信技术制式：选定制式会预选合理默认频段并给出单站容量/塔桅形态建议；"
            "仍可在上方手动微调频段。覆盖半径与站间距由频段驱动。"
        )
        self.tech_combo.currentTextChanged.connect(self._on_tech_changed)
        form.addRow("通信技术制式:", self.tech_combo)

        self.tech_info_label = QLabel("")
        self.tech_info_label.setStyleSheet("color:#64748b;font-size:11px;")
        form.addRow("", self.tech_info_label)

        layout.addLayout(form)

        # ── AI 大模型辅助 ──
        ai_group = QGroupBox("AI 智能辅助")
        ai_group.setStyleSheet(group_style())
        ai_layout = QVBoxLayout()
        btn_ai_parse = QPushButton("AI 解析需求（自然语言）")
        btn_ai_parse.setStyleSheet(btn_qss("accent"))
        btn_ai_parse.clicked.connect(self._open_ai_parse_dialog)
        ai_layout.addWidget(btn_ai_parse)
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)

        layout.addStretch()
        self._nav_row(layout, 4)

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

    def _on_tech_changed(self, tech_str):
        """#5 技术轴：选定制式 → 预选默认频段 + 刷新容量/塔桅提示。

        不强制覆盖用户已手动选的频段（仅当频段不在可选范围或从未被用户改动时预选）。
        这里采用「预选默认频段」策略：切换制式即同步 band_combo 到该制式推荐频段，
        用户仍可随后手动微调——与预设方案的写法一致，零破坏现网补盲演示。
        """
        band = default_band_for(tech_str)
        base = get_baseline(tech_str)
        # 同步频段（与 _on_preset_changed 同样避免信号循环）
        self.band_combo.blockSignals(True)
        try:
            if band in [self.band_combo.itemText(i) for i in range(self.band_combo.count())]:
                self.band_combo.setCurrentText(band)
                self._on_band_changed(band)
        finally:
            self.band_combo.blockSignals(False)

        if base is not None and self.tech_info_label is not None:
            self.tech_info_label.setText(
                f"覆盖半径≈{base.coverage_radius_km:.2f}km · 站间距≈{base.suggested_spacing_km:.2f}km · "
                f"单站容量参考 {base.capacity_ref:.0f} · {base.tower_form}"
            )
        self._log(f"通信技术制式: {tech_str}（建议频段 {band}）")

    # ────────────────────────────────────────────────
    #  ⑥ 生成布局
    # ────────────────────────────────────────────────
    def _build_step6(self):
        """⑥ 一键生成基站布局"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 5,
            "按第 5 步参数在框选区内自动排布蜂窝站点；也可调用后端拓扑引擎"
            "生成扇区覆盖 + 设备清单。生成后可手动增删、加载避让数据。"
        )

        # 生成基站布局（优先拓扑引擎，无后端时本地六边形兜底）
        btn_generate = QPushButton("生成基站布局")
        btn_generate.setStyleSheet(btn_qss("warn"))
        btn_generate.setToolTip(
            "按第 5 步参数在框选区内自动排布蜂窝站点。\n"
            "优先调用后端拓扑引擎（扇区覆盖+设备清单）；\n"
            "若后端未启动，则自动改用本地六边形布局兜底。")
        btn_generate.clicked.connect(self._generate_layout)
        layout.addWidget(btn_generate)

        # 手动添加
        btn_row = QHBoxLayout()

        self.add_station_btn = QPushButton("手动添加基站")
        self.add_station_btn.setCheckable(True)
        self.add_station_btn.setStyleSheet(btn_qss("default"))
        self.add_station_btn.clicked.connect(self._toggle_add_station)
        btn_row.addWidget(self.add_station_btn)

        layout.addLayout(btn_row)

        # 避让
        avoid_row = QHBoxLayout()
        btn_avoid = QPushButton("加载避让数据")
        btn_avoid.setStyleSheet(btn_qss("default"))
        btn_avoid.clicked.connect(self._load_avoidance)
        avoid_row.addWidget(btn_avoid)

        btn_avoid_layer = QPushButton("从图层加载建筑")
        btn_avoid_layer.setStyleSheet(btn_qss("accent"))
        btn_avoid_layer.clicked.connect(self._load_avoidance_from_qgis_layers)
        avoid_row.addWidget(btn_avoid_layer)

        btn_clear_avoid = QPushButton("清除本步成果(站点+避让)")
        btn_clear_avoid.setStyleSheet(btn_qss("danger"))
        btn_clear_avoid.setToolTip("一键清除第六步成果：所有基站站点 + 已加载的避让数据。")
        btn_clear_avoid.clicked.connect(self._clear_step6_results)
        avoid_row.addWidget(btn_clear_avoid)
        layout.addLayout(avoid_row)

        self.avoid_label = QLabel("未加载避让数据")
        self.avoid_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.avoid_label)

        # 站点列表
        layout.addWidget(self._build_site_table())

        layout.addStretch()
        self._nav_row(layout, 5)

        return page

    # ────────────────────────────────────────────────
    #  ⑦ 管线·场景
    # ────────────────────────────────────────────────
    def _build_step7(self):
        """⑦ 场景构建：机房 + 管线 + 覆盖热力图"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 6,
            "布置机房，生成基站到机房的管线并核算工程量与成本；"
            "再叠加覆盖热力图，与第 2 步的 FTTH 现网对照检查。"
        )

        # 机房位置
        room_group = QGroupBox("机房位置")
        room_group.setStyleSheet(group_style())
        room_layout = QVBoxLayout()

        # 方式1：在地图上点击添加
        room_btn_row = QHBoxLayout()
        btn_add_room = QPushButton("在地图上点击添加机房")
        btn_add_room.setStyleSheet(btn_qss("accent"))
        btn_add_room.clicked.connect(self._toggle_add_room)
        room_btn_row.addWidget(btn_add_room)

        btn_del_room = QPushButton("清除本步成果(机房+管线)")
        btn_del_room.setStyleSheet(btn_qss("danger"))
        btn_del_room.setToolTip("一键清除第七步成果：所有机房 + 所有管线。")
        btn_del_room.clicked.connect(self._clear_step7_results)
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

        # 关联显示模式（标注机房名 / 橙色关联线）
        conn_row = QHBoxLayout()
        conn_row.addWidget(QLabel("关联显示:"))
        self.assoc_mode_combo = QComboBox()
        self.assoc_mode_combo.addItems(["标注机房名(默认)", "橙色关联线"])
        self.assoc_mode_combo.setCurrentIndex(0)
        self.assoc_mode_combo.setToolTip(
            "标注机房名：在 FTTH 锚点下方直接显示归属机房名称，画面更简洁；\n"
            "橙色关联线：用虚线把锚点连到机房，直观展示挂钩关系（served_room_id）。"
        )
        self.assoc_mode_combo.currentIndexChanged.connect(self._on_assoc_mode_changed)
        conn_row.addWidget(self.assoc_mode_combo)
        room_layout.addLayout(conn_row)

        room_group.setLayout(room_layout)
        layout.addWidget(room_group)

        # 管线类型选择
        type_group = QGroupBox("管线参数")
        type_group.setStyleSheet(group_style())
        type_layout = QFormLayout()

        self.pipeline_type_combo = QComboBox()
        self.pipeline_type_combo.addItems(["直埋光缆", "通信管道", "架空光缆"])
        self.pipeline_type_combo.currentTextChanged.connect(self._on_pipeline_type_changed)
        type_layout.addRow("管线类型:", self.pipeline_type_combo)

        # 光纤类型（降本维度：不同光纤单价与适用场景不同）
        self.fiber_type_combo = QComboBox()
        self.fiber_type_combo.addItems(["G.652D (通用主干)", "G.657A (抗弯楼内)", "微型光缆 (管道高密度)"])
        self.fiber_type_combo.setCurrentIndex(0)
        self.fiber_type_combo.setToolTip(
            "G.652D：通用单模，单价最低，适合主干/长距离；\n"
            "G.657A：抗弯单模，适合楼内/密集弯曲布线；\n"
            "微型光缆：微束管，管道高密度场景省空间（单价最高）。\n"
            "成本按「管线类型 × 光纤类型」二维核算。"
        )
        type_layout.addRow("光纤类型:", self.fiber_type_combo)

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
        self.route_type_combo.addItems(["直线路径", "曼哈顿路径", "成本最优(避让)"])
        self.route_type_combo.setToolTip(
            "直线路径：站点直连机房（最短）；\n"
            "曼哈顿路径：沿道路格网（适合城市）；\n"
            "成本最优(避让)：网格 Dijkstra 自动绕开避让区，无障碍时近似直线。"
        )
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
        legend_group.setStyleSheet(group_style())
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

        # 覆盖分析（与 FTTH 现网叠加对照）
        cov_group = QGroupBox("覆盖分析")
        cov_group.setStyleSheet(group_style())
        cov_layout = QVBoxLayout()
        btn_heatmap = QPushButton("生成覆盖热力图")
        btn_heatmap.setStyleSheet(btn_qss("accent"))
        btn_heatmap.setToolTip("按 Okumura-Hata 模型渲染新建站点的覆盖强度，"
                               "可与第 2 步 FTTH 现网图层叠加比对")
        btn_heatmap.clicked.connect(self._generate_heatmap)
        cov_layout.addWidget(btn_heatmap)
        cov_group.setLayout(cov_layout)
        layout.addWidget(cov_group)

        layout.addStretch()
        self._nav_row(layout, 6)

        return page

    # ────────────────────────────────────────────────
    #  ⑧ 自检·联动
    # ────────────────────────────────────────────────
    def _build_step8(self):
        """⑧ 成果自检 + FTTH ↔ 新建设施联动查询"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 7,
            "出图前先自检：高亮不满足规范的 FTTH 要素；再用联动查询点选画布，"
            "同时高亮附近的现网要素（红）与本次新建的基站/管线/机房（蓝）。"
        )

        # 自检
        check_group = QGroupBox("成果自检")
        check_group.setStyleSheet(group_style())
        check_layout = QVBoxLayout()
        btn_ftth_hl = QPushButton("高亮自检异常要素")
        btn_ftth_hl.setStyleSheet(btn_qss("warn"))
        btn_ftth_hl.setToolTip("按 FTTH 竣工规范逐条校验，把不合规的要素在画布上标红")
        btn_ftth_hl.clicked.connect(self._highlight_ftth_anomalies)
        check_layout.addWidget(btn_ftth_hl)
        check_group.setLayout(check_layout)
        layout.addWidget(check_group)

        # 联动查询（FTTH ↔ 基站/管线/机房）
        link_group = QGroupBox("联动查询（现网 ↔ 新建）")
        link_group.setStyleSheet(group_style())
        link_layout = QVBoxLayout()

        linkage_row = QHBoxLayout()
        self._linkage_btn = QPushButton("联动查询：关")
        self._linkage_btn.setStyleSheet(btn_qss("accent"))
        self._linkage_btn.clicked.connect(self._toggle_linkage)
        linkage_row.addWidget(self._linkage_btn)

        self._linkage_radius = QDoubleSpinBox()
        self._linkage_radius.setRange(50, 5000)
        self._linkage_radius.setValue(300)
        self._linkage_radius.setSingleStep(50)
        self._linkage_radius.setSuffix(" m")
        self._linkage_radius.setToolTip("点击点周围多远距离内的要素会被高亮")
        linkage_row.addWidget(self._linkage_radius)
        link_layout.addLayout(linkage_row)

        link_tip = QLabel("开启后在地图上点击任意位置：红色 = FTTH 现网要素，"
                          "蓝色 = 本次设计的基站 / 管线 / 机房。")
        link_tip.setStyleSheet("color:#475569;font-size:11px;")
        link_tip.setWordWrap(True)
        link_layout.addWidget(link_tip)

        # 联动查询属性侧栏（P1-#5）：点选后展示高亮要素的统计与归属，形成信息闭环
        self._linkage_info = QLabel("开启联动查询并点击地图后，这里会显示高亮要素的统计与归属。")
        self._linkage_info.setWordWrap(True)
        self._linkage_info.setStyleSheet(
            "background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;"
            "color:#334155;font-size:11px;padding:8px 10px;line-height:1.5;"
        )
        link_layout.addWidget(self._linkage_info)

        link_group.setLayout(link_layout)
        layout.addWidget(link_group)

        layout.addStretch()
        self._nav_row(layout, 7)

        return page

    # ────────────────────────────────────────────────
    #  ⑨ 出图·交付
    # ────────────────────────────────────────────────
    def _build_step9(self):
        """⑨ 标准出图与交付物导出"""
        page = QWidget()
        layout = QVBoxLayout(page)

        self._step_header(
            layout, 8,
            "按官方标准出图并导出交付物：FTTH 标准 PDF、光路由表 / 光交箱汇总、"
            "工程量报表，最后同步到 M03 后端或生成 AI 设计报告。"
        )

        # 工程量报表
        report_group = QGroupBox("工程量报表（材料清单 + 造价估算）")
        report_group.setStyleSheet(group_style())
        report_layout = QVBoxLayout()

        report_desc = QLabel(
            "统计本次设计中用到的所有材料数量和规格，\n"
            "用于采购清单编制和工程造价概算。")
        report_desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        report_layout.addWidget(report_desc)

        btn_report = QPushButton("导出工程量报表")
        btn_report.setStyleSheet(btn_qss("warn"))
        btn_report.setToolTip(
            "【材料数量清单】\n"
            "统计光缆总长度、光交箱数量、接头数量、楼栋覆盖数等关键指标，\n"
            "以及基站设备清单(BOM)与 FTTH 光接入设计统计。\n"
            "点击后选择导出格式：CSV（Excel 可排序筛选）或 TXT（纯文本汇报）。")
        btn_report.clicked.connect(self._export_report)
        report_layout.addWidget(btn_report)

        report_group.setLayout(report_layout)
        layout.addWidget(report_group)

        # ── 导出视图范围选择 ──
        export_view_group = QGroupBox("导出视图范围")
        export_view_group.setStyleSheet(group_style())
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

        self.export_clear_btn = QPushButton("清除导出区域")
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

        # ── FTTH 官方交付物（真实标准对齐）──
        ftth_group = QGroupBox("FTTH 官方交付物（真实标准对齐）")
        ftth_group.setStyleSheet(group_style())
        ftth_layout = QVBoxLayout()
        ftth_desc = QLabel(
            "基于主办方真实 FTTH 竣工标准，导出官方格式交付物。\n"
            "每种文件的用途见下方按钮说明 👇"
        )
        ftth_desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        ftth_layout.addWidget(ftth_desc)

        # ── 光路由表 ──
        route_row = QHBoxLayout()
        btn_ftth = QPushButton("导出光路由表 (Routes_Optiques)")
        btn_ftth.setStyleSheet(btn_qss("primary"))
        btn_ftth.setToolTip(
            "【光缆走向一览表】\n"
            "列出每条光缆从哪个光交箱出发、经过哪些接头点、\n"
            "最终接到哪栋楼/哪个用户。相当于光纤的「路线导航」。\n"
            "用途：施工队按表逐段熔接/布线，验收时核对路径是否正确。"
        )
        btn_ftth.clicked.connect(self._export_ftth_deliverables)
        route_row.addWidget(btn_ftth)
        ftth_layout.addLayout(route_row)

        route_hint = QLabel(
            "光路由表 = 每条光缆的「起点→途经→终点」清单，施工队按此布线")
        route_hint.setStyleSheet("color:#6b7280;font-size:10px;padding-left:4px;")
        route_hint.setWordWrap(True)
        ftth_layout.addWidget(route_hint)

        # ── 光交箱汇总 ──
        box_row = QHBoxLayout()
        btn_box = QPushButton("导出光交箱汇总 (Plans_de_Boite)")
        btn_box.setStyleSheet(btn_qss("warn"))
        btn_box.setToolTip(
            "【每个光交箱的详细配置单】\n"
            "列出每个光交箱(BOITE)的位置、型号、容量（多少芯）、\n"
            "已用多少芯、剩余多少芯、连接了哪些上下游缆。\n"
            "用途：物料采购（买多少芯的光交箱）、现场安装核对。"
        )
        # 复用同一个导出函数（内部同时导出两份）
        btn_box.clicked.connect(self._export_ftth_deliverables)
        box_row.addWidget(btn_box)
        ftth_layout.addLayout(box_row)

        box_hint = QLabel(
            "📦 光交箱汇总 = 每个光分纤箱的「配置清单」，采购和安装按此对号入座")
        box_hint.setStyleSheet("color:#6b7280;font-size:10px;padding-left:4px;")
        box_hint.setWordWrap(True)
        ftth_layout.addWidget(box_hint)

        # ── 一键同步到 S1 Web 端：免去手工拷 JSON + 重建前端 ──
        ftth_sync_row = QHBoxLayout()
        self._btn_ftth_sync = QPushButton("同步 FTTH 成果到 S1")
        self._btn_ftth_sync.setStyleSheet(btn_qss("success"))
        self._btn_ftth_sync.setToolTip(
            "【一键上传到 Web 平台】\n"
            "把 FTTH 设计成果（数据+自检结果）推送到云端，\n"
            "S1 三维网页端刷新就能看到，不用手动拷贝文件。")
        self._btn_ftth_sync.clicked.connect(self._sync_ftth_to_s1)
        ftth_sync_row.addWidget(self._btn_ftth_sync)
        ftth_layout.addLayout(ftth_sync_row)

        ftth_group.setLayout(ftth_layout)
        layout.addWidget(ftth_group)

        # ── 出图与方案存档 ──
        out_group = QGroupBox("出图与方案存档")
        out_group.setStyleSheet(group_style())
        out_layout = QVBoxLayout()

        out_desc = QLabel(
            "导出当前地图视图为通用 PDF（含所有图层，不限于 FTTH）；\n"
            "或保存/加载完整设计方案（含所有步骤的参数和成果），方便下次继续。")
        out_desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        out_layout.addWidget(out_desc)

        # 导出图纸：下拉选择类型 + 一个按钮（合并“导出当前视图”与“FTTH 标准 PDF 竣工图”）
        draw_row = QHBoxLayout()
        draw_row.addWidget(QLabel("图纸类型:"))
        self.drawing_type_combo = QComboBox()
        self.drawing_type_combo.addItems(DRAWING_TYPES)
        saved_drawing = self._qsettings.value("drawing_index", 0, type=int)
        if 0 <= saved_drawing < len(DRAWING_TYPES):
            self.drawing_type_combo.setCurrentIndex(saved_drawing)
        else:
            self.drawing_type_combo.setCurrentIndex(0)
        draw_row.addWidget(self.drawing_type_combo, 1)
        out_layout.addLayout(draw_row)

        btn_export = QPushButton("导出图纸")
        btn_export.setStyleSheet(btn_qss("primary"))
        btn_export.setToolTip(
            "按上方选择导出对应图纸：\n"
            "· 当前视图(通用PDF)：地图所见即所得，含所有图层，不限 FTTH；\n"
            "· FTTH 标准 PDF 竣工图：仅含 8 个 FTTH 标准图层，带图例/比例尺，可盖章归档。")
        btn_export.clicked.connect(self._export_drawing)
        out_layout.addWidget(btn_export)

        file_row = QHBoxLayout()
        btn_save = QPushButton("保存方案")
        btn_save.setStyleSheet(btn_qss("default"))
        btn_save.setToolTip(
            "【保存完整设计进度】\n"
            "把 9 个步骤的所有参数、站点位置、FTTH 数据等\n"
            "全部存到一个文件里，下次打开可继续编辑。")
        btn_save.clicked.connect(self._save_design)
        file_row.addWidget(btn_save)

        btn_load = QPushButton("加载方案")
        btn_load.setStyleSheet(btn_qss("default"))
        btn_load.setToolTip(
            "【恢复之前保存的设计】\n"
            "读取之前「保存方案」的文件，恢复到保存时的状态。")
        btn_load.clicked.connect(self._load_design)
        file_row.addWidget(btn_load)
        out_layout.addLayout(file_row)

        out_group.setLayout(out_layout)
        layout.addWidget(out_group)

        # ── 上云与 AI 报告 ──
        deliver_group = QGroupBox("上云与 AI 报告")
        deliver_group.setStyleSheet(group_style())
        deliver_layout = QVBoxLayout()

        deliver_desc = QLabel(
            "将设计成果同步到云端 M03 后端（S1 Web 端可查看）；\n"
            "或让 AI 自动生成一份设计说明报告（含数据统计、拓扑分析、建议）。")
        deliver_desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        deliver_layout.addWidget(deliver_desc)

        btn_sync = QPushButton("同步到 M03 后端")
        btn_sync.setStyleSheet(btn_qss("teal"))
        btn_sync.setToolTip(
            "【上传全部设计数据到服务器】\n"
            "把基站、管线、FTTH 等所有成果通过 API 推送到后端数据库，\n"
            "其他模块（S3 审查 / S4 BOM / S5 监管）可读取。")
        btn_sync.clicked.connect(self._sync_to_backend)
        deliver_layout.addWidget(btn_sync)

        btn_ai_report = QPushButton("生成设计报告")
        btn_ai_report.setStyleSheet(btn_qss("accent"))
        btn_ai_report.setToolTip(
            "【自动汇总当前全部设计数据为专业报告】\n"
            "基于已生成的基站/机房/FTTH/管线/BOM 数据，\n"
            "自动生成包含项目概况、明细表、物料清单、\n"
            "覆盖分析与建议的 Markdown 报告。\n"
            "用途：直接作为项目汇报/交付材料的基础稿。")
        btn_ai_report.clicked.connect(self._open_ai_report_dialog)
        deliver_layout.addWidget(btn_ai_report)

        deliver_group.setLayout(deliver_layout)
        layout.addWidget(deliver_group)

        layout.addStretch()
        self._nav_row(layout, 8)

        return page

    def _build_site_table(self):
        group = QGroupBox("基站设计明细")
        group.setStyleSheet(group_style())
        layout = QVBoxLayout()

        self.site_table = QTableWidget()
        self.site_table.setColumnCount(13)
        headers = [
            "站点ID", "名称", "站型", "场景", "塔高(m)",
            "频段", "频率(MHz)", "功率(W)", "方位角",
            "覆盖半径(km)", "站间距(km)", "坐标", "安装方式"
        ]
        self.site_table.setHorizontalHeaderLabels(headers)
        header = self.site_table.horizontalHeader()
        # 前12列固定宽度，最后一列自适应
        widths = [110, 90, 55, 55, 60, 55, 65, 50, 70, 75, 65, 90, 0]
        for i, w in enumerate(widths[:-1]):
            header.setSectionResizeMode(i, QHeaderView.Fixed)
            self.site_table.setColumnWidth(i, w)
        header.setSectionResizeMode(11, QHeaderView.Stretch)

        self.site_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.site_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.site_table.setAlternatingRowColors(True)
        layout.addWidget(self.site_table)

        # 站点操作改为右键菜单（减少按钮数量，避免面板拥挤）
        self.site_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.site_table.customContextMenuRequested.connect(self._on_site_context_menu)

        # 键盘可达性：Delete 删除选中站点（与右键“删除选中站点”一致）。
        # 使用 WidgetShortcut 上下文，仅当表格获得焦点时触发，避免误删。
        del_shortcut = QShortcut(QKeySequence("Delete"), self.site_table)
        del_shortcut.setContext(Qt.WidgetShortcut)
        del_shortcut.activated.connect(self._delete_site)
        site_tip = QLabel("提示：右键点击某行，可「定位 / 删除 / 频段对比 / 物料清单(BOM)」")
        site_tip.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        site_tip.setWordWrap(True)
        layout.addWidget(site_tip)

        self.stats_label = QLabel("站点: 0")
        self.stats_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.stats_label)

        group.setLayout(layout)
        return group

    def _on_site_context_menu(self, point):
        """站点明细表右键菜单：定位 / 删除 / 频段对比 / 物料清单(BOM)。"""
        row = self.site_table.indexAt(point).row()
        if row < 0 or row >= len(self.generated_sites):
            return
        self.site_table.selectRow(row)  # 让 _fly_to_site 等方法作用于右键行
        menu = QMenu(self)
        act_fly = menu.addAction("定位到选中站点")
        act_del = menu.addAction("删除选中站点")
        act_cmp = menu.addAction("频段对比")
        act_bom = menu.addAction("物料清单(BOM)")
        action = menu.exec_(self.site_table.viewport().mapToGlobal(point))
        if action == act_fly:
            self._fly_to_site()
        elif action == act_del:
            self._delete_site()
        elif action == act_cmp:
            self._show_band_comparison()
        elif action == act_bom:
            self._show_bom_dialog()

    # =================================================================
    #  第一步：底图
    # =================================================================

    def _add_esri_basemap(self):
        try:
            ok, msg = add_esri_imagery()
            if ok:
                self._zoom_to_morocco()
                self._log("Esri 全球卫星图已加载，已定位到摩洛哥")
            else:
                self._log(f"Esri 卫星图加载失败: {msg}")
        except Exception as e:
            self._log(f"加载失败: {e}")

    def _add_osm_basemap(self):
        try:
            ok, msg = add_osm()
            self._log(f"OSM地图{'已加载' if ok else '加载失败: ' + msg}")
        except Exception as e:
            self._log(f"加载失败: {e}")

    def _add_tianditu_basemap(self):
        try:
            ok, msg = add_tianditu_imagery()
            if ok:
                self._log("天地图影像已加载（国内最佳卫星底图）")
            else:
                self._log(f"天地图影像加载失败: {msg}")
        except Exception as e:
            self._log(f"加载失败: {e}")

    def _add_tianditu_labels(self):
        try:
            ok, msg = add_tianditu_labels()
            self._log(f"天地图注记{'已加载' if ok else '加载失败: ' + msg}")
        except Exception as e:
            self._log(f"加载失败: {e}")

    def _add_selected_basemap(self):
        """按下拉选择加载对应底图源（合并原 4 个独立按钮）"""
        dispatch = [
            self._add_tianditu_basemap,   # 天地图影像(国内)
            self._add_tianditu_labels,    # 天地图注记
            self._add_esri_basemap,       # Esri 卫星图(全球)
            self._add_osm_basemap,        # OSM地图
        ]
        idx = self.basemap_combo.currentIndex()
        self._qsettings.setValue("basemap_index", idx)
        if 0 <= idx < len(dispatch):
            dispatch[idx]()

    def _zoom_to_morocco(self, lon=-7.59, lat=33.57, half=0.4):
        """将地图视野定位到摩洛哥（默认卡萨布兰卡），half 为半幅范围(度)"""
        try:
            from qgis.core import (
                QgsRectangle, QgsCoordinateReferenceSystem, QgsCoordinateTransform
            )
            canvas = self.iface.mapCanvas()
            dst_crs = canvas.mapSettings().destinationCrs()
            rect_4326 = QgsRectangle(
                lon - half, lat - half, lon + half, lat + half
            )
            if dst_crs.isValid() and dst_crs.authid().upper() != "EPSG:4326":
                transform = QgsCoordinateTransform(
                    QgsCoordinateReferenceSystem("EPSG:4326"),
                    dst_crs,
                    QgsProject.instance(),
                )
                rect = transform.transform(rect_4326)
            else:
                rect = rect_4326
            canvas.setExtent(rect)
            canvas.refresh()
        except Exception as e:
            self._log(f"定位摩洛哥失败: {e}")

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
                    'tech_generation': self.tech_combo.currentText(),
                    'capacity': get_baseline(self.tech_combo.currentText()).capacity_ref,
                    'coverage_radius': get_baseline(self.tech_combo.currentText()).coverage_radius_km,
                    'is_valid': True,
                }
                sites.append(site)

            self._show_progress(True, 90)

            self.generated_sites = sites
            self._add_sites_to_map(sites)
            # #5 机房归属：每基站正下方自动建 1 个机房（1:1）
            for s in self.generated_sites:
                self._ensure_room_under_site(s)
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
        # #5 机房归属：该基站正下方自动建 1 个机房（1:1）
        self._ensure_room_under_site(site)
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

    def _clear_step6_results(self):
        """清除第六步成果：所有站点 + 避让数据（合并原“清除所有站点”与“清除避让”）。"""
        reply = QMessageBox.question(self, "确认", "确定清除本步成果（所有站点 + 避让数据）？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        # 直接清除站点（绕过二次确认），再清避让
        self.generated_sites.clear()
        self._update_site_table()
        layers = QgsProject.instance().mapLayersByName("基站设计")
        if layers:
            layers[0].startEditing()
            layers[0].deleteFeatures(layers[0].allFeatureIds())
            layers[0].commitChanges()
        canvas = self.iface.mapCanvas()
        for rb in self._marker_bands:
            canvas.scene().removeItem(rb)
        self._marker_bands.clear()
        canvas.refresh()
        self._clear_avoidance()
        self._log("已清除第六步成果（站点 + 避让）")

    def _collect_building_features(self):
        """从当前 QGIS 项目自动检测建筑/房屋要素并归一化为 GeoJSON Feature 列表。
        无 UI、无弹窗，供避让检查静默调用。

        同时识别两类『建筑』：
        - 多边形面（building/建筑/房屋/footprint/batiment/INFRASTRUCTURE…）
        - 楼栋/IMB 点（楼栋/imb/immeuble/IMB/栋…）

        CRS 安全：FTTH 真实数据的 .prj 常撒谎（声称 4326 但坐标是投影网格）。
        本方法会检测坐标范围，若超出 WGS84 合法范围则保留原始坐标不做变换，
        由调用方（_check_point_avoidance）在画布坐标系下统一比对。
        返回 (layer_names: list[str], features: list[dict], crs_authid: str)。
        """
        project = QgsProject.instance()
        poly_kw = ('building', '建筑', '房屋', 'house', '房产', 'structure',
                   'building_footprint', 'footprint', 'batiment', 'bat',
                   'infrastructure', 'bati')  # 扩充法语常见词
        point_kw = ('楼栋', 'imb', 'immeuble', '栋', '楼房', 'building_point',
                    'im b', 'im_b')  # IMB 可能带空格
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        from qgis.core import QgsWkbTypes
        poly_types = (QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon,
                      QgsWkbTypes.PolygonZ, QgsWkbTypes.MultiPolygonZ)
        point_types = (QgsWkbTypes.Point, QgsWkbTypes.MultiPoint,
                       QgsWkbTypes.PointZ, QgsWkbTypes.MultiPointZ)
        found_layers = []
        # 调试：列出所有矢量图层名，便于排查匹配失败
        all_layer_names = [l.name() for l in project.mapLayers().values()
                          if l.isValid() and l.type() == QgsMapLayer.VectorLayer]
        print(f"[避让调试] 工程矢量图层: {all_layer_names}")

        for layer in project.mapLayers().values():
            if not layer.isValid() or layer.type() != QgsMapLayer.VectorLayer:
                continue
            name_lower = layer.name().lower()
            is_poly = any(kw in name_lower for kw in poly_kw)
            is_point = any(kw in name_lower for kw in point_kw)
            if not (is_poly or is_point):
                continue
            gtype = layer.geometryType()
            if is_poly and gtype not in poly_types:
                continue
            if is_point and gtype not in point_types:
                continue
            found_layers.append(layer)
            print(f"[避让调试] 匹配到建筑图层: '{layer.name()}' (type={gtype}, "
                  f"CRS={layer.crs().authid() if layer.crs().isValid() else '?'})")

        if not found_layers:
            print("[避让调试] 未匹配到任何建筑图层（关键词未命中或几何类型不符）")

        features = []
        actual_crs = None
        for layer in found_layers:
            src_crs = layer.crs()
            if src_crs and src_crs.isValid():
                actual_crs = src_crs
            # 检测 CRS 谎言：若声称 4326 但坐标超出范围，跳过变换保留原坐标
            needs_transform = False
            if src_crs and src_crs.isValid() and src_crs != wgs84:
                needs_transform = True
            elif src_crs and src_crs.isValid():
                # 声称 4326？抽样验证第一个要素坐标
                sample_ext = layer.extent()
                if (sample_ext.xMinimum() < -360 or sample_ext.xMaximum() > 360 or
                    sample_ext.yMinimum() < -90 or sample_ext.yMaximum() > 90):
                    print(f"[避让调试] 图层 '{layer.name()}' 声称 {src_crs.authid()} "
                          f"但坐标范围 ({sample_ext.xMinimum():.1f}, {sample_ext.yMinimum():.1f})"
                          f"-({sample_ext.xMaximum():.1f}, {sample_ext.yMaximum():.1f}) "
                          f"明显不是 WGS84，保留原始坐标不做变换")
                    needs_transform = False  # 不变换，保留原坐标

            transform = (QgsCoordinateTransform(src_crs, wgs84, project)
                         if needs_transform else None)
            count = 0
            for f in layer.getFeatures():
                geom = f.geometry()
                if geom.isNull() or not geom.isGeosValid():
                    continue
                qg = QgsGeometry(geom)
                if transform is not None:
                    try:
                        qg.transform(transform)
                    except Exception:
                        continue  # 变换失败跳过该要素
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(qg.asJson()),
                    "properties": {},
                })
                count += 1
            print(f"[避让调试] 从 '{layer.name()}' 收集 {count} 个要素"
                  f"{'(已转4326)' if transform else '(原始坐标系)'}")
        return [l.name() for l in found_layers], features, (actual_crs.authid() if actual_crs else "?")

    def _ensure_avoidance_loaded(self) -> bool:
        """静默确保避让数据可用：若为空，尝试从 QGIS 建筑图层自动收集。
        返回是否成功收集到建筑数据。"""
        if self._avoidance_features:
            return True
        layer_names, features, crs_auth = self._collect_building_features()
        if features:
            self._avoidance_features = features
            self._avoidance_crs_auth = crs_auth  # 记录实际坐标系，供比对使用
            self._log(f"[避让] 自动收集建筑避让数据: {', '.join(layer_names)} "
                      f"({len(features)}个, CRS={crs_auth})")
            self.avoid_label.setText(f"自动: {', '.join(layer_names)} ({len(features)}个建筑)")
            self.avoid_label.setStyleSheet("color: #27ae60;")
            return True
        return False

    def _load_avoidance_from_qgis_layers(self):
        """从当前 QGIS 项目自动检测建筑/房屋图层并加载为避让数据（按钮触发，带弹窗提示）。

        匹配规则（图层名含任一关键词即视为建筑层）：
        - building / 建筑 / 房屋 / house / 房产 / structure
        - 图层几何类型为 Polygon/MultiPolygon
        """
        layer_names, features = self._collect_building_features()

        if not layer_names:
            QMessageBox.information(
                self, "未找到建筑图层",
                "当前项目中未检测到建筑/房屋图层。\n\n"
                "请确保项目中有名称含「建筑/房屋/building/house」的"
                "多边形图层，或使用「加载避让数据」手动选择 GeoJSON 文件。")
            return

        if not features:
            QMessageBox.warning(self, "无有效要素",
                                f"找到 {len(layer_names)} 个建筑图层，但无有效多边形要素。")
            return

        self._avoidance_features = features
        self.avoid_label.setText(f"自动: {', '.join(layer_names)} ({len(features)}个建筑)")
        self.avoid_label.setStyleSheet("color: #27ae60;")
        self._log(f"已从 QGIS 图层自动加载避让: {', '.join(layer_names)}, 共 {len(features)} 个建筑多边形")

    def _check_point_avoidance(self, lon, lat, canvas_crs=None) -> list:
        """检查坐标是否命中建筑避让区域（20m 缓冲/半径）。返回冲突列表（空=安全）。

        使用 QGIS 原生 QgsGeometry 判定，不依赖 shapely / SimplePolygon。
        关键改进：不再假设建筑要素在 EPSG:4326，而是通过 canvas_crs 统一到
        画布坐标系做比对，彻底解决 PRJ 撒谎导致的坐标基准不一致问题。

        Args:
            lon, lat: 落点坐标（应与 canvas_crs 一致）
            canvas_crs: 画布坐标系（QgsCoordinateReferenceSystem），若为 None 则自动取 iface
        """
        if not self._avoidance_features:
            return []
        from qgis.core import QgsGeometry, QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform

        # 确定目标坐标系（优先用传入的，否则取画布）
        if canvas_crs is None or not canvas_crs.isValid():
            try:
                canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
            except Exception:
                canvas_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        target = QgsGeometry.fromPointXY(QgsPointXY(lon, lat))
        project = QgsProject.instance()

        # 根据坐标系单位决定 20m 缓冲半径
        authid = canvas_crs.authid() if canvas_crs.authid() else ""
        is_geographic = '4326' in authid or 'wgs84' in authid.lower()
        buf_size = (20.0 / 111000.0) if is_geographic else 20.0  # 地理坐标系用度数近似

        conflict_count = 0
        for feat in self._avoidance_features:
            try:
                geom = QgsGeometry.fromJson(feat.get('geometry', feat))
                if geom.isNull() or not geom.isGeosValid():
                    continue

                # 将建筑几何变换到画布坐标系（处理 PRJ 与实际坐标不符的情况）
                feat_crs_str = getattr(self, '_avoidance_crs_auth', None)
                if feat_crs_str and feat_crs_str != '?':
                    feat_crs = QgsCoordinateReferenceSystem(feat_crs_str)
                    if feat_crs.isValid() and feat_crs != canvas_crs:
                        try:
                            t = QgsCoordinateTransform(feat_crs, canvas_crs, project)
                            geom.transform(t)
                        except Exception:
                            pass  # 变换失败则用原始坐标碰运气

                dist = geom.distance(target)
                if dist <= buf_size + 1e-9:
                    conflict_count += 1
                    if conflict_count <= 3:  # 最多报告 3 条冲突详情
                        pass  # 积累计数
            except Exception as exc:
                continue

        if conflict_count > 0:
            return [f"建筑缓冲区(20m) — 命中 {conflict_count} 个建筑要素"]
        return []

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

    # ────────────────────────────────────────────────
    #  撤销 / 重做（P2-#9）
    # ────────────────────────────────────────────────
    def _push_undo(self, fn):
        """把一个可撤销操作（闭包）压入撤销栈。"""
        self._undo_stack.append(fn)

    def _undo(self):
        """撤销最近一次可撤销操作（当前支持机房添加）。"""
        if not self._undo_stack:
            self._log("没有可撤销的操作")
            return
        fn = self._undo_stack.pop()
        try:
            fn()
        except Exception as exc:
            self._log(f"撤销失败：{exc}")

    def _remove_room(self, rid):
        """撤销用：按 room_id 移除机房数据 + 地图标记 + 关联。"""
        rm = next((r for r in self.machine_rooms if r.room_id == rid), None)
        if rm is not None:
            try:
                self.machine_rooms.remove(rm)
            except Exception:
                pass
        # 清理与之关联的 FTTH 锚点归属
        for k in [k for k, v in self._ftth_room_map.items() if v == rid]:
            self._ftth_room_map.pop(k, None)
        bands = self._room_markers.pop(rid, None)
        if bands:
            for rb in bands:
                try:
                    self.iface.mapCanvas().scene().removeItem(rb)
                except Exception:
                    pass
            self._marker_bands = [b for b in self._marker_bands if b not in bands]
        try:
            self.iface.mapCanvas().refresh()
        except Exception:
            pass
        self._refresh_room_list_with_links()
        # 同步刷新关联虚线（移除该机房对应的连线）
        self._draw_ftth_room_connectors()
        self._log(f"已撤销添加机房: {rid}")

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

        # ── 避让检查：点击落点若压在建筑 20m 缓冲区内则警告（点击路径此前漏做）──
        # 用画布原始坐标（lon, lat）做避让比对，避免 WGS84 变换后与建筑坐标基准不一致
        self._ensure_avoidance_loaded()
        canvas_crs_for_check = self.iface.mapCanvas().mapSettings().destinationCrs()
        conflicts = self._check_point_avoidance(lon, lat, canvas_crs=canvas_crs_for_check)
        if conflicts:
            reply = QMessageBox.warning(
                self, "机房位置冲突",
                f"该位置 ({lon_wgs84:.6f}, {lat_wgs84:.6f}) 位于:\n"
                + "\n".join(f"  • {c}" for c in conflicts) +
                "\n\n是否仍要在此处放置机房？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                self._log(f"机房放置已取消（命中避让: {', '.join(conflicts)}）")
                return

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
        self._push_undo(lambda rid=room_id: self._remove_room(rid))

        # ② 增强：把最近 FTTH 锚点归属到此机房
        self._link_ftth_to_room(data)

        # 更新机房列表显示
        self._refresh_room_list_with_links()

        self._log(f"已添加机房: {room_name} ({lon_wgs84:.6f}, {lat_wgs84:.6f})")

        # 取消添加模式
        if hasattr(self, '_room_tool'):
            self.iface.mapCanvas().unsetMapTool(self._room_tool)

    def _add_room_by_coord(self):
        """按输入框坐标添加机房"""
        lon = self.room_lon_spin.value()
        lat = self.room_lat_spin.value()

        # ── 避让检查：若已加载（或能自动收集到）建筑数据，警告与建筑重叠 ──
        # 按坐标输入的是 WGS84 经纬度，传 4326 CRS 给避让检查
        self._ensure_avoidance_loaded()
        from qgis.core import QgsCoordinateReferenceSystem
        conflicts = self._check_point_avoidance(lon, lat, canvas_crs=QgsCoordinateReferenceSystem("EPSG:4326"))
        if conflicts:
            reply = QMessageBox.warning(
                self, "机房位置冲突",
                f"该坐标 ({lon:.6f}, {lat:.6f}) 位于:\n"
                + "\n".join(f"  • {c}" for c in conflicts) +
                "\n\n是否仍要在此处放置机房？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                self._log(f"机房放置已取消（命中避让: {', '.join(conflicts)}）")
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
        self._add_room_marker(lon, lat, room_name, room_id)
        self._push_undo(lambda rid=room_id: self._remove_room(rid))

        # ② 增强：把最近 FTTH 锚点归属到此机房
        self._link_ftth_to_room(data)

        # 更新机房列表显示
        self._refresh_room_list_with_links()

        self._log(f"已添加机房: {room_name} ({lon:.6f}, {lat:.6f})")

    def _delete_last_room(self, silent=False):
        """删除最后一个添加的机房（含地图标记）。silent=True 时跳过确认（供批量清除用）。"""
        if not self.machine_rooms:
            if not silent:
                QMessageBox.information(self, "提示", "当前没有可删除的机房")
            return

        last_room = self.machine_rooms[-1]
        room_id = last_room.room_id
        if not silent:
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

    def _clear_step7_results(self):
        """清除第七步成果：机房 + 管线（合并原“删除机房”与“清除管线”）。"""
        reply = QMessageBox.question(self, "确认", "确定清除本步成果（机房 + 管线）？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        # 静默删除所有机房（跳过逐条确认）
        while self.machine_rooms:
            self._delete_last_room(silent=True)
        self._clear_pipelines()
        self._log("已清除第七步成果（机房 + 管线）")

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

    # ────────────────────────────────────────────────
    #  ② 增强：FTTH 锚点 ↔ 机房 硬关联（served_room_id）
    # ────────────────────────────────────────────────
    def _add_ftth_room_field(self, layers):
        """给 FTTH 锚点层(SITE/BOITE)补 served_room_id 字段，默认空。

        SITE 是 NRO/PM 站点（固网机房级锚点），BOITE 是光交箱（BPE/PBO）。
        加机房时通过 _link_ftth_to_room 把最近的锚点归属到该机房，使固网↔机房可追溯。
        """
        from qgis.PyQt.QtCore import QVariant
        for name in ("SITE", "BOITE"):
            lyr = layers.get(name)
            if lyr is None:
                continue
            idx = lyr.fields().indexOf("served_room_id")
            nidx = lyr.fields().indexOf("served_room_name")
            if idx >= 0 and nidx >= 0:
                continue  # 已存在
            try:
                adds = []
                if idx < 0:
                    adds.append(_new_qgs_field("served_room_id", QVariant.String))
                if nidx < 0:
                    adds.append(_new_qgs_field("served_room_name", QVariant.String))
                lyr.dataProvider().addAttributes(adds)
                lyr.updateFields()
            except Exception as e:
                self._log(f"FTTH 补 served_room 字段失败({name}): {e}")

    def _link_ftth_to_room(self, room):
        """把最近的 FTTH 锚点(SITE)归属到该机房，回填 served_room_id 并记映射。"""
        if not self._ftth_layers:
            return
        site_lyr = self._ftth_layers.get("SITE")
        if site_lyr is None:
            return

        # 找最近的 SITE 锚点（按几何距离）
        nearest_fid = None
        nearest_code = None
        min_dist = float("inf")
        ridx = self._ftth_layers["SITE"].fields().indexOf("served_room_id")
        for feat in site_lyr.getFeatures():
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            dist = geom.distance(
                QgsGeometry.fromPointXY(QgsPointXY(room.longitude, room.latitude))
            )
            # 已归属其它机房则跳过（避免重复抢占）
            if ridx >= 0:
                cur = feat.attributes()[ridx]
                if cur and str(cur) not in ("", "NULL", "None"):
                    continue
            if dist < min_dist:
                min_dist = dist
                nearest_fid = feat.id()
                nearest_code = feat["CODE"] if "CODE" in feat.fields().names() else str(feat.id())

        if nearest_fid is None:
            return

        # 回填 served_room_id
        try:
            site_lyr.startEditing()
            if ridx >= 0:
                site_lyr.changeAttributeValue(nearest_fid, ridx, room.room_id)
            nidx = site_lyr.fields().indexOf("served_room_name")
            if nidx >= 0:
                site_lyr.changeAttributeValue(nearest_fid, nidx, room.name)
            site_lyr.commitChanges()
        except Exception as e:
            self._log(f"回填 served_room 失败: {e}")
            try:
                site_lyr.rollBack()
            except Exception:
                pass

        # 记映射（FTTH 锚点 id → 机房 id），供联动/报告追溯
        self._ftth_room_map[str(nearest_code)] = room.room_id
        self._log(
            f"固网↔机房关联：FTTH 锚点 {nearest_code} 归属机房 {room.room_id} "
            f"(距离约 {min_dist:.1f} m)"
        )
        # 更新机房列表，显示已关联数
        self._refresh_room_list_with_links()
        # 按当前关联显示模式刷新（标注机房名 / 橙色关联线）
        self._refresh_ftth_association_view()

    def _refresh_room_list_with_links(self):
        """刷新机房列表标签，附已关联 FTTH 锚点数。"""
        if not hasattr(self, "room_list_label"):
            return
        n_links = len(self._ftth_room_map)
        self.room_list_label.setText(
            f"已添加机房: {len(self.machine_rooms)}个 | 已关联 FTTH 锚点: {n_links}个"
        )

    def _draw_ftth_room_connectors(self):
        """根据 served_room_id 映射，画橙色虚线把每个 FTTH 锚点连到其归属机房，
        直观展示「光纤网络 ↔ 机房」的挂钩关系。"""
        layer_name = "FTTH↔机房关联线"

        # 标注模式：不画关联线，仅确保锚点已标注机房名（画面更简洁）
        if getattr(self, "_assoc_mode", "label") == "label":
            for old in QgsProject.instance().mapLayersByName(layer_name):
                QgsProject.instance().removeMapLayer(old.id())
            self._apply_site_room_label(self._ftth_layers.get("SITE"))
            return

        # 没有任何关联时，清掉残留图层并退出
        if not self._ftth_room_map:
            for old in QgsProject.instance().mapLayersByName(layer_name):
                QgsProject.instance().removeMapLayer(old.id())
            self._log("暂无 FTTH↔机房 关联（先在地图上添加机房，系统会自动关联最近 FTTH 锚点）")
            return

        site_lyr = self._ftth_layers.get("SITE")
        if site_lyr is None:
            self._log("未找到 FTTH SITE 层，无法绘制关联线")
            return

        # 反查机房坐标（WGS84）
        room_by_id = {r.room_id: r for r in self.machine_rooms}

        canvas = self.iface.mapCanvas()
        canvas_crs = canvas.mapSettings().destinationCrs()
        crs_auth = canvas_crs.authid() or "EPSG:4326"
        from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        xform_room = QgsCoordinateTransform(wgs84, canvas_crs, QgsProject.instance())
        xform_site = QgsCoordinateTransform(site_lyr.crs(), canvas_crs, QgsProject.instance())

        # 预建 FTTH 锚点 CODE → 几何
        site_geoms = {}
        for feat in site_lyr.getFeatures():
            fcode = feat["CODE"] if "CODE" in feat.fields().names() else str(feat.id())
            site_geoms[str(fcode)] = feat.geometry()

        segments = []
        for code, rid in self._ftth_room_map.items():
            room = room_by_id.get(rid)
            if room is None:
                continue
            sgeom = site_geoms.get(str(code))
            if sgeom is None or sgeom.isEmpty():
                continue
            try:
                rpt = xform_room.transform(QgsPointXY(room.longitude, room.latitude))
                sg = QgsGeometry(sgeom)
                sg.transform(xform_site)
                if sg.type() == QgsWkbTypes.PolygonGeometry:
                    sp = sg.centroid().asPoint()
                else:
                    sp = sg.asPoint()
                segments.append((rpt, sp, code, rid))
            except Exception:
                continue

        if not segments:
            self._log("未找到可绘制连线的 FTTH 锚点几何")
            return

        # 创建或复用内存线层
        existing = QgsProject.instance().mapLayersByName(layer_name)
        if existing:
            vl = existing[0]
            vl.startEditing()
            ids = [f.id() for f in vl.getFeatures()]
            if ids:
                vl.deleteFeatures(ids)
        else:
            vl = QgsVectorLayer(f"LineString?crs={crs_auth}", layer_name, "memory")
            QgsProject.instance().addMapLayer(vl)
            vl.startEditing()

        pr = vl.dataProvider()
        if vl.fields().indexOf("ftth_code") < 0:
            pr.addAttributes([_new_qgs_field("ftth_code", QVariant.String),
                              _new_qgs_field("room_id", QVariant.String)])
            vl.updateFields()

        for (rp, sp, code, rid) in segments:
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPolylineXY([rp, sp]))
            f.setAttributes([code, rid])
            pr.addFeature(f)
        vl.commitChanges()
        vl.updateExtents()

        # 橙色虚线（line_style=dash）表示挂钩关系
        from qgis.core import QgsLineSymbol
        line_sym = QgsLineSymbol.createSimple({
            "color": "255,140,0,255",
            "width": "1.4",
            "line_style": "dash",
            "cap_style": "round",
            "join_style": "round",
        })
        vl.renderer().setSymbol(line_sym)
        vl.triggerRepaint()
        node = QgsProject.instance().layerTreeRoot().findLayer(vl.id())
        if node is not None:
            node.setItemVisibilityChecked(True)
        canvas.refresh()
        self._log(f"已绘制 {len(segments)} 条 FTTH↔机房 关联虚线（橙色虚线 = 光交箱归属机房）")

    def _on_assoc_mode_changed(self, idx):
        """关联显示模式切换：0=标注机房名(默认) / 1=橙色关联线。"""
        self._assoc_mode = "line" if idx == 1 else "label"
        self._refresh_ftth_association_view()

    def _apply_site_room_label(self, site_lyr):
        """在 FTTH SITE 锚点符号下方标注其归属机房名（served_room_name）。"""
        if site_lyr is None:
            return
        try:
            from qgis.core import (
                QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling,
            )
            if site_lyr.fields().indexOf("served_room_name") < 0:
                return
            ls = QgsPalLayerSettings()
            ls.fieldName = "served_room_name"
            ls.placement = QgsPalLayerSettings.Below
            ls.enabled = True
            fmt = QgsTextFormat()
            fmt.setSize(8.0)
            fmt.setColor(QColor(214, 90, 0))  # 与关联线同色系（橙）
            ls.setFormat(fmt)
            site_lyr.setLabeling(QgsVectorLayerSimpleLabeling(ls))
            site_lyr.setLabelsEnabled(True)
            site_lyr.triggerRepaint()
        except Exception as e:
            self._log(f"FTTH 锚点标注机房名失败: {e}")

    def _refresh_ftth_association_view(self):
        """按 _assoc_mode 刷新 FTTH↔机房 关联展示：
        label = 锚点下方标机房名（默认，画面简洁）；line = 画橙色关联虚线。"""
        site_lyr = self._ftth_layers.get("SITE") if self._ftth_layers else None
        if getattr(self, "_assoc_mode", "label") == "label":
            for old in QgsProject.instance().mapLayersByName("FTTH↔机房关联线"):
                QgsProject.instance().removeMapLayer(old.id())
            if site_lyr is not None:
                self._apply_site_room_label(site_lyr)
            self._log("关联显示：标注模式（FTTH 锚点下方显示归属机房名）")
        else:
            if site_lyr is not None:
                site_lyr.setLabelsEnabled(False)
                site_lyr.triggerRepaint()
            self._draw_ftth_room_connectors()

    # ────────────────────────────────────────────────
    #  ① 增强：建设模式切换（现网补盲 / 新区新建）
    # ────────────────────────────────────────────────
    def _on_mode_changed(self, index):
        """建设模式切换：现网补盲(0) / 新区新建(1)。"""
        self._build_mode = "greenfield" if index == 1 else "brownfield"
        # 持久化（P2-#10）
        self._qsettings.setValue("build_mode", index)
        self._update_mode_note()
        self._refresh_step_nav()
        self._log(f"建设模式切换为: {'新区新建' if self._build_mode == 'greenfield' else '现网补盲'}")

    def _update_mode_note(self):
        """根据当前模式更新第 2 步提示标签与 FTTH 加载按钮可用状态。"""
        if self._mode_note_label is None or self._ftth_load_btn is None:
            return
        if self._build_mode == "greenfield":
            self._ftth_load_btn.setDisabled(True)
            self._ftth_load_btn.setToolTip(
                "新区新建模式下 FTTH 为设计产物：布置机房+区域+管线后，"
                "点下方『生成 FTTH 设计』自动合成（示意）。请先在第④-⑦步布置机房与管线。"
            )
            self._mode_note_label.setText(
                "当前模式：新区新建。FTTH 不再是固定加载的现网，而是机房/管线布置后"
                "由下方『生成 FTTH 设计』自动合成的设计产物（示意，非竣工依据）；"
                "故第②/③步已禁用。当前正式可用的是「现网补盲」模式。"
            )
            if self._greenfield_banner is not None:
                self._greenfield_banner.setVisible(True)
            if getattr(self, "_gen_ftth_btn", None) is not None:
                self._gen_ftth_btn.setVisible(True)   # greenfield 才可用
        else:
            self._ftth_load_btn.setDisabled(False)
            self._ftth_load_btn.setToolTip(
                "读取 IMB / SITE / BOITE / CABLE / PTECH / "
                "INFRASTRUCTURE / ZNRO / ZPM 共 8 类图层并套用官方符号"
            )
            self._mode_note_label.setText(
                "当前模式：现网补盲。FTTH 为固定竣工基线——先加载（本步）找缺口（第 ③ 步），"
                "再在缺口处补机房/管线/基站（第 ⑤-⑦ 步）。"
            )
            if self._greenfield_banner is not None:
                self._greenfield_banner.setVisible(False)
            if getattr(self, "_gen_ftth_btn", None) is not None:
                self._gen_ftth_btn.setVisible(False)

    def _on_generate_ftth_design(self):
        """#5 Phase B：greenfield 由机房+管线合成 FTTH 设计并渲染到地图。

        仅 greenfield 模式可触发（按钮已仅在该模式可见）。brownfield 路径不触碰。
        产物为示意性设计，标注为非竣工依据。
        """
        if self._build_mode != "greenfield":
            return
        # 前置检查
        if not self.machine_rooms:
            QMessageBox.warning(self, "提示",
                "请先在地图上添加至少 1 个机房（OLT 锚点），再生成 FTTH 设计。")
            return
        if not self.selected_extent:
            QMessageBox.warning(self, "提示",
                "请先在第④步框选设计区域，再生成 FTTH 设计。")
            return

        try:
            # 设计区域面（selected_extent 为矩形 → 闭合多边形）
            min_lon, min_lat, max_lon, max_lat = self.selected_extent
            area_poly = [
                [min_lon, min_lat], [max_lon, min_lat],
                [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat],
            ]
            rooms = [r.to_dict() for r in self.machine_rooms]
            design = generate_ftth_design(
                rooms=rooms,
                area_poly=area_poly,
                pipelines=self.generated_pipelines,
            )
            self._render_ftth_design(design)
            self.ftth_design = design

            st = design["stats"]
            msg = (f"已生成 FTTH 设计（示意）：OLT {st['olt_count']} · FD {st['fd_count']} · "
                   f"楼栋 {st['building_count']} · 主干 {st['trunk_cables']}段/"
                   f"{st['trunk_length_km']}km · 入户 {st['drop_cables']}段/{st['drop_length_km']}km")
            self._log(msg)
            if self._greenfield_banner is not None:
                self._greenfield_banner.setText(
                    "新区新建：FTTH 已由机房/管线自动生成（示意性设计产物，非竣工依据）。可重新布置后再次生成。")
                self._greenfield_banner.setStyleSheet(
                    "background-color:#ecfdf5;border:1px solid #6ee7b7;border-radius:6px;"
                    "color:#065f46;font-size:11px;padding:8px 10px;line-height:1.5;")
            QMessageBox.information(self, "FTTH 设计已生成", msg)
        except Exception as e:
            self._log(f"FTTH 设计生成失败: {e}")
            QMessageBox.critical(self, "生成失败", str(e))

    def _render_ftth_design(self, design: dict):
        """把合成 FTTH 设计渲染为内存图层（ZNRO/IMB 点 + CABLE 线），沿用 ftth 配色。"""
        project = QgsProject.instance()
        # 清理旧设计层
        for name in ("S1-GF-OLT", "S1-GF-楼栋", "S1-GF-光缆"):
            lyr = project.mapLayersByName(name)
            if lyr:
                project.removeMapLayer(lyr[0])

        # OLT / 机房节点（玫瑰红，与 ftth ZNRO 配色一致 #f43f5e）
        olt_layer = QgsVectorLayer("Point?crs=EPSG:4326", "S1-GF-OLT", "memory")
        olt_layer.renderer().setSymbol(QgsMarkerSymbol.createSimple(
            {"name": "diamond", "color": "#f43f5e", "size": "5", "outline_color": "#ffffff"}))
        of = []
        for z in design["ZNRO"]:
            ft = QgsFeature(olt_layer.fields())
            ft.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(z["lon"], z["lat"])))
            ft.setAttributes([z["name"]])
            of.append(ft)
        olt_layer.dataProvider().addFeatures(of)
        olt_layer.updateExtents()
        project.addMapLayer(olt_layer)

        # 楼栋（中性灰蓝）
        imb_layer = QgsVectorLayer("Point?crs=EPSG:4326", "S1-GF-楼栋", "memory")
        imb_layer.renderer().setSymbol(QgsMarkerSymbol.createSimple(
            {"name": "square", "color": "#64748b", "size": "3", "outline_color": "#ffffff"}))
        imf = []
        for b in design["IMB"]:
            ft = QgsFeature(imb_layer.fields())
            ft.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(b["lon"], b["lat"])))
            ft.setAttributes([b["name"]])
            imf.append(ft)
        imb_layer.dataProvider().addFeatures(imf)
        imb_layer.updateExtents()
        project.addMapLayer(imb_layer)

        # 光缆（主干 rose / 入户 蓝灰 线）
        cable_layer = QgsVectorLayer("LineString?crs=EPSG:4326", "S1-GF-光缆", "memory")
        cf = []
        for c in design["CABLE"]:
            coords = c["coordinates"]
            if len(coords) < 2:
                continue
            ft = QgsFeature(cable_layer.fields())
            geom = QgsGeometry.fromPolylineXY([QgsPointXY(*coords[0]), QgsPointXY(*coords[1])])
            ft.setGeometry(geom)
            ft.setAttributes([c["kind"]])
            cf.append(ft)
        cable_layer.dataProvider().addFeatures(cf)
        # 统一简单线符号（主干/入户同色，演示用）
        cable_layer.renderer().setSymbol(QgsLineSymbol.createSimple(
            {"color": "#2563eb", "width": "0.6"}))
        cable_layer.updateExtents()
        project.addMapLayer(cable_layer)

        self.iface.mapCanvas().refresh()
        self._log("FTTH 设计图层已渲染：S1-GF-OLT / S1-GF-楼栋 / S1-GF-光缆")

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

    def _add_room_marker_wgs84(self, lon, lat, name, room_id=None):
        """WGS84 坐标的机房标记：先变换到画布 CRS，再画紫色菱形（与手动加机房一致）。"""
        canvas = self.iface.mapCanvas()
        canvas_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        if canvas_crs != wgs84:
            from qgis.core import QgsCoordinateTransform
            xform = QgsCoordinateTransform(wgs84, canvas_crs, QgsProject.instance())
            try:
                pt = xform.transform(QgsPointXY(lon, lat))
                lon, lat = pt.x(), pt.y()
            except Exception:
                pass
        self._add_room_marker(lon, lat, name, room_id)

    def _ensure_room_under_site(self, site):
        """#5 机房归属：每个基站落点时在其正下方自动建 1 个机房（1:1），
        绑定 served_room_id；房间坐标与基站重合（纬度南偏 ~0.0004°≈40m 以示区分）。
        FD（光交箱）接入时即连「最近基站下方的机房」。幂等：同 site_id 不重复建。"""
        sid = site.get('site_id')
        if sid is None:
            return
        room_id = f"ROOM-{sid}"
        if any(r.room_id == room_id for r in self.machine_rooms):
            return  # 已存在（重生成/撤销重做防护）
        try:
            rlon = float(site['longitude'])
            rlat = float(site['latitude']) - 0.0004
        except (KeyError, TypeError, ValueError):
            return
        room = MachineRoom(
            room_id=room_id,
            name=f"{site.get('name', '基站')}机房",
            room_type='汇聚机房',
            longitude=rlon,
            latitude=rlat,
            capacity=10,
        )
        self.machine_rooms.append(room)
        self._add_room_marker_wgs84(rlon, rlat, room.name, room_id)
        site['served_room_id'] = room_id
        try:
            self._link_ftth_to_room(room)
            self._refresh_room_list_with_links()
        except Exception:
            pass
        self._log(f"自动建机房: {room.name}（位于 {site.get('name', '基站')} 正下方）")

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
            fiber_map = {
                "G.652D (通用主干)": FiberType.G652D,
                "G.657A (抗弯楼内)": FiberType.G657A,
                "微型光缆 (管道高密度)": FiberType.MINI,
            }
            pipeline_type = type_map[self.pipeline_type_combo.currentText()]
            fiber_type = fiber_map[self.fiber_type_combo.currentText()]
            idx = self.route_type_combo.currentIndex()
            route_type = {0: "direct", 1: "manhattan", 2: "optimal"}.get(idx, "direct")

            self._show_progress(True, 20)
            QApplication.processEvents()

            # 逐站解析各自应连接的机房：优先 served_room_id 绑定，否则最近机房
            room_by_id = {r.room_id: r for r in self.machine_rooms}

            def _room_for(site):
                rid = site.get('served_room_id')
                if rid and rid in room_by_id:
                    return room_by_id[rid]
                # 回退：到所有机房中坐标最近者（平方距离比较，无需 haversine）
                best, best_d = None, None
                for r in self.machine_rooms:
                    d = (r.longitude - site['longitude']) ** 2 + (r.latitude - site['latitude']) ** 2
                    if best_d is None or d < best_d:
                        best_d, best = d, r
                return best

            # 为每个基站生成管线
            if self.share_route_check.isChecked():
                # 共享路由：按"目标机房"分组，每组内部做共享去重（跨机房不强行共享）
                self._log("使用共享管线路由（按归属机房分组）...")
                groups = {}
                for site in self.generated_sites:
                    r = _room_for(site)
                    if r is None:
                        continue
                    groups.setdefault(r.room_id, []).append(site)
                all_pipelines, shared_segments = [], {}
                for rid, grp in groups.items():
                    r = room_by_id[rid]
                    pls, segs = generate_shared_pipelines(
                        sites=grp,
                        room_lon=r.longitude,
                        room_lat=r.latitude,
                        pipeline_type=pipeline_type,
                        route_type=route_type,
                        fiber_type=fiber_type,
                    )
                    for p in pls:
                        p.end_site_id = rid  # 修正为该机房真实 ID
                    all_pipelines.extend(pls)
                    shared_segments.update(segs)
                volume = calculate_shared_engineering_volume(all_pipelines, shared_segments)
                self.volume_label.setText(
                    f"原始: {volume['原始总长度(m)']:.0f}m | 去重: {volume['去重后总长度(m)']:.0f}m | 节省: {volume['节省比例(%)']:.1f}%")
            else:
                # 非共享：逐站连各自归属机房
                self._log("生成管线（逐站连归属机房）...")
                all_pipelines = []
                for i, site in enumerate(self.generated_sites):
                    r = _room_for(site)
                    if r is None:
                        continue
                    p = generate_pipeline_to_room(
                        site_lon=site['longitude'],
                        site_lat=site['latitude'],
                        room_lon=r.longitude,
                        room_lat=r.latitude,
                        pipeline_type=pipeline_type,
                        route_type=route_type,
                        fiber_type=fiber_type,
                    )
                    p.pipeline_id = f"PL-{i + 1:04d}"
                    p.start_site_id = site['site_id']
                    p.end_site_id = r.room_id
                    all_pipelines.append(p)
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
            fiber_label = self.fiber_type_combo.currentText().split(" ")[0]
            self.cost_stats_label.setText(
                f"总成本: {cost_summary['总成本(元)']:,.0f}元  |  光纤: {fiber_label}")

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
            _new_qgs_field("rsrp", QVariant.Double),
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

        apply_glossary_tips(dialog)
        dialog.exec_()

    def _export_report(self):
        """导出工程量报表：单个对话框选择 CSV 或 TXT 格式。"""
        saved_dir = self._qsettings.value("report_dir", "", type=str)
        default_name = f"{REPORT_DEFAULT_NAME}_{datetime.now().strftime('%Y%m%d')}"
        default_path = os.path.join(saved_dir, default_name) if saved_dir else default_name
        fpath, sel_filter = QFileDialog.getSaveFileName(
            self, "导出工程量报表", default_path, REPORT_SAVE_FILTER)
        fpath, fmt = resolve_report_target(fpath, sel_filter)
        if not fpath:
            return
        self._qsettings.setValue("report_dir", os.path.dirname(fpath))
        if fmt == CSV:
            self._export_report_csv(fpath)
        else:
            self._export_report_txt(fpath)

    def _export_report_txt(self, fpath=None):
        """导出工程量报表为TXT格式（管线 + 设备清单 + BOM + FTTH 统计）"""
        if not self.generated_pipelines and not self.generated_sites:
            QMessageBox.warning(self, "导出", "没有管线或站点数据，请先生成方案")
            return

        if not fpath:
            fpath, _ = QFileDialog.getSaveFileName(
                self, "导出工程量报表",
                f"{REPORT_DEFAULT_NAME}_{datetime.now().strftime('%Y%m%d')}.txt",
                "文本文件 (*.txt)")
            if not fpath:
                return

        try:
            from io import StringIO
            buf = StringIO()

            # ── 第一部分：管线报表（原有逻辑）──
            if self.generated_pipelines:
                buf.write(generate_pipeline_report_text(self.generated_pipelines))
                buf.write("\n\n")

            # ── 第二部分：基站设备清单（第六步拓扑引擎产物）──
            buf.write("=" * 60)
            buf.write("\n  六、基站设备清单（拓扑引擎 / 本地BOM）\n")
            buf.write("=" * 60)
            buf.write(f"\n  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            buf.write("-" * 40)

            if self._device_layout:
                buf.write(f"\n  拓扑引擎设备: {len(self._device_layout)} 条\n")
                buf.write(f"  {'所属站点':<14} {'设备名称':<18} {'设备类型':<12} {'方位角':<8} {'下倾角':<8}\n")
                buf.write("-" * 62 + "\n")
                for d in self._device_layout:
                    buf.write(f"  {str(d.get('parentDevice') or ''):<14} "
                              f"{str(d.get('deviceName') or ''):<18} "
                              f"{str(d.get('deviceType') or ''):<12} "
                              f"{str(d.get('azimuth') or ''):<8} "
                              f"{str(d.get('downtilt') or ''):<8}\n")
            else:
                buf.write("\n  拓扑引擎设备: 无（未走拓扑引擎或未生成）\n")

            # 本地 BOM（从 Site.bill_of_materials）
            from models.site import Site
            bom_rows = []
            for s in self.generated_sites:
                st = Site(
                    site_id=s.get('site_id', ''), name=s.get('name', ''),
                    longitude=float(s.get('longitude', 0)), latitude=float(s.get('latitude', 0)),
                    site_type=s.get('site_type', 'MACRO'),
                    tower_type=s.get('tower_type', 'MONOPOLE'),
                    tower_height=float(s.get('tower_height', 35)),
                    mount_type=s.get('mount_type', 'GROUND'),
                )
                bom = st.bill_of_materials()
                mt_cn = '楼面塔' if bom['mount_type'] == 'ROOFTOP' else '地面塔'
                for it in bom['items']:
                    bom_rows.append((s.get('site_id', ''), mt_cn, it['name'], it['spec'],
                                     f"{it['qty']} {it['unit']}"))

            if bom_rows:
                buf.write(f"\n  基站BOM物料: {len(bom_rows)} 行\n")
                buf.write(f"  {'站点':<10} {'安装方式':<8} {'物料':<16} {'规格':<12} {'数量/单位':<12}\n")
                buf.write("-" * 60 + "\n")
                for sid, mt, nm, sp, qty in bom_rows:
                    buf.write(f"  {sid:<10} {mt:<8} {nm:<16} {sp:<12} {qty:<12}\n")
            else:
                buf.write("\n  基站BOM物料: 无（请先生成基站方案）\n")

            # ── 第三部分：FTTH 设计统计（greenfield 产物）──
            buf.write("\n")
            buf.write("=" * 60)
            buf.write("\n  七、FTTH 光接入设计统计\n")
            buf.write("=" * 60)

            ftth = getattr(self, 'ftth_design', None)
            if ftth and isinstance(ftth, dict) and "stats" in ftth:
                st = ftth["stats"]
                # 分类表格化（不再散列两列）
                buf.write(f"\n  {'分类':<14} {'指标':<12} {'数值':<10} {'单位/说明':<20}\n")
                buf.write("  " + "-" * 56 + "\n")
                buf.write(f"  {'机房锚点':<14} {'OLT/机房':<12} {st.get('olt_count', 0):<10} {'光信号起点':<20}\n")
                buf.write(f"  {'分光节点':<14} {'光交箱FD':<12} {st.get('fd_count', 0):<10} {'光纤分配节点':<20}\n")
                buf.write(f"  {'覆盖对象':<14} {'覆盖楼栋':<12} {st.get('building_count', 0):<10} {'栋 (IMB)':<20}\n")
                buf.write(f"  {'主干光缆':<14} {'缆段数':<12} {st.get('trunk_cables', 0):<10} {'机房→FD':<20}\n")
                buf.write(f"  {'主干光缆':<14} {'总长度':<12} {st.get('trunk_length_km', 0):.2f}{' km':<16} {'':>4}\n")
                buf.write(f"  {'入户光缆':<14} {'缆段数':<12} {st.get('drop_cables', 0):<10} {'FD→楼栋':<20}\n")
                buf.write(f"  {'入户光缆':<14} {'总长度':<12} {st.get('drop_length_km', 0):.2f}{' km':<16} {'':>4}\n")
                buf.write("\n  FD接入方式: 每个光交箱连接最近基站下方机房(trunk)，符合工程逻辑\n")
                buf.write(f"\n  FD→机房接入方式: 每个FD连接最近基站下方机房（trunk）\n")
            else:
                buf.write("\n  FTTH 设计: 未生成（仅 greenfield 模式可用）\n")

            buf.write("\n")
            buf.write("=" * 60)
            buf.write("  报表结束\n")
            buf.write("=" * 60)
            buf.write("\n")

            report_text = buf.getvalue()
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(report_text)

            QMessageBox.information(self, "导出成功",
                                    f"工程量报表已导出到:\n{fpath}\n\n"
                                    f"包含内容:\n"
                                    f"- 管线工程量与成本（原）\n"
                                    f"- 基站设备清单（拓扑引擎/BOM）\n"
                                    f"- FTTH 光接入设计统计")
            self._log("工程量报表已导出 (TXT, 含设备+BOM+FTTH)")

        except Exception as e:
            QMessageBox.critical(self, "导出错误", str(e))
            self._log(f"报表导出失败: {e}")

    def _export_report_csv(self, fpath=None):
        """导出工程量报表为CSV格式（管线 + 设备清单 + BOM + FTTH 统计）"""
        if not self.generated_pipelines and not self.generated_sites:
            QMessageBox.warning(self, "导出", "没有管线或站点数据，请先生成方案")
            return

        if not fpath:
            fpath, _ = QFileDialog.getSaveFileName(
                self, "导出工程量报表",
                f"{REPORT_DEFAULT_NAME}_{datetime.now().strftime('%Y%m%d')}.csv",
                "CSV文件 (*.csv)")
            if not fpath:
                return

        try:
            import csv

            # ── 第一部分：管线4表（原有逻辑）──
            if self.generated_pipelines:
                success = export_pipeline_report_csv(self.generated_pipelines, fpath)
                if not success:
                    QMessageBox.warning(self, "导出失败", "CSV管线部分导出失败，请检查文件路径")
                    return

            # ── 第二部分：设备清单（拓扑引擎）──
            dev_path = fpath.replace(".csv", "_设备清单.csv")
            with open(dev_path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(["所属站点", "设备名称", "设备类型", "方位角(°)", "下倾角(°)"])
                for d in (self._device_layout or []):
                    w.writerow([
                        d.get("parentDevice") or "",
                        d.get("deviceName") or "",
                        d.get("deviceType") or "",
                        d.get("azimuth") or "",
                        d.get("downtilt") or "",
                    ])

            # ── 第三部分：基站BOM物料 ──
            from models.site import Site
            bom_path = fpath.replace(".csv", "_BOM物料.csv")
            with open(bom_path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(["站点ID", "安装方式", "物料名称", "规格", "数量", "单位"])
                for s in self.generated_sites:
                    st = Site(
                        site_id=s.get('site_id', ''), name=s.get('name', ''),
                        longitude=float(s.get('longitude', 0)), latitude=float(s.get('latitude', 0)),
                        site_type=s.get('site_type', 'MACRO'),
                        tower_type=s.get('tower_type', 'MONOPOLE'),
                        tower_height=float(s.get('tower_height', 35)),
                        mount_type=s.get('mount_type', 'GROUND'),
                    )
                    bom = st.bill_of_materials()
                    mt_cn = '楼面塔' if bom['mount_type'] == 'ROOFTOP' else '地面塔'
                    for it in bom['items']:
                        w.writerow([s.get('site_id', ''), mt_cn, it['name'], it['spec'],
                                    it['qty'], it['unit']])

            # ── 第四部分：FTTH 设计统计（分类多列表格）──
            ftth_path = fpath.replace(".csv", "_FTTH统计.csv")
            with open(ftth_path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(["分类", "指标", "数值", "单位", "说明"])
                ftth = getattr(self, 'ftth_design', None)
                if ftth and isinstance(ftth, dict) and "stats" in ftth:
                    st = ftth["stats"]
                    w.writerow(["机房锚点", "OLT/机房数量", st.get('olt_count', 0), "个", "光信号起点"])
                    w.writerow(["分光节点", "光交箱(FD)数量", st.get('fd_count', 0), "个", "光纤分配节点"])
                    w.writerow(["覆盖对象", "覆盖楼栋数", st.get('building_count', 0), "栋", "IMB 楼栋"])
                    w.writerow(["主干光缆", "主干缆段数", st.get('trunk_cables', 0), "段", "机房→FD"])
                    w.writerow(["主干光缆", "主干总长度", f"{st.get('trunk_length_km', 0):.2f}", "km", "—"])
                    w.writerow(["入户光缆", "入户缆段数", st.get('drop_cables', 0), "段", "FD→楼栋"])
                    w.writerow(["入户光缆", "入户总长度", f"{st.get('drop_length_km', 0):.2f}", "km", "—"])
                    w.writerow(["接入方式", "FD→机房连接", "逐站连最近基站下方机房", "—", "trunk"])
                else:
                    w.writerow(["状态", "未生成（仅greenfield模式）", "", "", ""])

            file_count = 4 + (1 if self.generated_pipelines else 0)  # 设备+BOM+FTTH + 汇总(管线已有)
            if self.generated_pipelines:
                file_count += 3  # 管线明细+工程量+成本

            QMessageBox.information(self, "导出成功",
                                    f"工程量报表已导出到:\n{fpath}\n\n"
                                    f"共生成 {file_count} 个CSV文件:\n"
                                    f"- 明细表 / 工程量表 / 成本表 / 汇总表（管线）\n"
                                    f"- 设备清单（拓扑引擎）\n"
                                    f"- BOM物料（基站物料）\n"
                                    f"- FTTH统计（光接入设计）")
            self._log("工程量报表已导出 (CSV, 含设备+BOM+FTTH)")

        except Exception as e:
            QMessageBox.critical(self, "导出错误", str(e))
            self._log(f"报表导出失败: {e}")

    def _export_drawing(self):
        """按下拉选择导出对应图纸：当前视图(通用PDF) 或 FTTH 标准 PDF 竣工图。"""
        idx = self.drawing_type_combo.currentIndex()
        self._qsettings.setValue("drawing_index", idx)
        if drawing_type_for_index(idx) == DRAWING_FTTH:
            self._export_ftth_pdf()
        else:
            self._export_pdf()

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

    def _export_ftth_deliverables(self):
        """导出 FTTH 官方交付物：光交箱汇总 + 光路由表 + 机柜熔接盘图 + 系统图（真实标准对齐）。"""
        import os
        from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
        from ftth.field_map import LAYER_FILE_PREFIX

        # ── 智能选择数据源：优先复用已加载的 FTTH 目录，避免重复选文件 ──
        default_dir = getattr(self, "_ftth_shape_dir", None) or ""
        # 如果当前已有 FTTH 图层在项目中，直接用已知路径，不再弹目录选择框
        if self._ftth_layers and default_dir and os.path.isdir(default_dir):
            shape_dir = default_dir
            self._log(f"自动使用已加载的 FTTH 目录: {shape_dir}")
        else:
            shape_dir = QFileDialog.getExistingDirectory(
                self, "选择 FTTH Shape 目录（含 IMB/SITE/BOITE/... 共 8 个 .dbf）",
                default_dir)
            if not shape_dir:
                return

        # ── 校验：目录里必须真有 FTTH 的 .dbf 数据，否则拦截 ──
        present = [p for p in LAYER_FILE_PREFIX.values()
                   if os.path.exists(os.path.join(shape_dir, p + ".dbf"))]
        if not present:
            QMessageBox.warning(
                self, "目录不对",
                "该目录下找不到任何 FTTH 数据文件（期望 IMB.dbf / SITE.dbf / "
                "BOITE.dbf 等共 8 个）。\n\n"
                "请选择【当初加载 FTTH 图层时】选的那个 Shape 目录\n"
                "（例如 Plan_de_récolement/Shape 或 模版/EJA02-MRJ02/Shape），\n"
                "不要选导出结果所在的输出目录（那里只有 xlsx）。")
            return
        if len(present) < len(LAYER_FILE_PREFIX):
            self._log(f"提示：该目录仅含 {len(present)}/{len(LAYER_FILE_PREFIX)} 个 FTTH 层"
                      f"（{', '.join(present)}），部分交付物可能为空。")

        try:
            # 延迟导入：避免 ftth 包异常影响插件整体加载
            from ftth.export_runner import export_from_dbf
            # ── 自选保存文件夹：交付物输出位置可自由选择，默认记忆上次选择 ──
            default_out = self._qsettings.value("ftth_export_dir", shape_dir, type=str)
            out_dir = QFileDialog.getExistingDirectory(
                self, "选择 FTTH 交付物保存文件夹", default_out)
            if not out_dir:
                return
            self._qsettings.setValue("ftth_export_dir", out_dir)
            prefix = os.path.basename(shape_dir.rstrip("/\\")) or "ftth"
            result = export_from_dbf(shape_dir, out_dir, prefix=prefix)
            s = result["summary"]
            pdb_lines = "\n".join(
                f"  机柜熔接盘图[{pm}]: {os.path.basename(p)}"
                for pm, p in result.get("plan_de_baie", {}).items()
            )
            syn_lines = "\n".join(
                f"  系统图[{pm}]: {os.path.basename(p)}"
                for pm, p in result.get("synoptique", {}).items()
            )
            msg = (
                f"FTTH 交付物已导出 (数据源: {s.get('source')})\n"
                f"图层计数: IMB={s.get('IMB')} SITE={s.get('SITE')} BOITE={s.get('BOITE')} "
                f"CABLE={s.get('CABLE')} PTECH={s.get('PTECH')} INFRA={s.get('INFRASTRUCTURE')} "
                f"ZNRO={s.get('ZNRO')} ZPM={s.get('ZPM')}\n\n"
                f"光路由表: {os.path.basename(result['routes_optiques'])}\n"
                f"光交箱汇总: {os.path.basename(result['boite_sommaire'])}\n"
                f"{pdb_lines}\n{syn_lines}\n"
                f"输出目录: {out_dir}"
            )
            # 记录本次导出位置，供「同步到 S1」直接取用，免得操作员再选一次目录
            self._ftth_last_export = {"out_dir": out_dir, "file_tag": prefix}

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("FTTH 交付物导出成功")
            box.setText(msg + "\n\n可直接同步到 S1 Web 端，无需手工拷贝 JSON。")
            sync_btn = box.addButton("立即同步到 S1", QMessageBox.AcceptRole)
            box.addButton("稍后再说", QMessageBox.RejectRole)
            box.exec_()
            self._log("FTTH 官方交付物已导出: 光路由表 + 光交箱汇总 + 机柜熔接盘图 + 系统图")
            if box.clickedButton() is sync_btn:
                self._sync_ftth_to_s1()
        except Exception as e:
            QMessageBox.critical(self, "FTTH 导出错误", str(e))

    # ------------------------------------------------------------------
    # FTTH 成果一键同步到 S1 Web 端
    # ------------------------------------------------------------------
    def _sync_ftth_to_s1(self):
        """把最近一次导出的 FTTH 三件套推送到 M03 后端，S1 前端刷新即可见。"""
        import os
        import glob
        import json
        from qgis.PyQt.QtWidgets import (QFileDialog, QMessageBox, QInputDialog,
                                         QApplication)

        last = getattr(self, "_ftth_last_export", None) or {}
        out_dir = last.get("out_dir")
        file_tag = last.get("file_tag")

        # 没有导出记录（比如刚开 QGIS）→ 让操作员选导出目录
        if not out_dir or not os.path.isdir(out_dir):
            out_dir = QFileDialog.getExistingDirectory(
                self, "选择 FTTH 导出目录（含 *_ftth-data.json 的 livrables 目录）",
                self._qsettings.value(
                    "ftth_export_dir", getattr(self, "_ftth_shape_dir", None) or "", type=str))
            if not out_dir:
                return
            file_tag = None

        # 定位 *_ftth-data.json，多个则让操作员挑
        candidates = sorted(glob.glob(os.path.join(out_dir, "*_ftth-data.json")))
        if not candidates:
            QMessageBox.warning(
                self, "没有可同步的数据",
                f"目录下找不到 *_ftth-data.json：\n{out_dir}\n\n"
                "请先执行【导出光路由表 + 光交箱汇总】，导出链会一并生成前端所需的 JSON。")
            return
        if file_tag and os.path.join(out_dir, f"{file_tag}_ftth-data.json") in candidates:
            picked = os.path.join(out_dir, f"{file_tag}_ftth-data.json")
        elif len(candidates) == 1:
            picked = candidates[0]
        else:
            names = [os.path.basename(p) for p in candidates]
            name, ok = QInputDialog.getItem(
                self, "选择要同步的成果", "该目录有多份导出，选择一份：", names, 0, False)
            if not ok:
                return
            picked = os.path.join(out_dir, name)
        file_tag = os.path.basename(picked)[: -len("_ftth-data.json")]

        # 推断数据集标识：优先 PM 编码（与前端既有数据集命名一致），回退文件前缀
        try:
            data = json.loads(open(picked, encoding="utf-8").read())
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法解析 {os.path.basename(picked)}：\n{e}")
            return
        guess = (data.get("summary", {}) or {}).get("pm_code") \
            or (data.get("pm_list") or [None])[0] or file_tag
        counts = (f"箱体 {len(data.get('boites') or [])} · "
                  f"光缆 {len(data.get('cables') or [])} · "
                  f"站点 {len(data.get('sites') or [])}")

        tag, ok = QInputDialog.getText(
            self, "同步到 S1",
            f"待同步：{os.path.basename(picked)}\n本次内容：{counts}\n"
            f"目标后端：{self.sync_engine.api_url}\n\n"
            "数据集标识（S1 前端下拉里显示的 key，同名会覆盖）：",
            text=str(guess))
        if not ok or not tag.strip():
            return
        tag = tag.strip()

        self._btn_ftth_sync.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            success, detail = self.sync_engine.upload_ftth_from_dir(
                out_dir, tag, file_tag=file_tag, label=f"{tag} · QGIS 同步")
        finally:
            QApplication.restoreOverrideCursor()
            self._btn_ftth_sync.setEnabled(True)

        if success:
            c = detail.get("counts") or {}
            files = detail.get("written") or []
            verified = "已通过（服务端回读比对一致）" if detail.get("verified") else "未通过，请核对后端数据目录"
            body = (
                f"数据集：{tag}\n"
                f"写入文件：{', '.join(files) if files else '（内容未变，跳过写盘）'}\n"
                f"服务端计数：箱体 {c.get('boites')} · 光缆 {c.get('cables')} · "
                f"站点 {c.get('sites')} · PM {c.get('pm')}\n"
                f"校验回环：{verified}\n"
                f"落盘目录：{detail.get('data_dir')}\n\n"
                "打开 S1 Web 端「FTTH 竣工数据」页，点【从后端刷新】即可看到本次成果。"
            )
            if detail.get("idempotent"):
                body = "内容与上次同步完全一致，服务端已幂等跳过。\n\n" + body
            QMessageBox.information(self, "同步成功", body)
            self._log(f"FTTH 成果已同步到 S1：{tag}（{counts}），校验回环"
                      f"{'通过' if detail.get('verified') else '未通过'}")
        else:
            QMessageBox.critical(
                self, "同步失败",
                f"{detail}\n\n排查顺序：\n"
                f"1. M03 后端是否已启动（{self.sync_engine.api_url}）\n"
                "2. 环境变量 M03_API_KEY 是否与后端 m03.api-key 一致\n"
                "3. 后端 FTTH_DATA_DIR 指向的目录是否可写\n\n"
                "本次数据已存入本地上传队列（~/.qgis_plugin_cache/upload_queue.json），不会丢失。")
            self._log(f"FTTH 同步失败：{detail}")

    # ------------------------------------------------------------------
    # 联动查询 (FTTH ↔ 基站/管线/机房)：点击画布高亮附近两类要素
    # ------------------------------------------------------------------
    def _toggle_linkage(self, checked):
        canvas = self.iface.mapCanvas()
        if not self._linkage_active:
            # 进入联动模式：清掉其它地图工具
            for t in (getattr(self, '_station_tool', None),
                      getattr(self, '_room_tool', None),
                      getattr(self, '_extent_tool', None)):
                try:
                    if t is not None:
                        canvas.unsetMapTool(t)
                except Exception:
                    pass
            self._linkage_tool = LinkageQueryTool(canvas)
            self._linkage_tool.point_clicked.connect(self._on_linkage_clicked)
            canvas.setMapTool(self._linkage_tool)
            self._linkage_active = True
            self._linkage_btn.setText("联动查询：开（点地图）")
            self._linkage_btn.setStyleSheet(btn_qss("success"))
            self._log("联动查询已开启：点击地图，高亮附近的 FTTH 与基站/管线/机房要素")
        else:
            if self._linkage_tool is not None:
                canvas.unsetMapTool(self._linkage_tool)
            self._linkage_active = False
            self._linkage_btn.setText("联动查询：关")
            self._linkage_btn.setStyleSheet(btn_qss("warn"))
            self._clear_linkage()
            self._log("联动查询已关闭")

    def _clear_linkage(self):
        """清除上一次联动高亮。"""
        for rb in self._linkage_rubberbands:
            try:
                rb.reset()
            except Exception:
                pass
        self._linkage_rubberbands = []

    def _linkage_highlight_feature(self, layer, feat, color, width=2.5):
        """安全高亮单个要素（兼容 QGIS 3.44 多部件几何 API）。"""
        rb = QgsRubberBand(self.iface.mapCanvas(), layer.geometryType())
        rb.setColor(color)
        rb.setWidth(width)
        rb.setBrushStyle(Qt.NoBrush)
        geom = QgsGeometry(feat.geometry().constGet().clone())
        if not QgsWkbTypes.isMultiType(geom.wkbType()):
            rb.addGeometry(geom, layer)
        else:
            abs_geom = geom.constGet()
            for i in range(abs_geom.partCount()):
                part = abs_geom.geometryN(i)
                if part is not None:
                    rb.addGeometry(QgsGeometry(part.clone()), layer)
        self._linkage_rubberbands.append(rb)
        return rb

    def _on_linkage_clicked(self, lon, lat):
        """点击画布后的联动逻辑。"""
        canvas = self.iface.mapCanvas()
        canvas_crs = canvas.mapSettings().destinationCrs()
        radius_m = float(self._linkage_radius.value())

        # 清理缓存里已被用户删除的 FTTH 层，避免点击联动时触发
        # "wrapped C/C++ object has been deleted" 崩溃
        from ftth.coverage_gap import _live_layers
        self._ftth_layers = _live_layers(self._ftth_layers)

        self._clear_linkage()

        # 点击点在画布 CRS
        click_pt = QgsPointXY(lon, lat)

        # 收集待查询图层：(layer, 颜色, 类别名)
        targets = []
        # 基站设计
        for lyr in QgsProject.instance().mapLayersByName("基站设计"):
            targets.append((lyr, QColor(0, 120, 255), "基站"))
        # 通信管线
        for lyr in QgsProject.instance().mapLayersByName("通信管线"):
            targets.append((lyr, QColor(0, 120, 255), "管线"))
        # FTTH 8 层
        for name, lyr in (self._ftth_layers or {}).items():
            targets.append((lyr, QColor(239, 68, 68), "FTTH"))

        counters = {}
        for layer, color, category in targets:
            if layer is None:
                continue
            layer_crs = layer.crs()
            # 阈值换算：地理坐标系按纬度近似（1°≈111320m），投影系按米
            if layer_crs.isGeographic():
                lat0 = click_pt.y()
                deg_per_m_lat = 1.0 / 111320.0
                deg_per_m_lon = 1.0 / (111320.0 * max(0.01, abs(math.cos(math.radians(lat0)))))
                # 取较保守的（经度方向）作为统一阈值
                threshold = radius_m * min(deg_per_m_lat, deg_per_m_lon)
            else:
                threshold = radius_m
            # 点击点 → 图层 CRS
            xform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            lp = xform.transform(click_pt)
            pt_geom = QgsGeometry.fromPointXY(lp)
            cnt = 0
            for feat in layer.getFeatures():
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                # 把要素几何也转到点击点同一 CRS 再算距（直接用图层CRS内算距离）
                d = geom.distance(pt_geom)
                if d <= threshold:
                    self._linkage_highlight_feature(layer, feat, color)
                    cnt += 1
            if cnt:
                counters[category] = counters.get(category, 0) + cnt

        # 机房（仅内存坐标，按经纬度近似判断）
        rooms = getattr(self, 'machine_rooms', []) or []
        if rooms:
            room_hits = 0
            for rm in rooms:
                try:
                    rlon, rlat = float(rm.longitude), float(rm.latitude)
                except Exception:
                    continue
                # 经纬度近似距离（米）
                dy = (rlat - lat) * 111320.0
                dx = (rlon - lon) * 111320.0 * math.cos(math.radians(lat))
                if math.hypot(dx, dy) <= radius_m:
                    rb = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
                    rb.setColor(QColor(0, 120, 255))
                    rb.setFillColor(QColor(0, 120, 255))
                    rb.setIcon(QgsRubberBand.ICON_DIAMOND)
                    rb.setIconSize(13)
                    rb.addPoint(QgsPointXY(rlon, rlat))
                    self._linkage_rubberbands.append(rb)
                    room_hits += 1
            if room_hits:
                counters["机房"] = counters.get("机房", 0) + room_hits

        # 联动查询属性侧栏（P1-#5）：点选后展示统计与归属，形成信息闭环
        info_lines = []
        if not counters:
            info_lines.append(f"{radius_m:.0f}m 内未找到任何基站 / 管线 / 机房 / FTTH 要素。")
            self._log(f"联动查询：{radius_m:.0f}m 内未找到任何基站/管线/机房/FTTH 要素")
        else:
            parts = []
            if counters.get("FTTH"):
                parts.append(f"FTTH {counters['FTTH']} 个（红）")
            if counters.get("基站"):
                parts.append(f"基站 {counters['基站']} 个（蓝）")
            if counters.get("管线"):
                parts.append(f"管线 {counters['管线']} 条（蓝）")
            if counters.get("机房"):
                parts.append(f"机房 {counters['机房']} 个（蓝）")
            summary = "；".join(parts)
            self._log(f"联动查询({radius_m:.0f}m)：{summary}")
            info_lines.append(f"高亮统计：{summary}")
            # 归属机房（本次新建）：列出命中半径内的机房名，形成信息闭环
            hit_rooms = []
            for rm in rooms:
                try:
                    rlon = float(getattr(rm, "longitude", 0))
                    rlat = float(getattr(rm, "latitude", 0))
                except Exception:
                    continue
                dy = (rlat - lat) * 111320.0
                dx = (rlon - lon) * 111320.0 * math.cos(math.radians(lat))
                if math.hypot(dx, dy) <= radius_m:
                    hit_rooms.append(getattr(rm, "name", getattr(rm, "room_id", "")))
            if hit_rooms:
                info_lines.append("归属机房（命中）：" + "、".join(hit_rooms))
            info_lines.append("红 = FTTH 现网，蓝 = 本次新建设施；"
                              "可在图层面板查看各要素完整属性表。")
        if hasattr(self, "_linkage_info"):
            self._linkage_info.setText("\n".join(info_lines))

    # ------------------------------------------------------------------
    # S1 增强：覆盖缺口识别 + 智能建议站点（真实数据 → 设计输入）
    # ------------------------------------------------------------------
    def _on_coverage_gap(self):
        """读取真实 FTTH 覆盖区，找出未覆盖楼栋，智能建议新增 NRO 站点。"""
        from qgis.PyQt.QtWidgets import QMessageBox
        from qgis.gui import QgsRubberBand
        from qgis.core import (QgsProject, QgsPointXY, QgsWkbTypes,
                                QgsCoordinateTransform)
        from ftth.coverage_gap import (
            analyze_coverage_gap,
            build_suggested_sites_layer,
            _live_layers,
        )

        # 清理缓存里已被用户在图层面板删除的层（避免 "wrapped C/C++ object
        # has been deleted" 崩溃），并保持 self._ftth_layers 为最新活层集合
        self._ftth_layers = _live_layers(self._ftth_layers)
        if not self._ftth_layers:
            QMessageBox.warning(
                self, "覆盖缺口",
                "FTTH 图层已全部从工程中移除，无法分析。\n"
                "请重新点击「加载并符号化 FTTH 图层」后再试。")
            return

        # 覆盖区面(ZNRO/ZPM)被删除 → 缺口功能无法判断覆盖，明确提示
        missing_cover = [n for n in ("ZNRO", "ZPM") if n not in self._ftth_layers]
        if missing_cover and "IMB" in self._ftth_layers:
            QMessageBox.information(
                self, "覆盖缺口",
                f"覆盖区图层 {', '.join(missing_cover)} 已从工程中移除，"
                "缺口功能无法判断楼栋是否被覆盖。\n\n"
                "若要临时排除覆盖区（例如想看缺口效果），请在图层面板用"
                "『眼睛图标』隐藏图层，而不要删除它——隐藏的图层仍参与分析。\n"
                "若确实要测试缺口，请加载一份『覆盖不全』的片区数据。")
            return

        self._set_status("覆盖缺口识别中…", busy=True)
        QApplication.processEvents()
        # S1 #1：读取需求评分权重（无投诉/路测数据时加权不生效，行为不变）
        try:
            weights = {
                "w1": float(self.w1_spin.value()),
                "w2": float(self.w2_spin.value()),
                "w3": float(self.w3_spin.value()),
            }
        except Exception:
            weights = None
        try:
            result = analyze_coverage_gap(self._ftth_layers, weights=weights)
        except Exception as exc:
            self._log(f"覆盖缺口识别失败：{exc}")
            QMessageBox.critical(
                self, "覆盖缺口识别失败",
                f"分析过程中出错：\n{type(exc).__name__}: {exc}\n\n"
                "请检查 FTTH 图层字段是否完整（含 ZNRO/ZPM 覆盖区与 IMB 楼栋），或稍后重试。"
            )
            self._set_status("就绪", busy=False)
            return

        if not result["has_coverage"]:
            self._log("覆盖缺口识别：未找到 ZNRO/ZPM 覆盖区面，无法判断缺口。")
            self._set_status("就绪", busy=False)
            QMessageBox.information(
                self, "覆盖缺口识别",
                "未找到 ZNRO / ZPM 覆盖区面，无法判断楼栋是否被覆盖。\n\n"
                "请确认第②步已成功「加载并符号化 FTTH 图层」，且图层面板中存在名为 "
                "ZNRO、ZPM 的覆盖区面图层（不要删除，仅可隐藏）。\n\n"
                "若确实没有覆盖区数据，则缺口识别功能无意义，可跳过本步直接进入第④步框选设计区域。")
            return

        try:
            # 1) 红框高亮缺口楼栋（清掉上次的）
            self._clear_gap_rubberbands()
            canvas = self.iface.mapCanvas()
            rb = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
            rb.setColor(QColor(239, 68, 68))
            rb.setFillColor(QColor(239, 68, 68))
            rb.setIcon(QgsRubberBand.ICON_CIRCLE)
            rb.setIconSize(9)
            for lon, lat, nb, code in result["gap_features"]:
                rb.addPoint(QgsPointXY(lon, lat))
            self._gap_rubberbands = [rb]

            # 2) 生成建议站点内存图层（清掉上次的）
            old = getattr(self, "_suggested_sites_layer", None)
            if old is not None:
                QgsProject.instance().removeMapLayer(old.id())

            gap_cnt = result["gap"]
            sugg_sites = result["suggested_sites"]

            if gap_cnt == 0:
                # ── 全覆盖：没有缺口 → 不创建空图层，给明确弹窗提示 ──
                self._suggested_sites_layer = None
                self._log(f"覆盖缺口识别完成：全部 {result['total_imb']} 栋 IMB 均在 ZNRO/ZPM "
                          f"覆盖区内，无缺口。建议站点图层未创建（无需新建 NRO）。")
                self._log("   提示：当前 FTTH 数据为已部署完整网络，覆盖区已包含所有楼栋。"
                          "如需测试缺口功能，可手动隐藏 ZNRO/ZPM 图层后重试，或加载仅部分覆盖的片区数据。")
                QMessageBox.information(
                    self, "覆盖缺口识别",
                    f"识别完成：全部 {result['total_imb']} 栋 IMB 楼栋均已落在 ZNRO/ZPM "
                    f"覆盖区内，无覆盖缺口。\n\n"
                    "当前 FTTH 数据为已部署完整网络，无需新建补盲站点（不会生成建议站点图层）。\n\n"
                    "若想查看缺口演示效果，可二选一：\n"
                    "  ① 在图层面板用「眼睛图标」隐藏 ZNRO/ZPM 覆盖区（隐藏仍参与分析，"
                    "会判出全部楼栋为缺口）；\n"
                    "  ② 加载一份仅部分覆盖的片区数据再运行本功能。")
            else:
                # ── 关键修复：建议站点内存图层必须落在画布真实 CRS 下 ──
                # FTTH 数据 .prj 虽标 EPSG:4326，实际坐标常是投影网格(extent 出现
                # ±90 之外的纬度)。若画布 CRS ≠ 4326，硬写 4326 会让图层被重投影到
                # 错误位置 → 青色菱形在地图上"消失"（而红圈 RubberBand 用画布原始
                # 坐标绘制，不受影响，所以缺口红圈能看见、建议站点看不见）。
                # 这里取画布目标 CRS，并把站点点从 IMB 源 CRS 变换过去，确保对齐。
                canvas_crs_auth = "EPSG:4326"
                xform = None
                if self.iface is not None:
                    try:
                        canvas = self.iface.mapCanvas()
                        canvas_crs = canvas.mapSettings().destinationCrs()
                        if canvas_crs is not None and canvas_crs.isValid() and canvas_crs.authid():
                            canvas_crs_auth = canvas_crs.authid()
                        imb = self._ftth_layers.get("IMB")
                        imb_crs = imb.crs() if imb is not None else None
                        if imb_crs is not None and imb_crs.isValid() and \
                                imb_crs.authid() and imb_crs.authid() != canvas_crs_auth:
                            xform = QgsCoordinateTransform(
                                imb_crs, canvas_crs, QgsProject.instance())
                            self._log(f"[建议站点] IMB CRS={imb_crs.authid()} ≠ 画布 "
                                      f"CRS={canvas_crs_auth}，已启用坐标变换对齐。")
                    except Exception as ce:
                        self._log(f"[建议站点] 取画布/IMB CRS 失败（回退 4326）: {ce}")

                layer = build_suggested_sites_layer(
                    result, crs=canvas_crs_auth, transform=xform)
                QgsProject.instance().addMapLayer(layer)
                self._suggested_sites_layer = layer
                self._style_suggested_sites(layer)

                # 诊断日志：确认图层确实生成、要素数与范围
                self._log(f"[建议站点] 图层已加入工程: name={layer.name()}, "
                          f"CRS={layer.crs().authid()}, 要素数={layer.featureCount()}, "
                          f"extent=({layer.extent().xMinimum():.4f},{layer.extent().yMinimum():.4f})-"
                          f"({layer.extent().xMaximum():.4f},{layer.extent().yMaximum():.4f})")

                # 缩放画布到"缺口红圈 + 建议站点"联合范围，确保操作员立即看到标记
                if self.iface is not None and layer.featureCount() > 0:
                    try:
                        canvas = self.iface.mapCanvas()
                        ext = layer.extent()
                        if not ext.isEmpty():
                            # 稍微扩大范围（15%边距），避免标记贴边
                            ext.scale(1.15)
                            canvas.setExtent(ext)
                            canvas.refresh()
                            self._log(f"[建议站点] 已缩放画布到建议站点范围并刷新。")
                    except Exception:
                        pass  # 缩放失败不影响主流程
                self._log(f"覆盖缺口识别：楼栋 {result['total_imb']} | 已覆盖 {result['covered']} | "
                          f"缺口 {gap_cnt}（红圈）")
                self._log(f"→ 智能建议在 {len(sugg_sites)} 处新增 NRO 候选站点（亮青色菱形，已加入图层，"
                          f"字段含覆盖楼栋数、住户容量与需求评分）")
                for s in sugg_sites:
                    self._log(f"   建议站点: 覆盖 {s['imb_cnt']} 栋 | 需求评分 "
                              f"{s.get('demand_score', 0):.3f} "
                              f"(投诉 {s.get('complaint_cnt', 0)} 处, "
                              f"路测弱覆盖占比 {s.get('roadtest_area_frac', 0):.2f})")
            self._mark_step_done(2)   # 第③步完成态闭环
        except Exception as exc:
            self._log(f"覆盖缺口高亮/出图失败：{exc}")
            QMessageBox.critical(
                self, "覆盖缺口渲染失败",
                f"缺口已计算但渲染高亮时出错：\n{type(exc).__name__}: {exc}"
            )
        finally:
            self._set_status("就绪", busy=False)

    def _on_gen_demo_feedback(self):
        """S1 #1：在已加载 IMB 楼栋的同一坐标系内，合成『投诉点』+『路测弱覆盖』
        演示数据，用于演示「需求评分选址」。真实数据到位后替换 COMPLAINT/ROADTEST
        图层即可，无需改代码。"""
        from qgis.PyQt.QtWidgets import QMessageBox
        from qgis.core import (QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
                               QgsField, QgsPointXY)
        from qgis.PyQt.QtCore import QVariant
        import random
        from ftth.coverage_gap import _live_layers

        self._ftth_layers = _live_layers(self._ftth_layers)
        imb = self._ftth_layers.get("IMB")
        if imb is None:
            # 第②步尚未加载 IMB 楼栋：自动生成虚拟楼栋兜底，使第③步可独立演示
            imb = self._ensure_virtual_imb()
            if imb is None:
                QMessageBox.warning(
                    self, "演示数据",
                    "无法生成虚拟楼栋数据，请先在第②步「加载并符号化 FTTH 图层」"
                    "（需要 IMB 楼栋图层），再生成演示投诉/路测数据。")
                return

        pts = []
        for f in imb.getFeatures():
            g = f.geometry()
            if g is not None and not g.isEmpty():
                try:
                    p = g.asPoint()
                    pts.append((p.x(), p.y()))
                except Exception:
                    pass
        if not pts:
            QMessageBox.warning(self, "演示数据", "IMB 图层中没有有效的点要素。")
            return

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
        jitter = span * 0.004        # 投诉点散布半径（占跨度 0.4%）
        r_radius = span * 0.012      # 路测弱覆盖区半径（占跨度 1.2%）
        crs = imb.crs().authid() or "EPSG:4326"
        random.seed(42)

        # 移除旧的演示图层（同 key），避免重复叠加
        project = QgsProject.instance()
        for key in ("COMPLAINT", "ROADTEST"):
            old = self._ftth_layers.get(key)
            if old is not None:
                try:
                    project.removeMapLayer(old.id())
                except Exception:
                    pass

        # ── 投诉点图层（Point）──
        comp = QgsVectorLayer(f"Point?crs={crs}", "S1-演示投诉点", "memory")
        cpr = comp.dataProvider()
        cpr.addAttributes([QgsField("id", QVariant.Int),
                           QgsField("type", QVariant.String)])
        comp.updateFields()
        cfeats = []
        cid = 0
        sample = random.sample(pts, max(1, int(len(pts) * 0.18)))
        for bx, by in sample:
            for _ in range(random.randint(1, 3)):
                ox = bx + random.uniform(-jitter, jitter)
                oy = by + random.uniform(-jitter, jitter)
                f = QgsFeature()
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(ox, oy)))
                cid += 1
                f.setAttributes([cid, "投诉-弱覆盖"])
                cfeats.append(f)
        cpr.addFeatures(cfeats)
        comp.updateExtents()

        # ── 路测弱覆盖图层（Polygon）──
        rt = QgsVectorLayer(f"Polygon?crs={crs}", "S1-演示路测弱覆盖", "memory")
        rpr = rt.dataProvider()
        rpr.addAttributes([QgsField("id", QVariant.Int),
                           QgsField("rsrp", QVariant.String)])
        rt.updateFields()
        rfeats = []
        rid = 0
        clusters = random.sample(pts, max(1, int(len(pts) * 0.06)))
        for bx, by in clusters:
            cx = bx + random.uniform(-jitter * 2, jitter * 2)
            cy = by + random.uniform(-jitter * 2, jitter * 2)
            r = r_radius * random.uniform(0.6, 1.4)
            ring = [QgsPointXY(cx - r, cy - r), QgsPointXY(cx + r, cy - r),
                    QgsPointXY(cx + r, cy + r), QgsPointXY(cx - r, cy + r),
                    QgsPointXY(cx - r, cy - r)]
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPolygonXY([ring]))
            rid += 1
            f.setAttributes([rid, "RSRP<-110"])
            rfeats.append(f)
        rpr.addFeatures(rfeats)
        rt.updateExtents()

        project.addMapLayer(comp)
        project.addMapLayer(rt)
        self._ftth_layers["COMPLAINT"] = comp
        self._ftth_layers["ROADTEST"] = rt

        # 简单符号化：投诉点红色、弱覆盖半透明红面
        try:
            comp.renderer().symbol().setColor(QColor(220, 38, 38))
            rt.renderer().symbol().setColor(QColor(239, 68, 68, 90))
            comp.triggerRepaint()
            rt.triggerRepaint()
        except Exception:
            pass

        self._log(f"已生成演示反馈数据：投诉点 {comp.featureCount()} 个、路测弱覆盖区 "
                  f"{rt.featureCount()} 处（坐标系 = IMB: {crs}）。")
        QMessageBox.information(
            self, "演示数据",
            f"已合成『投诉点』{comp.featureCount()} 个 + 『路测弱覆盖』{rt.featureCount()} 处，"
            "已加入图层并在本次缺口分析中生效。\n\n"
            "运行「覆盖缺口识别 · 智能建议站点」即可看到建议站点按需求评分偏移、并标注需求分。\n"
            "（真实投诉/路测数据到位后，替换 COMPLAINT / ROADTEST 图层即可，无需改代码。）")

    def _ensure_virtual_imb(self):
        """第③步未加载真实 IMB 时的虚拟楼栋兜底。

        在默认演示区（摩洛哥卡萨布兰卡附近，EPSG:4326）合成一批虚拟楼栋点
        内存层（含 CODE / NB_LOC_TOT 字段），套 IMB 样式后加入画布，并缓存到
        self._ftth_layers["IMB"]。返回该层；失败返回 None。

        真实数据到位后，第②步加载的 IMB 会优先（本方法仅在缺失时调用），
        无需改此处代码。
        """
        from qgis.core import (
            QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
            QgsField, QgsPointXY, QgsCoordinateReferenceSystem,
        )
        from qgis.PyQt.QtCore import QVariant
        from ftth.qgis_style import make_renderer

        # 演示区中心：卡萨布兰卡附近（与 docs 中的 FTTH 真实样本地理一致）
        cx, cy = -7.5898, 33.5731
        step = 0.004          # 楼栋间距（约 400m @4326）
        n = 12                # 12 x 12 = 144 栋虚拟楼栋
        crs = "EPSG:4326"

        layer = QgsVectorLayer(f"Point?crs={crs}", "S1-虚拟楼栋(IMB)", "memory")
        pr = layer.dataProvider()
        pr.addAttributes([
            QgsField("CODE", QVariant.String),
            QgsField("NB_LOC_TOT", QVariant.Int),
        ])
        layer.updateFields()

        feats = []
        code_i = 0
        import random
        random.seed(7)
        for i in range(n):
            for j in range(n):
                lon = cx + (i - n / 2) * step + random.uniform(-step * 0.2, step * 0.2)
                lat = cy + (j - n / 2) * step + random.uniform(-step * 0.2, step * 0.2)
                f = QgsFeature()
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
                code_i += 1
                f.setAttributes([f"IMB-{code_i:03d}", random.randint(8, 60)])
                feats.append(f)
        pr.addFeatures(feats)
        layer.updateExtents()
        layer.setCrs(QgsCoordinateReferenceSystem(crs))
        layer.setRenderer(make_renderer("IMB"))

        project = QgsProject.instance()
        project.addMapLayer(layer)
        self._ftth_layers["IMB"] = layer
        self._log(f"已生成虚拟楼栋兜底：{layer.featureCount()} 栋（演示坐标 "
                  f"EPSG:4326，中心点 {cx:.4f},{cy:.4f}）。")
        return layer

    def _clear_gap_rubberbands(self):
        for rb in getattr(self, "_gap_rubberbands", []) or []:
            try:
                self.iface.mapCanvas().scene().removeItem(rb)
            except Exception:
                pass
        self._gap_rubberbands = []

    def _on_clear_gap(self):
        """第 3 步『清除缺口标记』：红圈 + 建议站点图层一起清掉"""
        from qgis.core import QgsProject

        had = bool(getattr(self, "_gap_rubberbands", None)) or \
            getattr(self, "_suggested_sites_layer", None) is not None

        self._clear_gap_rubberbands()

        sugg = getattr(self, "_suggested_sites_layer", None)
        if sugg is not None:
            try:
                QgsProject.instance().removeMapLayer(sugg.id())
            except Exception:
                pass
            self._suggested_sites_layer = None

        try:
            self.iface.mapCanvas().refresh()
        except Exception:
            pass

        self._log("已清除覆盖缺口标记与建议站点图层" if had else "当前没有缺口标记可清除")

    def _style_suggested_sites(self, layer):
        """给 S1 建议站点图层套高对比度符号：亮青色菱形 + 外发光 + 大尺寸，
        与已有的 IMB(粉)/NRO(黄)/SITE(黄) 等圆点形成强烈视觉区分。
        同时启用标注（显示覆盖楼栋数），确保操作员在地图上能快速识别。"""
        from qgis.core import (QgsSingleSymbolRenderer, QgsFillSymbol,
                                QgsSimpleMarkerSymbolLayer, QgsSimpleLineSymbolLayer,
                                QgsMarkerSymbol, QgsLineSymbol,
                                QgsTextFormat, QgsTextBufferSettings,
                                QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
        # ── 底层：半透明白色光晕（大圆，模拟发光） ──
        halo = QgsSimpleMarkerSymbolLayer()
        halo.setShape(QgsSimpleMarkerSymbolLayer.Circle)
        halo.setSize(14)              # 加大光晕范围，远距离也能注意到
        halo.setColor(QColor(0, 212, 255, 60))   # 亮青色 24% 不透明
        halo.setStrokeStyle(Qt.PenStyle.NoPen)

        # ── 顶层：实心亮青色菱形 + 深色描边（加大一号） ──
        diamond = QgsSimpleMarkerSymbolLayer()
        diamond.setShape(QgsSimpleMarkerSymbolLayer.Diamond)
        diamond.setSize(9)             # 比普通站点标记大一倍
        diamond.setColor(QColor(0, 200, 255))     # 亮青色 #00C8FF
        diamond.setStrokeColor(QColor(0, 80, 120))  # 深青色描边（加粗对比）
        diamond.setStrokeWidth(2.0)

        symbol = QgsMarkerSymbol([halo, diamond])
        renderer = QgsSingleSymbolRenderer(symbol)
        layer.setRenderer(renderer)

        # ── 启用标注：显示 "NRO-n (覆盖x栋)" ──
        try:
            settings = QgsPalLayerSettings()
            settings.fieldName = "\"id\" || ' (覆盖' || \"imb_cnt\" || '栋,需求' || \"demand_score\" || ')'"
            settings.enabled = True
            # 文字格式
            text_format = QgsTextFormat()
            text_format.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            text_format.setColor(QColor(0, 120, 180))
            buffer = QgsTextBufferSettings()
            buffer.setEnabled(True)
            buffer.setColor(QColor(255, 255, 255, 200))
            buffer.setSize(1.0)
            text_format.setBuffer(buffer)
            settings.setFormat(text_format)
            # 标注位置：右上偏移，避免遮挡标记中心
            settings.placement = QgsPalLayerSettings.QuadrantPosition.QUADRANT_ABOVE_RIGHT if hasattr(QgsPalLayerSettings.QuadrantPosition, 'QUADRANT_ABOVE_RIGHT') else 2
            settings.dist = 2
            settings.dataDefinedProperties().clear()  # 避免残留 DD 属性导致崩溃
            layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
            layer.setLabelsEnabled(True)
        except Exception:
            pass  # 标注失败不影响符号渲染

        # 强制刷新图例和画布
        layer.triggerRepaint()
        if self.iface is not None:
            self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    # ------------------------------------------------------------------
    # FTTH 画布符号化 (Q3) / 异常高亮 / 标准 PDF 出图 (Q5)
    # ------------------------------------------------------------------
    def _load_ftth_layers(self):
        """加载 8 个 FTTH Shape 图层并应用标准符号化(分类着色 + 半透明面)。"""
        from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
        from qgis.core import QgsProject
        from ftth.qgis_style import load_ftth_layers, apply_ftth_styles, combined_extent

        shape_dir = QFileDialog.getExistingDirectory(
            self, "选择 FTTH Shape 目录（含 8 个 .shp）", "")
        if not shape_dir:
            return
        # 清理上次的覆盖缺口标记/建议站点，避免与新区叠加混淆
        self._clear_gap_rubberbands()
        old_sugg = getattr(self, "_suggested_sites_layer", None)
        if old_sugg is not None:
            try:
                QgsProject.instance().removeMapLayer(old_sugg.id())
            except Exception:
                pass
            self._suggested_sites_layer = None
        self._set_status("FTTH 图层加载中…", busy=True)
        QApplication.processEvents()
        try:
            layers = load_ftth_layers(shape_dir)
            if not layers:
                QMessageBox.warning(self, "FTTH 图层",
                                    "未在该目录找到任何有效的 FTTH .shp 图层。")
                self._set_status("就绪", busy=False)
                return
            apply_ftth_styles(layers)

            project = QgsProject.instance()
            # 移除旧版同名图层，避免重复叠加
            for old in list(self._ftth_layers.values()):
                project.removeMapLayer(old.id())
            for name, layer in layers.items():
                project.addMapLayer(layer)

            self._ftth_layers = layers
            self._ftth_shape_dir = shape_dir

            # ② 增强：给 FTTH 锚点层(SITE/BOITE)补 served_room_id 字段，
            # 使固网↔机房可追溯（默认空，加机房时回填）
            self._add_ftth_room_field(layers)

            ext = combined_extent(layers)
            if ext is not None and not ext.isEmpty():
                self.iface.mapCanvas().setExtent(ext)
                self.iface.mapCanvas().refresh()

            counts = ", ".join(f"{n}={lyr.featureCount()}" for n, lyr in layers.items())
            QMessageBox.information(
                self, "FTTH 图层已加载",
                f"已加载并符号化 {len(layers)} 个 FTTH 图层:\n{counts}\n\n"
                f"调色板: PBO 青 / BPE 橙 / PM 金 / 配线缆 蓝 / 主干缆 绿")
            self._log(f"FTTH 图层已加载并符号化: {counts}")
            self._mark_step_done(1)   # 第②步完成态闭环
        except Exception as e:
            QMessageBox.critical(self, "FTTH 加载错误", str(e))
            self._log(f"FTTH 图层加载失败: {e}")
        finally:
            self._set_status("就绪", busy=False)

    def _highlight_ftth_anomalies(self):
        """运行 FTTH 自检，并在画布上红框高亮异常要素。"""
        from qgis.PyQt.QtWidgets import QMessageBox
        from qgis.core import QgsProject
        from ftth.loader import load_qgis
        from ftth.validate import validate_project
        from ftth.qgis_style import highlight_anomalies, clear_highlights

        if not self._ftth_layers:
            QMessageBox.warning(self, "FTTH 高亮",
                                "请先『加载并符号化 FTTH 图层』。")
            return
        try:
            # 基于已加载的 QGIS 图层构建拓扑，再跑自检
            proj = load_qgis(self._ftth_layers)
            report = validate_project(proj, shape_dir=self._ftth_shape_dir)
            anomalies = report.get("anomalies", {})
            summary = report.get("summary", {})

            # 清理上一次高亮
            clear_highlights(self._ftth_rubberbands)
            self._ftth_rubberbands = []
            canvas = self.iface.mapCanvas()
            self._ftth_rubberbands = highlight_anomalies(
                self._ftth_layers, anomalies, canvas)

            total = sum(len(v) for v in anomalies.values())
            detail = "; ".join(f"{k}={len(v)}" for k, v in anomalies.items() if v) \
                or "无"
            QMessageBox.information(
                self, "FTTH 自检完成",
                f"通过率: {summary.get('passed_rate', 0)}% "
                f"({summary.get('passed')}/{summary.get('total')})\n"
                f"异常要素总数: {total}\n按图层: {detail}\n"
                f"已在画布红框高亮。")
            self._log(f"FTTH 自检: 通过率 {summary.get('passed_rate')}%, "
                      f"异常要素 {total} 个，已高亮")
        except Exception as e:
            QMessageBox.critical(self, "FTTH 自检错误", str(e))
            self._log(f"FTTH 自检失败: {e}")

    def _export_ftth_pdf(self):
        """导出 FTTH 标准竣工 PDF(仅包含 8 个 FTTH 标准图层)。"""
        from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
        from qgis.core import QgsProject, QgsRectangle
        from design_engine.layout_export import create_ftth_drawing
        from ftth.qgis_style import combined_extent

        if not self._ftth_layers:
            QMessageBox.warning(self, "FTTH 出图",
                                "请先『加载并符号化 FTTH 图层』。")
            return
        import os
        default_dir = self._qsettings.value("ftth_export_dir", "", type=str)
        init_path = (os.path.join(default_dir, "FTTH_Plan_de_Reculement.pdf")
                     if default_dir else "FTTH_Plan_de_Reculement.pdf")
        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出 FTTH 标准竣工图", init_path, "PDF (*.pdf)")
        if not fpath:
            return
        self._qsettings.setValue("ftth_export_dir", os.path.dirname(fpath))
        try:
            # 优先用 FTTH 数据联合范围成图，避免底图把设计内容缩成一团
            ext = combined_extent(self._ftth_layers)
            if ext is None or ext.isEmpty():
                ext = self.iface.mapCanvas().extent()
            extent = QgsRectangle(ext.xMinimum(), ext.yMinimum(),
                                  ext.xMaximum(), ext.yMaximum())

            result = create_ftth_drawing(
                project=QgsProject.instance(),
                ftth_layers=self._ftth_layers,
                map_extent=extent,
                title="FTTH Plan de Reculement",
                output_path=fpath,
                paper_size="A3" if fpath.endswith(".pdf") else "A4",
                export_format="PDF",
                dpi=300,
            )
            if result:
                QMessageBox.information(self, "FTTH 出图成功", f"已导出到:\n{result}")
                self._log("FTTH 标准竣工 PDF 已导出")
            else:
                QMessageBox.warning(self, "FTTH 出图失败",
                                    "导出失败，请检查 QGIS Print Layout 支持。")
        except Exception as e:
            QMessageBox.critical(self, "FTTH 出图错误", str(e))
            self._log(f"FTTH 出图失败: {e}")

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
        # 路由类型：direct=直线, manhattan=曼哈顿(L型), optimal=成本最优(绕避让)
        idx = self.route_type_combo.currentIndex()
        route_type = {0: "direct", 1: "manhattan", 2: "optimal"}.get(idx, "direct")

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

        idx = self.route_type_combo.currentIndex()
        # 上传时 optimal 的几何已含绕行；route_type 字段用后端已知值 manhattan，避免未知枚举
        route_type = {0: "direct", 1: "manhattan", 2: "manhattan"}.get(idx, "direct")
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
                _new_qgs_field("site_id", QVariant.String),
                _new_qgs_field("name", QVariant.String),
                _new_qgs_field("site_type", QVariant.String),
                _new_qgs_field("tower_height", QVariant.Double),
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
    #  拓扑引擎成果接入（B线）：由后端 /generate 返回扇区覆盖 + 设备清单
    # =================================================================

    def _generate_layout(self):
        """生成基站布局：优先调用拓扑引擎；无后端或失败时本地六边形兜底。

        改进：兜底不再静默进行——会标记结果来源并向用户给出非阻塞提示，
        避免评委看到“正常出图”却不知实际是本地兜底结果。
        """
        prev_sites = len(self.generated_sites)
        engine_error = False
        try:
            self._load_engine_result()
        except Exception as e:
            engine_error = True
            self._log(f"拓扑引擎调用异常，改用本地生成: {e}")

        has_device_layout = bool(getattr(self, "_device_layout", None))
        if should_fallback_local(prev_sites, len(self.generated_sites), has_device_layout, engine_error):
            self._layout_source = "local"
            self._generate_hex_grid()
            self._notify_layout_source()
            return

        self._layout_source = "engine"
        self._log("已采用拓扑引擎生成结果")

    def _notify_layout_source(self):
        """非阻塞提示：本次基站布局来自本地兜底，而非拓扑引擎。"""
        title = "布局为本地兜底"
        detail = "拓扑引擎未返回有效结果，已用本地六边形布局生成。如需引擎方案请检查后端连接。"
        self._log(detail)
        if getattr(self, "iface", None) and hasattr(self.iface, "messageBar"):
            self.iface.messageBar().pushMessage(title, detail, level=Qgis.Warning)
        else:
            QMessageBox.information(self, title, detail)

    def _load_engine_result(self):
        """由拓扑引擎生成：调用后端 /generate，渲染扇区覆盖多边形 + 设备清单。"""
        if not self.selected_extent:
            QMessageBox.warning(self, "提示", "请先在第二步选择设计区域")
            return

        import math
        min_lon, min_lat, max_lon, max_lat = self.selected_extent
        center_lon = (min_lon + max_lon) / 2.0
        center_lat = (min_lat + max_lat) / 2.0
        mid_lat = math.radians(center_lat)
        width_m = abs(max_lon - min_lon) * 111320 * math.cos(mid_lat)
        height_m = abs(max_lat - min_lat) * 110540
        coverage_radius = max(int(width_m), int(height_m)) // 2

        band_key = self.band_combo.currentText()
        config = BAND_CONFIGS[band_key]
        try:
            site_type = self.type_combo.currentText().split("(")[1].rstrip(")")
        except Exception:
            site_type = "MACRO"

        params = {
            "projectId": 1,
            "schemeName": "拓扑引擎生成方案",
            "templateType": site_type.lower(),
            "centerLongitude": round(center_lon, 6),
            "centerLatitude": round(center_lat, 6),
            "coverageRadius": coverage_radius,
            "frequencyBand": band_key,
            "towerHeight": float(self.height_spin.value()),
            "gridSize": 200,
            "sectorCount": self.sector_spin.value(),
        }

        self._log("调用拓扑引擎生成设计方案...")
        self._show_progress(True, 20)
        try:
            ok, data = self.sync_engine.generate_design(params)
            self._show_progress(True, 80)
            if not ok:
                QMessageBox.warning(self, "生成失败", str(data))
                self._log(f"拓扑引擎调用失败: {data}")
                self._show_progress(False)
                return

            sites = data.get("sites") or []
            device_layout = data.get("deviceLayout") or []
            self._device_layout = device_layout  # 供第九步报表复用
            self._log(f"拓扑引擎生成 {len(sites)} 个站点，设备清单 {len(device_layout)} 条")

            cov_sites = [s for s in sites if s.get("coveragePolygons")]
            if cov_sites:
                self._add_coverage_polygons_to_map(cov_sites)
                self._log(f"已渲染 {sum(len(s['coveragePolygons']) for s in cov_sites)} 个扇区覆盖多边形")
            else:
                self._log("后端未返回扇区覆盖多边形（可能走本地回退，无引擎成果）")

            # 渲染基站站点本身（修复：此前仅渲染扇区多边形+设备清单，
            # 未把站点落图，导致“只有设备清单、地图上没基站”）
            normalized = self._normalize_engine_sites(sites)
            if normalized:
                self.generated_sites = normalized
                self._add_sites_to_map(normalized)
                for s in normalized:
                    self._ensure_room_under_site(s)
                self._update_site_table()
                self.design_completed.emit(normalized)
                self._log(f"已在地图渲染 {len(normalized)} 个基站")
            else:
                self._log("后端未返回有效站点坐标，地图未生成基站（仅设备清单）")

            self._show_device_bom_dialog(device_layout, sites)
            self._show_progress(False)
        except Exception as e:
            self._log(f"错误: {e}")
            QMessageBox.critical(self, "生成失败", str(e))
            self._show_progress(False)

    def _normalize_engine_sites(self, sites):
        """把拓扑引擎返回的 sites 归一化为本地 generated_sites 字典 schema。

        后端字段多为 siteId/siteName/longitude/latitude/siteType/towerHeight；
        本地需要 site_id/name/longitude/latitude/site_type/tower_height。
        缺少经纬度时尝试用 coveragePolygons 质心兜底；仍拿不到则跳过该站。
        """
        if not sites:
            return []
        out = []
        valid_types = {"MACRO", "SMALL", "INDOOR"}

        def _centroid(polys):
            pts = []
            for poly in (polys or []):
                if isinstance(poly, list):
                    for p in poly:
                        if isinstance(p, (list, tuple)) and len(p) >= 2:
                            try:
                                pts.append((float(p[0]), float(p[1])))
                            except (TypeError, ValueError):
                                pass
            if not pts:
                return None
            n = len(pts)
            return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n

        for s in sites:
            if not isinstance(s, dict):
                continue
            lon = s.get("longitude")
            lat = s.get("latitude")
            if lon is None or lat is None:
                c = _centroid(s.get("coveragePolygons"))
                if c is None:
                    self._log(f"跳过无坐标站点: {s.get('siteId', s.get('site_id', '?'))}")
                    continue
                lon, lat = c
            try:
                lon = float(lon)
                lat = float(lat)
            except (TypeError, ValueError):
                continue
            st = str(s.get("siteType") or s.get("site_type")
                      or s.get("type") or "MACRO").upper()
            if st not in valid_types:
                st = "MACRO"
            th = s.get("towerHeight") or s.get("tower_height") or s.get("height")
            try:
                th = float(th) if th is not None else float(self.height_spin.value())
            except (TypeError, ValueError):
                th = float(self.height_spin.value())
            sid = s.get("siteId") or s.get("site_id") or ""
            name = s.get("siteName") or s.get("name") or sid or "站点"
            out.append({
                "site_id": sid,
                "name": name,
                "longitude": lon,
                "latitude": lat,
                "tower_height": th,
                "site_type": st,
                "num_sectors": self.sector_spin.value(),
                "is_valid": True,
            })
        return out

    def _add_coverage_polygons_to_map(self, sites):
        """将拓扑引擎返回的扇区覆盖多边形渲染为 QGIS 矢量图层。"""
        from qgis.PyQt.QtCore import QVariant
        from qgis.core import QgsFillSymbol, QgsSingleSymbolRenderer

        layer_name = "扇区覆盖(拓扑引擎)"
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer = layers[0]
            layer.startEditing()
            layer.deleteFeatures(layer.allFeatureIds())
        else:
            layer = QgsVectorLayer("Polygon?crs=EPSG:4326", layer_name, "memory")
            layer.dataProvider().addAttributes([
                _new_qgs_field("site_id", QVariant.String),
                _new_qgs_field("sector", QVariant.Int),
            ])
            layer.updateFields()
            symbol = QgsFillSymbol.createSimple({
                'color': '#4aa3ff55',
                'outline_color': '#4aa3ff',
                'outline_width': '0.4',
            })
            layer.setRenderer(QgsSingleSymbolRenderer(symbol))
            QgsProject.instance().addMapLayer(layer)

        layer.startEditing()
        feats = []
        for s in sites:
            site_id = s.get("siteId") or s.get("site_id") or ""
            for idx, poly in enumerate(s.get("coveragePolygons") or []):
                if not isinstance(poly, list) or len(poly) < 3:
                    continue
                ring = []
                for pt in poly:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        try:
                            ring.append(QgsPointXY(float(pt[0]), float(pt[1])))
                        except (TypeError, ValueError):
                            continue
                if len(ring) < 3:
                    continue
                geom = QgsGeometry.fromPolygonXY([ring])
                if geom.isEmpty() or not geom.isGeosValid():
                    continue
                feat = QgsFeature(layer.fields())
                feat.setGeometry(geom)
                feat.setAttributes([site_id, idx + 1])
                feats.append(feat)
        layer.addFeatures(feats)
        layer.commitChanges()
        layer.updateExtents()
        layer.triggerRepaint()

    def _show_device_bom_dialog(self, device_layout, sites):
        """以信息面板（表格）展示拓扑引擎设备清单 deviceLayout。"""
        if not device_layout:
            QMessageBox.information(
                self, "设备清单",
                "后端未返回设备拓扑清单（deviceLayout 为空）。\n"
                "可能为本地回退生成，未走拓扑引擎，无设备级产出。"
            )
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("拓扑引擎设备清单")
        dlg.setMinimumSize(580, 420)
        dlg.setStyleSheet("QDialog{background:#fafafa;}")
        layout = QVBoxLayout(dlg)
        tip = QLabel(f"共 {len(device_layout)} 条设备（来自拓扑引擎 deviceLayout）")
        tip.setStyleSheet("font-size:12px;padding:4px;color:#334155;")
        layout.addWidget(tip)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["所属站点", "设备名称", "设备类型", "方位角°", "下倾角°"])
        table.setRowCount(len(device_layout))
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for i, d in enumerate(device_layout):
            table.setItem(i, 0, QTableWidgetItem(str(d.get("parentDevice") or "")))
            table.setItem(i, 1, QTableWidgetItem(str(d.get("deviceName") or "")))
            table.setItem(i, 2, QTableWidgetItem(str(d.get("deviceType") or "")))
            table.setItem(i, 3, QTableWidgetItem(
                str(d.get("azimuth")) if d.get("azimuth") is not None else ""))
            table.setItem(i, 4, QTableWidgetItem(
                str(d.get("downtilt")) if d.get("downtilt") is not None else ""))
        table.horizontalHeader().setStretchLastSection(True)
        table.resizeColumnsToContents()
        layout.addWidget(table)
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(btn_qss("default"))
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        apply_glossary_tips(dlg)
        dlg.exec_()

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
        apply_glossary_tips(dlg)
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
        """设计报告：基于当前已生成的全部数据（基站+机房+FTTH+管线+BOM），
        在本地汇成一份 Markdown 专业总结报告，不依赖外部 AI 服务。"""
        if not self.generated_sites and not self.machine_rooms:
            QMessageBox.warning(self, "提示", "请先生成基站方案或添加机房")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("设计报告")
        dlg.setMinimumSize(700, 560)
        dlg.setStyleSheet("QDialog{background:#fafafa;}")
        layout = QVBoxLayout(dlg)
        status = QLabel("正在汇总数据…")
        status.setStyleSheet("color:#64748b;font-size:12px;padding:4px;")
        layout.addWidget(status)
        md_view = QTextEdit()
        md_view.setReadOnly(True)
        layout.addWidget(md_view)
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(btn_qss("default"))
        close_btn.clicked.connect(dlg.accept)

        btn_row = QHBoxLayout()
        export_docx_btn = QPushButton("导出 DOCX")
        export_docx_btn.setStyleSheet(btn_qss("accent"))
        export_docx_btn.setToolTip(
            "将本报告导出为 Word (.docx) 文档（含标题/表格/列表，零依赖生成）")
        export_docx_btn.clicked.connect(lambda: self._export_report_docx())
        btn_row.addWidget(export_docx_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        QApplication.processEvents()
        try:
            markdown = self._build_local_design_report()
            self._last_report_markdown = markdown
            status.setText("报告已生成（%s）" % datetime.now().strftime("%H:%M:%S"))
            if hasattr(md_view, "setMarkdown"):
                md_view.setMarkdown(markdown)
            else:
                md_view.setPlainText(markdown)
        except Exception as e:
            status.setText("生成出错")
            md_view.setPlainText("报告生成失败: %s" % str(e))
            self._log(f"本地报告生成失败: {e}")

        apply_glossary_tips(dlg)
        dlg.exec_()

    def _analyze_signal_strength(self):
        """基于当前基站布局，用 Okumura-Hata 模型采样覆盖栅格，
        统计 RSRP 信号强弱分布（与「生成覆盖热力图」同源逻辑）。

        :return: dict（含 grades/avg_rsrp/coverage_rate/blind_rate 等），失败返回 None
        """
        sites = self.generated_sites or []
        if not sites:
            return None
        try:
            band_combo = getattr(self, "band_combo", None)
            if not band_combo:
                return None
            band_key = band_combo.currentText()
            config = BAND_CONFIGS.get(band_key)
            if not config:
                return None
            height_spin = getattr(self, "height_spin", None)
            tower_height = height_spin.value() if height_spin else 35.0
            scenario_combo = getattr(self, "scenario_combo", None)
            scenario = (scenario_combo.currentText().split("(")[1].rstrip(")")
                        if scenario_combo else "URBAN")
            radius_km = config.ideal_isr_km * 1.5

            all_rsrp = []
            for site in sites:
                data = generate_coverage_heatmap_data(
                    site_lon=site.get("longitude", 0),
                    site_lat=site.get("latitude", 0),
                    tx_height_m=tower_height,
                    frequency_mhz=config.frequency_mhz,
                    tx_power_w=config.default_power_w,
                    antenna_gain_dbi=config.default_gain_dbi,
                    radius_km=radius_km,
                    resolution_m=150,
                    rsrp_threshold_dbm=-110,
                    environment=scenario,
                )
                for d in data:
                    all_rsrp.append(d["rsrp"])

            if not all_rsrp:
                return None

            total = len(all_rsrp)
            grades = [
                ("优 (Excellent)", "≥ -65 dBm",
                 len([r for r in all_rsrp if r >= -65])),
                ("良 (Good)", "-80 ~ -65 dBm",
                 len([r for r in all_rsrp if -80 <= r < -65])),
                ("中 (Fair)", "-90 ~ -80 dBm",
                 len([r for r in all_rsrp if -90 <= r < -80])),
                ("差 (Poor)", "-100 ~ -90 dBm",
                 len([r for r in all_rsrp if -100 <= r < -90])),
                ("盲区 (None)", "< -100 dBm",
                 len([r for r in all_rsrp if r < -100])),
            ]
            avg = round(sum(all_rsrp) / total, 1)
            covered = len([r for r in all_rsrp if r >= -80])
            blind = len([r for r in all_rsrp if r < -100])
            return {
                "total": total,
                "avg_rsrp": avg,
                "coverage_rate": round(covered / total * 100, 1),
                "blind_rate": round(blind / total * 100, 1),
                "grades": grades,
                "radius_km": round(radius_km, 2),
                "scenario": scenario,
                "band_key": band_key,
            }
        except Exception as e:
            self._log("信号强弱分析失败: %s" % e)
            return None

    def _build_local_design_report(self) -> str:
        """从当前全部设计数据中汇出一份 Markdown 专业总结报告。"""
        from models.site import Site
        L = []  # 报告行

        # ── 标题 ──
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        L.append("# 通信设施智能设计方案报告")
        L.append("")
        L.append("> 生成时间：%s | 数据来源：QGIS 插件本地汇总" % now)
        L.append("")

        # ── 一、项目概况 ──
        L.append("## 一、项目概况")
        L.append("")
        sites = self.generated_sites or []
        # 防御性统一：MachineRoom(dataclass) / dict → 全部转为 dict，避免 .get() 报错
        raw_rooms = self.machine_rooms or []
        rooms = []
        for r in raw_rooms:
            if isinstance(r, dict):
                rooms.append(r)
            elif hasattr(r, 'to_dict'):
                rooms.append(r.to_dict())
            elif hasattr(r, 'room_id'):
                rooms.append({
                    'room_id': getattr(r, 'room_id', ''),
                    'name': getattr(r, 'name', '机房'),
                    'room_type': getattr(r, 'room_type', '汇聚机房'),
                    'longitude': float(getattr(r, 'longitude', 0)),
                    'latitude': float(getattr(r, 'latitude', 0)),
                    'capacity': getattr(r, 'capacity', 50.0),
                    'power_supply': getattr(r, 'power_supply', 'AC220V'),
                    'served_site_id': getattr(r, 'served_site_id', None),
                })
            else:
                rooms.append(r)  # 兜底
        pipes = self.generated_pipelines or []
        ftth = getattr(self, 'ftth_design', None)

        cur_sc = getattr(self, 'scenario_combo', None)
        scenario_text = cur_sc.currentText() if cur_sc else "未选择"
        band_text = getattr(self, 'band_combo', None)
        freq_band = band_text.currentText() if band_text else "未选择"
        tech_text = getattr(self, 'tech_combo', None)
        tech_gen = tech_text.currentText() if tech_text else "未选择"

        mode = getattr(self, '_build_mode', None) or "brownfield"
        mode_cn = "新区新建（Greenfield）" if mode == "greenfield" else "现网补盲（Brownfield）"

        extent = getattr(self, 'selected_extent', None)
        area_desc = ""
        if extent and len(extent) == 4:
            area_desc = ("设计区域：%.4f°E ~ %.4f°E，%.4f°N ~ %.4f°N"
                        % (extent[0], extent[2], extent[1], extent[3]))

        L.append("| 项目 | 内容 |")
        L.append("|------|------|")
        L.append("| 建设模式 | %s |" % mode_cn)
        L.append("| 场景类型 | %s |" % scenario_text.replace("(", "（").rstrip(")") if "(" in scenario_text else scenario_text)
        L.append("| 通信制式 | %s |" % tech_gen)
        L.append("| 工作频段 | %s |" % freq_band)
        L.append("| 基站数量 | **%d 个** |" % len(sites))
        L.append("| 机房数量 | **%d 个** |" % len(rooms))
        L.append("| 管线数量 | **%d 条** |" % len(pipes))
        if area_desc:
            L.append("| %s |" % area_desc.replace("|", "\\|").replace("：", "| ").replace("，", ", "))
        L.append("")

        # ── 二、基站设计明细 ──
        if sites:
            L.append("## 二、基站设计明细")
            L.append("")
            type_map = {'MACRO': '宏站', 'SMALL': '微站', 'INDOOR': '室分'}
            mount_map = {'GROUND': '地面塔', 'ROOFTOP': '楼面塔'}
            L.append("| 站点ID | 名称 | 类型 | 安装方式 | 塔高(m) | 频段 | 制式 | 经度 | 纬度 |")
            L.append("|--------|------|------|----------|---------|------|------|------|------|")
            for s in sites:
                stype = s.get('site_type', 'MACRO')
                mt = s.get('mount_type', 'GROUND')
                L.append("| %s | %s | %s | %s | %.1f | %s | %s | %.4f | %.4f |" % (
                    s.get('site_id', '-'),
                    s.get('name', '-'),
                    type_map.get(stype, stype),
                    mount_map.get(mt, mt),
                    float(s.get('tower_height', 0)),
                    s.get('band', '-'),
                    s.get('tech_generation', tech_gen),
                    float(s.get('longitude', 0)),
                    float(s.get('latitude', 0)),
                ))
            L.append("")

        # ── 三、机房配置 ──
        if rooms:
            L.append("## 三、机房配置")
            L.append("")
            L.append("| 机房ID | 名称 | 类型 | 经度 | 纬度 | 归属站点 |")
            L.append("|--------|------|------|------|------|----------|")
            for r in rooms:
                L.append("| %s | %s | %s | %.4f | %.4f | %s |" % (
                    r.get('room_id', '-'), r.get('name', '-'),
                    r.get('room_type', '-'),
                    float(r.get('longitude', 0)), float(r.get('latitude', 0)),
                    r.get('served_site_id', '-')))
            L.append("")

        # ── 四、FTTH 光接入设计（仅 greenfield）──
        if ftth and isinstance(ftth, dict) and "stats" in ftth:
            L.append("## 四、FTTH 光接入设计统计")
            L.append("")
            st = ftth["stats"]
            L.append("| 指标 | 数值 | 说明 |")
            L.append("|------|------|------|")
            L.append("| OLT / 机房锚点 | **%d** 个 | 光信号起点 |" % st.get('olt_count', 0))
            L.append("| 光交箱 (FD) | **%d** 个 | 分光节点 |" % st.get('fd_count', 0))
            L.append("| 覆盖楼栋 (IMB) | **%d** 栋 | 覆盖对象 |" % st.get('building_count', 0))
            L.append("| 主干光缆 | **%d** 段 / **%.2f** km | 机房→FD |" % (st.get('trunk_cables', 0), st.get('trunk_length_km', 0)))
            L.append("| 入户光缆 | **%d** 段 / **%.2f** km | FD→楼栋 |" % (st.get('drop_cables', 0), st.get('drop_length_km', 0)))
            L.append("")
            L.append("**FD 接入方式**：每个光交箱连接最近基站下方的机房（trunk），符合实际工程逻辑。")
            L.append("")

        # ── 五、物料清单 (BOM) ──
        if sites:
            L.append("## 五、物料清单 (BOM)")
            L.append("")
            bom_all = []
            for s in sites:
                st = Site(
                    site_id=s.get('site_id', ''), name=s.get('name', ''),
                    longitude=float(s.get('longitude', 0)), latitude=float(s.get('latitude', 0)),
                    site_type=s.get('site_type', 'MACRO'),
                    tower_type=s.get('tower_type', 'MONOPOLE'),
                    tower_height=float(s.get('tower_height', 35)),
                    mount_type=s.get('mount_type', 'GROUND'),
                )
                bom = st.bill_of_materials()
                mt_cn = '楼面塔' if bom['mount_type'] == 'ROOFTOP' else '地面塔'
                for it in bom['items']:
                    bom_all.append((s.get('site_id', ''), mt_cn, it['name'], it['spec'],
                                    it['qty'], it['unit']))
            if bom_all:
                L.append("| 站点 | 安装方式 | 物料名称 | 规格 | 数量 | 单位 |")
                L.append("|------|----------|----------|------|------|------|")
                for sid, mt, nm, sp, qty, unit in bom_all:
                    L.append("| %s | %s | %s | %s | %s | %s |" % (sid, mt, nm, sp, qty, unit))
                L.append("")
                # 汇总
                from collections import Counter
                item_counter = Counter()
                for _, _, nm, sp, qty, unit in bom_all:
                    item_counter[(nm, sp, unit)] += int(qty)
                L.append("### 物料汇总")
                L.append("")
                L.append("| 物料名称 | 规格 | 总数量 | 单位 |")
                L.append("|----------|------|--------|------|")
                for (nm, sp, unit), total in sorted(item_counter.items()):
                    L.append("| %s | %s | **%s** | %s |" % (nm, sp, total, unit))
                L.append("")

        # ── 六、管线工程量 ──
        if pipes:
            L.append("## 六、管线工程量")
            L.append("")
            try:
                cost_summary = calculate_total_cost(pipes)
                L.append("| 指标 | 数值 |")
                L.append("|------|------|")
                L.append("| 管线总数 | **%d** 条 |" % cost_summary.get('管线总数', 0))
                L.append("| 总长度 | **%.2f** m |" % cost_summary.get('总长度(m)', 0))
                L.append("| 材料费合计 | **%.2f** 元 |" % cost_summary.get('材料费合计(元)', 0))
                L.append("| 施工费合计 | **%.2f** 元 |" % cost_summary.get('施工费合计(元)', 0))
                L.append("| 总成本 | **%.2f** 元 |" % cost_summary.get('总成本(元)', 0))
                L.append("| 每米成本 | **%.2f** 元/m |" % cost_summary.get('每米成本(元/m)', 0))
                L.append("")
            except Exception:
                L.append("*（管线成本计算异常，请以第九步导出的报表为准）*")
                L.append("")

        # ── 七、设备清单（拓扑引擎产物）──
        if getattr(self, '_device_layout', None):
            dev = self._device_layout
            L.append("## 七、设备清单（拓扑引擎）")
            L.append("")
            L.append("| 所属站点 | 设备名称 | 设备类型 | 方位角(°) | 下倾角(°) |")
            L.append("|----------|----------|----------|-----------|-----------|")
            for d in dev:
                L.append("| %s | %s | %s | %s | %s |" % (
                    d.get('parentDevice') or '-', d.get('deviceName') or '-',
                    d.get('deviceType') or '-',
                    str(d.get('azimuth')) if d.get('azimuth') is not None else '-',
                    str(d.get('downtilt')) if d.get('downtilt') is not None else '-',
                ))
            L.append("")

        # ── 八、信号覆盖分析与建议 ──
        L.append("## 八、信号覆盖分析与建议")
        L.append("")
        # 基于当前参数做定性分析
        band_key = freq_band
        bc = BAND_CONFIGS.get(band_key, BAND_CONFIGS.get("3.5GHz"))
        isr = getattr(bc, 'ideal_isr_km', 1.5) if bc else 1.5
        radius = getattr(bc, 'coverage_radius_km', 0.8) if bc else 0.8

        L.append("### 当前参数下的覆盖特性")
        L.append("")
        L.append("| 参数 | 当前值 | 行业参考范围 | 评估 |")
        L.append("|------|--------|-------------|------|")
        L.append("| 工作频段 | %s | 700MHz~26GHz | %s |" % (
            freq_band,
            "低频覆盖广、高频容量大" if any(f in freq_band for f in ['700', '800', '900']) else "中高频，适合密集城区"))
        L.append("| 覆盖半径 | %.2f km | 0.3~3.0 km | %s |" % (
            radius,
            "偏大，适合郊区/农村" if radius > 1.5 else "适中，适合城区" if radius > 0.7 else "偏小，适合高密度城区"))
        L.append("| 站间距 | %.2f km | 0.5~2.0 km | %s |" % (
            isr,
            "偏大，可能存在覆盖缝隙" if isr > 2.0 else "合理" if isr > 0.8 else "较密，重叠覆盖充足"))
        L.append("| 基站密度 | %.2f 站/km² | 0.3~3.0 站/km² | %s |" % (
            (len(sites) / max((isr * isr * 0.866), 0.01)) if sites and isr else 0,
            "偏低" if len(sites) < 3 else "适中" if len(sites) < 10 else "较高"))
        L.append("")

        # ── 信号强弱程度（RSRP 分布，与覆盖热力图同源）──
        sig = self._analyze_signal_strength()
        if sig:
            L.append("### 信号强弱程度（RSRP 分布）")
            L.append("")
            L.append("采用 **Okumura-Hata 传播模型** 计算各基站在覆盖栅格上的参考信号接收功率 "
                     "**RSRP(dBm)**（数值越大信号越强），按 %.2f km 半径、150m 分辨率采样，"
                     "环境类型 %s。信号等级划分与「生成覆盖热力图」完全一致。" % (
                         sig["radius_km"], sig["scenario"]))
            L.append("")
            meanings = {
                "优 (Excellent)": "可承载高速数据业务",
                "良 (Good)": "稳定通话与中速数据",
                "中 (Fair)": "基本可用、边缘体验",
                "差 (Poor)": "弱覆盖、易掉线",
                "盲区 (None)": "无覆盖、需补站",
            }
            L.append("| 信号等级 | RSRP 范围 | 覆盖栅格数 | 占比 | 含义 |")
            L.append("|----------|-----------|------------|------|------|")
            for name, rng, cnt in sig["grades"]:
                pct = cnt / sig["total"] * 100
                L.append("| %s | %s | %d | %.1f%% | %s |" % (
                    name, rng, cnt, pct, meanings.get(name, "-")))
            L.append("")
            L.append("- **平均 RSRP**：%s dBm" % sig["avg_rsrp"])
            L.append("- **有效覆盖率（RSRP ≥ −80 dBm）**：**%.1f%%**" % sig["coverage_rate"])
            L.append("- **覆盖盲区占比（RSRP < −100 dBm）**：%.1f%%" % sig["blind_rate"])
            L.append("")
            if sig["blind_rate"] > 10:
                L.append("**结论**：存在 %.1f%% 的覆盖盲区，建议加密基站或提升站高/功率以填补弱覆盖区。" % sig["blind_rate"])
            elif sig["coverage_rate"] < 90:
                L.append("**结论**：有效覆盖率 %.1f%%，边缘区域存在弱覆盖，建议按需补微站。" % sig["coverage_rate"])
            else:
                L.append("**结论**：有效覆盖率达 %.1f%%，整体信号良好，满足 %s 场景覆盖需求。" % (
                    sig["coverage_rate"], scenario_text.split("(")[0].strip()))
            L.append("")

        L.append("### 建议")
        L.append("")
        if not sites:
            L.append("- 请先在第五步生成基站布局，再查看本报告获取更详细的分析。")
        elif len(sites) < 3:
            L.append("- **站点偏少**：当前仅 %d 个基站，建议增加至 5-8 个以形成连续覆盖。" % len(sites))
            L.append("- 重点补盲方向：结合第三步的缺口分析和投诉热点区域布站。")
        else:
            L.append("- **覆盖连续性**：当前 %d 个基站按 %.2f km 站间距部署，基本满足 %s 场景覆盖需求。" % (
                len(sites), isr, scenario_text.split("(")[0].strip() if "(" in scenario_text else scenario_text))
            L.append("- **边缘区域**：设计区域边缘处信号可能弱于中心，建议后续通过路测验证并按需补微站。")
            L.append("- **容量预留**：若目标用户密度高于预期，可考虑将部分宏站升级为三扇区或增加微站补盲。")
        L.append("")
        L.append("---")
        L.append("")
        L.append("*本报告由 QGIS 通信设施智能设计插件自动生成，数据来源于当前设计方案。")
        L.append("*如需调整参数后重新生成报告，请修改第五步参数并重新点击「生成设计报告」。")

        return "\n".join(L)

    def _export_report_docx(self):
        """将当前设计报告导出为 Word (.docx) 文档（零依赖，纯标准库生成）。"""
        md = getattr(self, "_last_report_markdown", None)
        if not md:
            QMessageBox.information(
                self, "提示", "请先点击「生成设计报告」生成内容后再导出。")
            return
        default_name = "通信设施智能设计方案报告.docx"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出设计报告 (DOCX)", default_name, "Word 文档 (*.docx)")
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        try:
            markdown_to_docx(md, path)
            QMessageBox.information(self, "导出成功", "已导出 DOCX 报告：\n%s" % path)
            self._log("设计报告 DOCX 已导出: %s" % path)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", "DOCX 导出失败：%s" % str(e))
            self._log("DOCX 导出失败: %s" % e)

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
        """更新站点表格 — 13列专业字段"""
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
            mount_cn = {'GROUND': '地面塔', 'ROOFTOP': '楼面塔'}.get(
                s.get('mount_type', 'GROUND'), s.get('mount_type', '地面塔'))
            self.site_table.setItem(i, 12, item(mount_cn))

        self.stats_label.setText(f"站点: {len(sites)}")

    def _show_bom_dialog(self):
        """弹出物料清单(BOM)汇总对话框（按安装方式区分地面塔/楼面塔）。"""
        from models.site import Site
        if not self.generated_sites:
            QMessageBox.information(self, "物料清单", "请先生成基站方案")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("基站物料清单 (BOM)")
        dlg.setMinimumSize(580, 440)
        dlg.setStyleSheet("QDialog{background:#fafafa;}")
        layout = QVBoxLayout(dlg)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["站点", "安装方式", "物料", "规格", "数量/单位"])
        rows = []
        for s in self.generated_sites:
            st = Site(
                site_id=s.get('site_id', ''), name=s.get('name', ''),
                longitude=float(s.get('longitude', 0)), latitude=float(s.get('latitude', 0)),
                site_type=s.get('site_type', 'MACRO'),
                tower_type=s.get('tower_type', 'MONOPOLE'),
                tower_height=float(s.get('tower_height', 35)),
                mount_type=s.get('mount_type', 'GROUND'),
            )
            bom = st.bill_of_materials()
            mt_cn = '楼面塔' if bom['mount_type'] == 'ROOFTOP' else '地面塔'
            for it in bom['items']:
                rows.append((s.get('site_id', ''), mt_cn, it['name'], it['spec'],
                             f"{it['qty']} {it['unit']}"))
        table.setRowCount(len(rows))
        for i, (sid, mt, nm, sp, qty) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(str(sid)))
            table.setItem(i, 1, QTableWidgetItem(str(mt)))
            table.setItem(i, 2, QTableWidgetItem(str(nm)))
            table.setItem(i, 3, QTableWidgetItem(str(sp)))
            table.setItem(i, 4, QTableWidgetItem(str(qty)))
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(btn_qss("default"))
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        apply_glossary_tips(dlg)
        dlg.exec_()

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
