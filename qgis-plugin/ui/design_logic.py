"""Design Dock 中与 QGIS/UI 无关的纯逻辑判定与路径处理。

抽离这些函数是为了：(1) 让 design_dock.py 的大类逐步瘦身；(2) 不依赖 QGIS
环境即可用 pytest 直接覆盖。所有函数必须是纯函数：相同输入 -> 相同输出，
不读写全局状态、不触达 self。
"""

# 报表格式键
CSV = "csv"
TXT = "txt"
XLSX = "xlsx"

# 出图类型键
DRAWING_PDF = "pdf"
DRAWING_FTTH = "ftth"
DRAWING_CAD = "cad"


def resolve_report_target(fpath, sel_filter):
    """根据保存对话框返回的路径与过滤器，归一化扩展名并判定格式。

    参数:
        fpath: 用户选择的路径（可能无扩展名，也可能为空）
        sel_filter: QFileDialog.getSaveFileName 返回的选中过滤器文本

    返回:
        (fpath, fmt)
        - fpath 为空字符串 -> ("", None) 表示用户取消
        - 否则补全省略的扩展名，并依据结尾判定 CSV / TXT
    """
    if not fpath:
        return "", None
    low = fpath.lower()
    # 已有可识别扩展名 -> 直接沿用，不受对话框过滤器干扰（避免叠加出
    # "方案A.csv.txt" 这种双扩展名）。格式由扩展名决定。
    if low.endswith(".csv"):
        return fpath, CSV
    if low.endswith(".xlsx"):
        return fpath, XLSX
    if low.endswith(".txt"):
        return fpath, TXT
    # 无扩展名 -> 按当前选中的过滤器补上对应扩展名并判定格式。
    if sel_filter.startswith("CSV"):
        return fpath + ".csv", CSV
    if sel_filter.startswith("Excel"):
        return fpath + ".xlsx", XLSX
    return fpath + ".txt", TXT


def drawing_type_for_index(index):
    """下拉索引 -> 图纸类型键。

    索引 1 = CAD 图纸(DXF/DWG)，其余（含 0）= 当前视图通用 PDF。
    """
    if index == 1:
        return DRAWING_CAD
    return DRAWING_PDF


def should_fallback_local(prev_sites, sites_after, has_device_layout, engine_error):
    """判定是否改用本地六边形布局兜底。

    规则（与 _generate_layout 原行为一致）：
        - 引擎调用抛异常 -> 兜底
        - 引擎未抛异常，但站点数相对调用前无变化且无设备清单 -> 兜底
        - 其余情况 -> 采用引擎结果

    参数:
        prev_sites: 调用引擎前 generated_sites 数量
        sites_after: 调用引擎后 generated_sites 数量
        has_device_layout: 引擎是否产出设备清单（_device_layout 是否真值）
        engine_error: 引擎调用是否抛异常
    """
    if engine_error:
        return True
    if sites_after == prev_sites and not has_device_layout:
        return True
    return False
