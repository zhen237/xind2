"""通信技术制式维度（4G/5G 信号特性）

专家反馈 #5 新增的「技术轴」：4G/5G 的覆盖半径、站间距、单站容量、塔桅形态不同。
本模块只做「规则/参数基线」，不绑定具体 UI 或引擎；由 design_dock / site / coverage 引用。

设计原则（与既有 BAND_CONFIGS 解耦、不破坏现网补盲演示）：
- 制式(tech) 是比 频段(band) 更高层的便捷预设：选定制式会预选一个合理默认频段，
  用户仍可手动微调频段。覆盖半径/站间距仍由 design_engine.rules.BAND_CONFIGS 驱动。
- 参数基线为「示例值」，行业校准后可在 TECH_BASELINE 单点修改。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class TechGeneration(Enum):
    """通信技术制式"""
    LTE4G = "4G LTE"
    NR5G_SUB6 = "5G NR(Sub-6)"
    NR5G_MMWAVE = "5G NR(mmWave)"
    MULTI = "4G+5G协同"


# 制式 → 默认频段（键须与 design_engine.rules.BAND_CONFIGS 一致）
TECH_DEFAULT_BAND = {
    TechGeneration.LTE4G: "2.6GHz",
    TechGeneration.NR5G_SUB6: "3.5GHz",
    TechGeneration.NR5G_MMWAVE: "4.9GHz",
    TechGeneration.MULTI: "3.5GHz",
}


# 单站设备 BOM 项（按制式追加，与 Site.bill_of_materials 的 mount_type 分支叠加）
@dataclass
class TechBaseline:
    coverage_radius_km: float       # 宏站覆盖半径（参考）
    suggested_spacing_km: float     # 建议站间距
    capacity_ref: float             # 单站容量参考（相对值 0-100，定性）
    tower_form: str                 # 塔桅/设备形态说明
    antenna_items: List[dict] = field(default_factory=list)  # BOM 设备项


# 技术维度参数基线（示例值，待行业校准）
TECH_BASELINE = {
    TechGeneration.LTE4G: TechBaseline(
        2.0, 1.2, 40.0, "RRU + 天线",
        [{"name": "4G RRU", "spec": "多频 4T4R", "qty": 1, "unit": "台"},
         {"name": "定向天线", "spec": "65° 18dBi", "qty": 1, "unit": "副"}],
    ),
    TechGeneration.NR5G_SUB6: TechBaseline(
        0.4, 0.3, 80.0, "AAU(有源天线)",
        [{"name": "5G AAU", "spec": "3.5GHz 64T64R", "qty": 1, "unit": "台"}],
    ),
    TechGeneration.NR5G_MMWAVE: TechBaseline(
        0.15, 0.12, 100.0, "小微站/灯杆站",
        [{"name": "5G mmWave 微站", "spec": "26/28GHz 4T4R", "qty": 1, "unit": "台"},
         {"name": "灯杆抱杆", "spec": "镀锌钢", "qty": 1, "unit": "套"}],
    ),
    TechGeneration.MULTI: TechBaseline(
        0.5, 0.4, 90.0, "多频天线/AAU",
        [{"name": "4G RRU", "spec": "多频 4T4R", "qty": 1, "unit": "台"},
         {"name": "5G AAU", "spec": "3.5GHz 64T64R", "qty": 1, "unit": "台"}],
    ),
}


def get_baseline(tech_str: str) -> TechBaseline:
    """按制式字符串（枚举 value，如 '5G NR(Sub-6)'）取基线；未知/缺省回退 4G+5G协同。"""
    for enum_val, base in TECH_BASELINE.items():
        if enum_val.value == tech_str:
            return base
    return TECH_BASELINE[TechGeneration.MULTI]


def default_band_for(tech_str: str) -> str:
    """制式 → 默认频段键（用于 design_dock 预选 band_combo）。"""
    for enum_val, band in TECH_DEFAULT_BAND.items():
        if enum_val.value == tech_str:
            return band
    return TECH_DEFAULT_BAND[TechGeneration.MULTI]
