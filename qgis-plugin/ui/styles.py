"""QGIS 插件统一样式常量 — Flat UI 调色板

用途: 消除 design_dock.py 中 57 处分散的 setStyleSheet 调用，
     所有颜色和样式模板从此文件统一管理。

使用:
    from ui.styles import PluginTheme
    btn.setStyleSheet(PluginTheme.STEP_BTN)
    btn_generate.setStyleSheet(PluginTheme.danger_btn())
"""


class PluginTheme:
    """Flat UI 调色板 — 单一样式源"""

    # ── 基础色 ───────────────────────────────────────────────
    DARK_BG    = "#2c3e50"   # 左侧菜单背景
    DARK_HOVER = "#4a6a8a"   # 按钮 hover
    MID_BG     = "#34495e"   # 未选中按钮 / 日志区
    PRIMARY    = "#3498db"   # 选中 / 信息
    SUCCESS    = "#27ae60"   # 确认 / 成功 / BOM导出
    DANGER     = "#e74c3c"   # 危险操作 / 清除
    WARNING    = "#e67e22"   # 导出报表
    PURPLE     = "#9b59b6"   # 机房 / 热力图
    DARK_PURPLE = "#8e44ad"  # 按坐标添加机房
    TEAL       = "#1abc9c"   # 同步后端
    GRAY       = "#7f8c8d"   # 提示 / 说明
    LIGHT_GRAY = "#95a5a6"   # 次要说明
    WHITE      = "#ffffff"
    DARK_BLUE  = "#1a1a7a"   # 覆盖"很差"等级

    # ── 字体 ────────────────────────────────────────────────
    FONT_SMALL  = "font-size: 10px;"
    FONT_NORMAL = "font-size: 11px;"
    FONT_LABEL  = "font-size: 12px; font-weight: bold;"

    # ── 步骤按钮模板 (固定宽度侧边栏) ────────────────────────
    STEP_BTN = f"""
        QPushButton {{
            background-color: {MID_BG};
            color: {WHITE};
            border: none;
            padding: 8px;
            text-align: left;
            font-size: 11px;
        }}
        QPushButton:checked {{
            background-color: {PRIMARY};
        }}
        QPushButton:hover {{
            background-color: {DARK_HOVER};
        }}
    """

    # ── 操作按钮工厂 ────────────────────────────────────────
    @staticmethod
    def action_btn(color: str, padding: str = "10px",
                   font_size: str = "13px", width: str = None) -> str:
        """生成操作按钮样式"""
        width_rule = f"width: {width};" if width else ""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: {padding};
                font-size: {font_size};
                font-weight: bold;
                {width_rule}
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
            QPushButton:disabled {{
                background-color: #7f8c8d;
            }}
        """

    @staticmethod
    def primary_btn(text: str = None, width: str = None) -> str:
        return PluginTheme.action_btn(PluginTheme.PRIMARY, width=width)

    @staticmethod
    def success_btn(text: str = None, width: str = None) -> str:
        return PluginTheme.action_btn(PluginTheme.SUCCESS, width=width)

    @staticmethod
    def danger_btn(text: str = None, width: str = None) -> str:
        return PluginTheme.action_btn(PluginTheme.DANGER, width=width)

    @staticmethod
    def purple_btn(text: str = None, width: str = None) -> str:
        return PluginTheme.action_btn(PluginTheme.PURPLE, width=width)

    @staticmethod
    def teal_btn(text: str = None, width: str = None) -> str:
        return PluginTheme.action_btn(PluginTheme.TEAL, width=width)

    @staticmethod
    def warning_btn(text: str = None, width: str = None) -> str:
        return PluginTheme.action_btn(PluginTheme.WARNING, width=width)

    @staticmethod
    def gray_btn(text: str = None, width: str = None) -> str:
        return PluginTheme.action_btn(PluginTheme.GRAY, width=width)

    # ── 容器样式 ────────────────────────────────────────────
    PANEL = f"""
        QGroupBox {{
            border: 2px solid {PRIMARY};
            border-radius: 8px;
            margin-top: 12px;
            padding: 12px;
            font-weight: bold;
            color: {DARK_BG};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
        }}
    """

    # ── 日志区样式 ──────────────────────────────────────────
    LOG_AREA = f"""
        QTextEdit {{
            background-color: {MID_BG};
            color: {WHITE};
            border: none;
            font-size: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
        }}
    """

    # ── 状态栏样式 ──────────────────────────────────────────
    STATUS_BAR = f"color: {GRAY}; font-size: 10px; padding: 2px;"

    # ── 表格样式 ────────────────────────────────────────────
    TABLE = f"""
        QTableWidget {{
            gridline-color: {LIGHT_GRAY};
            font-size: 11px;
            alternate-background-color: #f8f9fa;
        }}
        QTableWidget::item:selected {{
            background-color: {PRIMARY};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {DARK_BG};
            color: white;
            padding: 4px;
            border: none;
            font-weight: bold;
        }}
    """

    # ── 进度条样式 ──────────────────────────────────────────
    PROGRESS_BAR = f"""
        QProgressBar {{
            border: 1px solid {PRIMARY};
            border-radius: 4px;
            background-color: {DARK_BG};
            text-align: center;
            color: {WHITE};
            font-size: 11px;
            height: 20px;
        }}
        QProgressBar::chunk {{
            background-color: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 {PRIMARY},
                stop: 0.5 {TEAL},
                stop: 1 {SUCCESS}
            );
            border-radius: 3px;
        }}
    """

    # 取消按钮（紧凑型，用于进度条旁边）
    CANCEL_BTN = f"""
        QPushButton {{
            background-color: transparent;
            color: {DANGER};
            border: 1px solid {DANGER};
            border-radius: 4px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: bold;
            min-width: 50px;
        }}
        QPushButton:hover {{
            background-color: {DANGER};
            color: {WHITE};
        }}
    """

    # ── 分隔线 ──────────────────────────────────────────────
    SEPARATOR = f"border-top: 1px solid {LIGHT_GRAY}; margin: 8px 0;"
