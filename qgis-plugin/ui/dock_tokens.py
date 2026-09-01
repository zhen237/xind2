# -*- coding: utf-8 -*-
"""通信设施智能设计面板 — 统一设计 Token（双主题）。

左侧菜单面板为**深色主题**，右侧内容面板为**浅色主题**。
此前所有颜色散落在 design_dock.py 各处，且 GLOBAL_STYLE 被挂到最外层 main 容器，
导致 `QLabel{color:#1e293b}`（深色字）级联到深色左面板，造成「建设模式」等标签看不见。

本模块把颜色集中为语义 Token，并提供**主题作用域样式函数**：
- dark_panel_style()  仅作用于左面板容器，内部 QLabel 用浅色字
- light_panel_style() 仅作用于右面板容器，内部 QLabel 用深色字
这样两种主题互不污染，业务代码里不再需要 ID 选择器 / QPalette 双重保险之类的 hack。
"""

# ---- 语义色（按钮 / 强调态，深浅主题通用） ----
# 每个语义色 = (常规背景, 悬停背景)
PALETTE = {
    "primary": ("#2f6df6", "#1d4fd0"),   # 主操作 · 蓝
    "accent":  ("#7c4dff", "#6234d6"),   # 强调 · 紫
    "success": ("#16a34a", "#11853b"),   # 成功 · 绿
    "danger":  ("#dc2626", "#b51c1c"),   # 危险/删除 · 红
    "warn":    ("#ea580c", "#c2410c"),   # 生成/导出 · 橙
    "teal":    ("#0d9488", "#0b7a70"),   # 同步 · 青
    "default": ("#475569", "#334155"),   # 次级 · 灰
}

# ---- 深色主题（左侧菜单面板） ----
DARK = {
    "bg": "#0f172a",            # 面板底
    "bg_card": "#1e293b",       # 步骤按钮底
    "bg_card_hover": "#334155", # 步骤按钮悬停
    "bg_active": "#3b82f6",     # 选中步骤底
    "text": "#f1f5f9",          # 主文字（浅）
    "text_muted": "#94a3b8",    # 次要文字
    "text_log": "#cbd5e1",      # 日志文字
    "border": "#475569",        # 边框
}

# ---- 浅色主题（右侧内容面板） ----
LIGHT = {
    "bg": "#ffffff",
    "text": "#1e293b",          # 主文字（深）
    "text_muted": "#7f8c8d",    # 说明文字
    "text_title": "#2c3e50",    # 步骤标题
    "border": "#e2e8f0",        # 输入控件边框
    "group_border": "#cbd5e1",  # 分组框边框
    "header_border": "#2f6df6", # 步骤标题左边框
    "grid": "#eef2f7",          # 表格网格线
    "header_bg": "#f1f5f9",     # 表头底
    "disabled_bg": "#334155",
    "disabled_text": "#94a3b8",
}


def btn_qss(kind="default", *, checkable=False):
    """生成语义化按钮样式表（主操作/强调/危险/成功/警告/同步/次级）。"""
    bg, hover = PALETTE.get(kind, PALETTE["default"])
    checked = "QPushButton:checked{background-color:%s;}" % hover if checkable else ""
    return (
        "QPushButton{background-color:%s;color:#ffffff;border:none;border-radius:6px;"
        "padding:9px 12px;font-size:12px;font-weight:600;}"
        "QPushButton:hover{background-color:%s;}"
        "QPushButton:disabled{background-color:%s;color:%s;}"
        % (bg, hover, LIGHT["disabled_bg"], LIGHT["disabled_text"])
        + checked
    )


def dark_panel_style():
    """左侧深色菜单面板的容器样式（含 QPushButton + QLabel 主题色）。

    关键点：显式声明 `QLabel{color:%s}`，让深色面板里的所有标签用浅色字，
    不再依赖被错误级联的全局深色字。
    """
    d = DARK
    return (
        "QWidget{background-color:%s;}"
        "QLabel{color:%s;}"
        "QPushButton{"
        "  color:%s;text-align:left;font-size:13px;border:none;"
        "  padding:10px 12px;border-radius:6px;background-color:%s;font-weight:600;"
        "}"
        "QPushButton:hover{background-color:%s;color:%s;}"
        "QPushButton:checked{background-color:%s;color:%s;font-weight:700;}"
        % (
            d["bg"], d["text"], d["text"], d["bg_card"],
            d["bg_card_hover"], d["text"], d["bg_active"], d["text"],
        )
    )


def light_panel_style():
    """右侧浅色内容面板的容器样式（替代原 GLOBAL_STYLE，作用域限定在右面板）。

    不再挂到最外层 main，避免 `QLabel{color:#1e293b}` 污染深色左面板。
    """
    l = LIGHT
    return (
        "QWidget{font-family:'Microsoft YaHei','PingFang SC',-apple-system,sans-serif;}"
        "QLabel{color:%s;}"
        "QGroupBox{font-weight:700;color:%s;border:1px solid %s;border-radius:8px;"
        "  margin-top:12px;padding-top:8px;}"
        "QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 4px;}"
        "QComboBox,QSpinBox,QDoubleSpinBox{border:1px solid %s;border-radius:6px;"
        "  padding:5px 8px;background:%s;min-height:22px;}"
        "QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus{border-color:%s;}"
        "QTableWidget{border:1px solid %s;border-radius:8px;gridline-color:%s;}"
        "QHeaderView::section{background:%s;color:%s;font-weight:600;border:none;padding:5px;}"
        "QTextEdit{border:1px solid %s;border-radius:6px;}"
        "QProgressBar{border:1px solid %s;border-radius:6px;text-align:center;"
        "  background:%s;color:%s;}"
        "QProgressBar::chunk{background:%s;border-radius:5px;}"
        % (
            l["text"], l["text"], l["border"], l["group_border"], l["bg"],
            l["header_border"], l["border"], l["grid"], l["header_bg"],
            l["text_muted"], l["border"], l["border"], l["grid"], l["bg"],
            l["text_title"],
        )
    )


def group_style():
    """右侧浅色面板的 QGroupBox 样式（标题深色字，分组框浅色边框）。"""
    l = LIGHT
    return (
        "QGroupBox{font-size:12px;font-weight:700;color:%s;border:1px solid %s;"
        "border-radius:8px;margin-top:12px;padding-top:8px;}"
        "QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 4px;color:%s;}"
        % (l["text_title"], l["group_border"], l["text_title"])
    )
