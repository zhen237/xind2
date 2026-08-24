"""Design Dock 界面文案与下拉选项常量。

集中管理原先散落在 design_dock.py 中的硬编码字符串，便于 i18n 与统一维护。
注意：BASEMAP_SOURCES 的顺序必须与design_dock._add_selected_basemap 的 dispatch
列表一一对应（索引 0=天地图影像, 1=天地图注记, 2=Esri, 3=OSM）。
"""

# 底图源（顺序与 dispatch 列表对应）
BASEMAP_SOURCES = [
    "天地图影像(国内)",
    "天地图注记",
    "Esri 卫星图(全球)",
    "OSM地图",
]

# 出图类型下拉（索引 0=当前视图通用PDF, 1=CAD图纸DXF/DWG）
DRAWING_TYPES = [
    "当前视图 (通用 PDF)",
    "CAD 图纸 (DXF / DWG)",
]

# 工程量报表保存对话框过滤器
REPORT_SAVE_FILTER = "Excel 工作簿 (*.xlsx);;文本文件 (*.txt)"

# 报表默认文件名前缀（实际文件名会追加日期）
REPORT_DEFAULT_NAME = "通信工程量报表"
