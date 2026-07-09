"""QGIS 插件字符串枚举 — 消除硬编码字符串判断

用途: 将 "rect"/"hex" 等运行时字符串替换为类型安全的枚举值，
     避免拼写错误导致的静默 bug。

使用:
    from ui.enums import GridType, RouteType, ScenarioType

    if self.grid_type == GridType.HEX:
        ...
    combo.setCurrentText(GridType.RECT.value)
"""

from enum import Enum

# ── 从 models 导入标准 PipelineType（避免重复定义）─────────
from ..models.pipeline import PipelineType  # noqa: F401 — 由 models 统一管理

# ── 管线类型中文映射（中文显示值 → models.PipelineType）────
PIPELINE_TYPE_CN_MAP = {
    PipelineType.DIRECT_BURIED: "直埋光缆",
    PipelineType.DUCT: "通信管道",
    PipelineType.AERIAL: "架空光缆",
}

# ── 管线类型反向映射（中文 → 枚举值）──────────────────────
PIPELINE_TYPE_REVERSE_MAP = {v: k for k, v in PIPELINE_TYPE_CN_MAP.items()}


class GridType(str, Enum):
    """网格类型"""
    HEX = "hex"
    RECT = "rect"


class RouteType(str, Enum):
    """管线路由类型"""
    DIRECT = "direct"
    MANHATTAN = "manhattan"


class ScenarioType(str, Enum):
    """场景类型"""
    URBAN = "URBAN"
    SUBURBAN = "SUBURBAN"
    RURAL = "RURAL"


class BandType(str, Enum):
    """频段类型"""
    MHZ_700 = "700MHz"
    MHZ_3500 = "3.5GHz"


class StepName(str, Enum):
    """设计步骤名称"""
    BASE_MAP = "底图"
    AREA = "区域"
    PARAMS = "参数"
    SITES = "基站"
    PIPELINES = "管线"
    ANALYSIS = "分析"
    MACHINE_ROOM = "机房"


# ── 频段配置键名映射 ────────────────────────────────────────
BAND_KEYS = {
