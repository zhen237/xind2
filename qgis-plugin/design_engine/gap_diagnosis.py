"""补盲补热 · 第一档：诊断内核（纯计算，无 QGIS 依赖）。

本模块是「弱覆盖诊断 · 补站」功能的纯计算内核，负责：
    站点集合 → RSRP 采样栅格 → 弱覆盖/盲区分级 → 网格聚类 → 需求评分
    → 建议站 → 去重 → （UI 裸 dict / Site dataclass 参数）双 schema 映射。

设计约束
--------
* **不得 import qgis / qgis.PyQt**：本模块必须能在没有 QGIS 的普通 Python 环境
  下用 pytest 直接运行。
* **不引入任何新的第三方依赖**：栅格用纯 Python 的 ``list[list[float]]`` 表示
  （实现环境未安装 numpy；采用二维列表即可满足全量用例）。
* 复用既有算力：``design_engine.coverage.path_loss_with_directivity`` 提供扇区化
  路径损耗、``design_engine.coverage.okumura_hata_path_loss`` 提供全向路径损耗
  （本模块自行遍历采样点逐格取最强）；``design_engine.coverage.calculate_coverage_rate``
  负责可用覆盖率口径。

RSRP 口径（v1.7 · 用户批准，**仅诊断链**）
------------------------------------------
    RSRP = 发射功率dBm + 天线增益 − 路径损耗 − 8dB阴影衰落 − 链路余量
其中「链路余量」默认 20dB（干扰抬升 + 穿透损耗 + 边缘可靠性）。本口径与第⑦步
热力图（``coverage_heatmap`` / ``coverage.calculate_rsrp``，仅 8dB 阴影、且按全向满增益）
**有意不同**：诊断须反映真实弱覆盖，故按**站点自身的扇区数**（``num_sectors``）逐扇区
取最强；``num_sectors <= 0``（全向）时**不施加方向图损失**，用
``okumura_hata_path_loss`` 直接算路径损耗。并对每点再扣一次链路余量。

可用覆盖率口径（v1.7 · 用户批准）
--------------------------------
现状覆盖率改用「**RSRP ≥ 弱覆盖阈值**」定义（即 ``diagnose_weak_coverage`` 的
``weak_threshold_dbm``），改名「可用覆盖率」，与弱/盲判定同一刻度，满足
``可用覆盖率 + 弱覆盖占比 + 盲区占比 = 100%``。口径拆成两个 stats 键：
``coverage_caliber_label``（固定标签「可用覆盖率」）+ ``coverage_caliber``
（可组合描述，如 ``"RSRP >= -100.0 dBm"``）。下游如需完整口径串，自行组合
``f"{label}（{caliber}）"`` —— 不要在口径串里再塞标签，否则会出现「标签重复 + 括号嵌套」。

v1.5 口径修正（务必牢记，勿照抄文档历史版本）
--------------------------------------------
1. **聚类网格尺寸按频段**：``clamp(BAND_CONFIGS[band].ideal_isr_km × 1000, 100, 2000)``
   米 —— 700MHz→2000m / 2.6GHz→1000m / 3.5GHz→500m / 4.9GHz→300m。
2. **最小弱区栅格数按面积**：``max(1, round(0.2 × (cell_m / resolution_m)²))``
   —— 语义 = "聚类网格面积的 20%"。**不得**写成 ``max(20, 桶容量)``
   （4G 桶容量仅 16 < 20 → 恒不成立 → 永远无聚类）。
3. **去重距离**：``min(layout_isr_m / 2, 200)``，**不得写死 200**。
4. **RSRP 内核为「按站点扇区数 + 链路余量」**：逐站 × 逐扇区计算
   ``power_w_to_dbm(power) + gain − path_loss − 8 − link_margin_db`` 并逐格取最大。
   扇区方位角由站点 dict 的 ``num_sectors`` 推导（见 :func:`_azimuths_for_site`）：
   缺键回退 ``SECTOR_AZIMUTHS_DEG``，``num_sectors <= 0`` 视作全向、**不施加方向图损失**
   （改用 ``okumura_hata_path_loss``）。``link_margin_db`` 是 ``compute_rsrp_grid`` 的
   **显式参数**（默认 ``DEFAULT_LINK_MARGIN_DB = 20.0``，档2 将暴露为面板输入框），
   **不得写死**。未被任何站点覆盖的格子保持 ``NO_COVERAGE_DBM`` 哨兵初值。
5. **可用覆盖率**：``diagnose_weak_coverage`` 的 ``covered`` 条件为
   ``rsrp >= weak_threshold_dbm``（不再用写死的 -80）；``stats["coverage_caliber"]``
   记录口径字符串，``summarize_diagnosis`` 引用它、不得写死阈值。
"""
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .coverage import (
    calculate_coverage_rate,
    okumura_hata_path_loss,
    path_loss_with_directivity,
    power_w_to_dbm,
)
from .rules import BAND_CONFIGS

try:  # 直接运行/测试时（插件目录在 sys.path 上）走绝对导入
    from models.tech import default_band_for, get_baseline
except ImportError:  # pragma: no cover - 作为包内子模块导入时的回退
    from ..models.tech import default_band_for, get_baseline


# ─────────────────────────── 模块常量（示意值，待校准）───────────────────────────

DEFAULT_WEAK_THRESHOLD_DBM = -100.0     # 弱覆盖阈值默认值（可调）
DEFAULT_BLIND_THRESHOLD_DBM = -110.0    # 盲区阈值默认值（可调）
DEFAULT_RESOLUTION_M = 100              # 采样分辨率默认值（可调，沿用现有热力图口径）

# 【v1.7 · 用户批准】诊断链路的 RSRP 口径参数（**仅诊断链**，与第⑦步热力图有意不同）。
DEFAULT_LINK_MARGIN_DB = 20.0              # 链路余量默认值（干扰抬升+穿透损耗+边缘可靠性）
SHADOW_FADE_DB = 8.0                       # 阴影衰落余量，与 coverage.calculate_rsrp 默认值一致
# ⚠️ 语义收窄：SECTOR_AZIMUTHS_DEG 仅在**站点 dict 缺 'num_sectors' 键**时作为回退值；
#    站点带 num_sectors 时以站点为准（0 或负 = 全向，不施加方向图损失）。
SECTOR_AZIMUTHS_DEG = (0.0, 120.0, 240.0)  # 缺 num_sectors 时的回退方位角（3 扇区）
SECTOR_BEAMWIDTH_DEG = 65.0                # 水平波束宽度
MAX_SECTORS = 64                           # num_sectors 上限护栏（防面板填超大值把遍历跑死）

# 【v1.5】最小弱区面积占"聚类网格面积"的比例；等价：
#   min_cells = max(1, round(MIN_WEAK_AREA_RATIO × (cell_m / resolution_m)²))
# 替代 v1.0 的"≥3 栅格"（过松）与 v1.1 的 max(20, 桶容量)（过严到恒不成立）。
MIN_WEAK_AREA_RATIO = 0.2

# 【v1.5】去重距离**上限**；实际取 min(实际布站 ISR(m) ÷ 2, 本值)。
# ⚠️ 不得写死 200：4.9GHz 布站 ISR 仅 300m 时会把网格站全判为重复。
DEDUPE_DISTANCE_MAX_M = 200.0

NO_COVERAGE_DBM = -200.0                # 无覆盖哨兵值
MAX_CELLS_REF = 20                      # 面积项归一参考（示意值，待校准）

# 需求评分权重（示意值，待校准），集中定义便于单点校准。
DEFAULT_SCORE_WEIGHTS: Dict[str, float] = {"area": 0.4, "depth": 0.4, "blind": 0.2}

# （v1.7 起）现状覆盖率改用「RSRP ≥ 弱覆盖阈值」定义，故删除旧的写死 -80 常量
# _COVERAGE_OK_DBM；口径字符串见 diagnose_weak_coverage 的 stats["coverage_caliber"]。


# ───────────────────────────── 数据结构 ─────────────────────────────

@dataclass
class WeakCell:
    """一个被判为弱覆盖/盲区的采样栅格单元。"""

    row: int            # 栅格行号（自 bbox 北边界向下）
    col: int            # 栅格列号（自 bbox 西边界向右）
    lon: float          # 栅格中心经度（EPSG:4326，度）
    lat: float          # 栅格中心纬度（EPSG:4326，度）
    rsrp: float         # 该栅格最强 RSRP（dBm）
    level: str          # "weak"（< 弱覆盖阈值）| "blind"（< 盲区阈值）
    cell_m: float       # 采样栅格边长（米）= 采样分辨率，用于建面与面积统计


@dataclass
class RasterDiagnosis:
    """一次覆盖诊断的完整栅格结果（供图层渲染 + 聚类 + 统计）。

    说明：``grid`` 采用纯 Python 二维列表（``List[List[float]]``）而非 ndarray，
    以满足"无第三方依赖"约束。取值单位 dBm，无覆盖处为 ``NO_COVERAGE_DBM``。
    """

    grid: List[List[float]]                  # shape=(rows, cols)，值=dBm，无覆盖=-200.0
    geotransform: Tuple[float, ...]          # GDAL 风格 (lon_min, dx, 0, lat_max, 0, -dy)
    bbox: Tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    resolution_m: int                        # 采样分辨率（米）
    tech: str                                # 制式（TechGeneration.value）
    band_key: str                            # 频段键（与 rules.BAND_CONFIGS 对齐）
    weak_threshold_dbm: float = DEFAULT_WEAK_THRESHOLD_DBM    # 默认值，可调
    blind_threshold_dbm: float = DEFAULT_BLIND_THRESHOLD_DBM  # 默认值，可调
    no_coverage_dbm: float = NO_COVERAGE_DBM                  # 无覆盖哨兵值
    weak_cells: List[WeakCell] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)


@dataclass
class WeakCluster:
    """一个弱覆盖聚类（网格分桶后 ≥ min_cells 的片）。"""

    cluster_id: str            # "CLU-001"
    cell_key: Tuple[int, int]  # 网格桶键 (round(lon/cell_deg_lon), round(lat/cell_deg_lat))
    centroid_lon: float        # 需求加权质心经度（度）
    centroid_lat: float        # 需求加权质心纬度（度）
    cell_count: int            # 聚类内弱覆盖栅格数
    blind_count: int           # 其中盲区栅格数
    mean_rsrp: float           # 聚类内平均 RSRP（dBm）
    min_rsrp: float            # 聚类内最低 RSRP（dBm）
    demand_score: float        # 需求评分 0~100（见 score_cluster）
    cell_m: float              # 本次聚类网格尺寸（米）


@dataclass
class SuggestedSite:
    """一条建议站记录（聚类 → 一位建议站）。

    ``needs_review`` / ``review_note`` 为 T07（建议站避让过滤）扩展字段：
    落在避让区内的建议站**不静默丢弃**，只在此打标供人工复核。
    """

    suggest_id: str            # "SUG-001"（UI 展示用；采纳时才生成正式 site_id）
    longitude: float           # 建议站经度（= 聚类质心，EPSG:4326，度）
    latitude: float            # 建议站纬度（度）
    demand_score: float        # 需求评分 0~100
    suggested_radius_km: float # 建议覆盖半径（km）= TECH_BASELINE[tech].coverage_radius_km
    tech: str                  # 制式（TechGeneration.value）
    cell_count: int            # 聚类栅格数
    blind_count: int           # 聚类内盲区栅格数
    mean_rsrp: float           # 聚类平均 RSRP（dBm）
    band_key: str              # 频段键（默认取面板 band_combo，默认值，可调）
    cluster_id: str            # 溯源到 WeakCluster
    needs_review: bool = False  # T07：是否需人工复核（避让冲突）
    review_note: str = ""       # T07：复核原因文案


# ───────────────────────────── 内部工具 ─────────────────────────────

def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Haversine 距离（米）。"""
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _min_cells_for(cell_m: float, resolution_m: float) -> int:
    """最小弱区栅格数 = max(1, round(0.2 × (cell_m / resolution_m)²))。"""
    if resolution_m <= 0:
        raise ValueError("resolution_m 必须为正")
    ratio = MIN_WEAK_AREA_RATIO * (cell_m / resolution_m) ** 2
    return max(1, int(round(ratio)))


def _band_key_for_config(band_config) -> Optional[str]:
    """按频率把 BandConfig 反查为其在 BAND_CONFIGS 中的键。"""
    freq = getattr(band_config, "frequency_mhz", None)
    if freq is None:
        return None
    for key, cfg in BAND_CONFIGS.items():
        if cfg.frequency_mhz == freq:
            return key
    return None


def _site_lon_lat(site: dict) -> Tuple[float, float]:
    """从站点 dict 读取经纬度（容忍 lon/lat 别名）。"""
    lon = site.get("longitude", site.get("lon"))
    lat = site.get("latitude", site.get("lat"))
    if lon is None or lat is None:
        raise ValueError("站点缺少 longitude/latitude")
    return float(lon), float(lat)


def _azimuths_for_site(site: dict) -> Tuple[float, ...]:
    """按站点 dict 的 ``num_sectors`` 推导扇区方位角。

    - 站点 dict **不含** ``'num_sectors'`` 键 → 回退 ``SECTOR_AZIMUTHS_DEG``（向后兼容）
    - ``num_sectors <= 0``（含 0 = 全向）→ 返回 ``()``，表示**不施加方向图损失**
    - ``num_sectors = N > 0`` → ``tuple(i * 360.0 / N for i in range(N))``，起始 0°
      （``N`` 上限 ``MAX_SECTORS`` = 64；``N > 64`` 时**静默截断到 64**，不抛错——
      抛错会让整个诊断动作失败，比截断更糟。实测 6 扇区以上结果已饱和，故该上限
      对合法取值不产生任何结果差异，纯防跑死护栏。）

    ⚠️ ``0`` 是 falsy：**不能**用 ``int(site.get("num_sectors", 3))``，否则真正的 0
    （全向）会被误当成缺省，故必须先判键是否存在。
    """
    if "num_sectors" not in site:
        return SECTOR_AZIMUTHS_DEG
    try:
        num_sectors = int(site["num_sectors"])
    except (TypeError, ValueError):
        return SECTOR_AZIMUTHS_DEG
    if num_sectors <= 0:
        return ()
    num_sectors = min(num_sectors, MAX_SECTORS)  # 上限护栏：静默截断
    return tuple(i * 360.0 / num_sectors for i in range(num_sectors))


# ───────────────────────────── 对外接口 ─────────────────────────────

def grid_size_for_band(band_key: str) -> float:
    """聚类网格尺寸（米）= clamp(BAND_CONFIGS[band].ideal_isr_km × 1000, 100, 2000)。

    按**频段**取实际布站间距（语义 = 一个站点的覆盖单元尺度）。
    """
    cfg = BAND_CONFIGS.get(band_key)
    if cfg is None:
        return 100.0
    return float(min(max(cfg.ideal_isr_km * 1000.0, 100.0), 2000.0))


def grid_size_for_tech(tech: str, coverage_radius_km: Optional[float] = None) -> float:
    """兼容 §4.1 签名的聚类网格尺寸入口。

    v1.5 口径修正：网格尺寸**按频段**推导，故本函数解析 ``tech`` 的默认频段后
    委托给 :func:`grid_size_for_band`。``coverage_radius_km`` 参数为契约兼容而保留，
    不再参与计算（R-11：网格应等于站点实际覆盖单元尺度，与制式半径脱钩）。
    """
    return grid_size_for_band(default_band_for(tech))


def compute_rsrp_grid(
    sites: List[dict],
    bbox: Tuple[float, float, float, float],
    band_config,
    tech: str,
    resolution_m: int = DEFAULT_RESOLUTION_M,
    environment: str = "URBAN",
    link_margin_db: float = DEFAULT_LINK_MARGIN_DB,
) -> RasterDiagnosis:
    """在 bbox 上铺 RSRP 采样栅格，逐格取最强 RSRP（**按站点扇区数 + 链路余量**）。

    对每个站点，以该站为中心按 ``resolution_m`` 遍历半径 ``band_config.max_radius_km``
    内的正方形邻域（``i, j ∈ [-steps, steps]``，``steps = int(radius_km × 1000 / resolution_m)``，
    与既有热力图遍历口径一致），再按站点 ``num_sectors`` 推导的方位角逐扇区计算路径损耗，
    并按

        ``RSRP = power_w_to_dbm(power) + gain − path_loss − 8dB阴影 − link_margin_db``

    得该扇区在该点的 RSRP；所有站/所有扇区在同一格子上取最大。

    扇区方位角由 :func:`_azimuths_for_site` 给出：站点 dict 缺 ``'num_sectors'`` 键时
    回退 ``SECTOR_AZIMUTHS_DEG``；``num_sectors <= 0``（全向）时**不施加方向图损失**，
    改用 :func:`design_engine.coverage.okumura_hata_path_loss` 直接算路径损耗。
    未被任何站点覆盖的格子保持 ``NO_COVERAGE_DBM`` 哨兵值（按盲区统计）。

    Args:
        sites: ``generated_sites`` 的裸 dict 列表（读 longitude/latitude/tower_height，
            以及可选的 num_sectors）。
        bbox: (min_lon, min_lat, max_lon, max_lat)，EPSG:4326。
        band_config: ``design_engine.rules.BandConfig``（读频率/功率/增益/最大半径）。
        tech: 制式字符串。
        resolution_m: 采样分辨率（米）。
        environment: URBAN/SUBURBAN/RURAL。
        link_margin_db: 链路余量（dB，**须非负**）。默认
            ``DEFAULT_LINK_MARGIN_DB=20.0``（干扰抬升 + 穿透损耗 + 边缘可靠性）。
            档2 起将通过面板输入框暴露，故为显式参数、不得写死。

    Returns:
        已装配 ``grid`` / ``geotransform`` / ``stats``（total_cells、site_count、
        link_margin_db）的 :class:`RasterDiagnosis` 对象（``weak_cells`` 由
        :func:`diagnose_weak_coverage` 回填）。

    Raises:
        ValueError: bbox 非法、sites 为空、resolution_m 非正或 link_margin_db 为负。
    """
    if not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
        raise ValueError("bbox 必须为 (min_lon, min_lat, max_lon, max_lat)")
    min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox)
    if not (min_lon < max_lon and min_lat < max_lat):
        raise ValueError("bbox 非法：要求 min_lon < max_lon 且 min_lat < max_lat")
    if not sites:
        raise ValueError("sites 为空：无站点可诊断")
    if resolution_m <= 0:
        raise ValueError("resolution_m 必须为正")
    if link_margin_db < 0:
        raise ValueError(f"link_margin_db 必须非负，收到 {link_margin_db}")

    mean_lat = (min_lat + max_lat) / 2.0
    cos_lat = math.cos(math.radians(mean_lat))
    dy_deg = resolution_m / 111000.0
    dx_deg = resolution_m / (111000.0 * cos_lat) if cos_lat > 1e-9 else dy_deg

    cols = max(1, int(round((max_lon - min_lon) / dx_deg)))
    rows = max(1, int(round((max_lat - min_lat) / dy_deg)))

    grid: List[List[float]] = [[NO_COVERAGE_DBM] * cols for _ in range(rows)]

    radius_km = float(getattr(band_config, "max_radius_km", 0.0) or 0.0)
    if radius_km <= 0:
        radius_km = 2.0  # 兜底，避免 0 半径导致无法覆盖
    frequency_mhz = float(band_config.frequency_mhz)
    power_w = float(band_config.default_power_w)
    gain_dbi = float(band_config.default_gain_dbi)

    tx_dbm = power_w_to_dbm(power_w)
    steps = int(radius_km * 1000 / resolution_m)

    for site in sites:
        site_lon, site_lat = _site_lon_lat(site)
        height = float(site.get("tower_height", 35.0) or 35.0)
        cos_site_lat = math.cos(math.radians(site_lat))
        # 采样点经纬度换算沿用 coverage_heatmap 的口径（按站点纬度，非 bbox 均值）。
        lon_per_km = 1.0 / (111.0 * cos_site_lat) if cos_site_lat > 1e-9 else 1.0 / 111.0
        lat_per_km = 1.0 / 111.0
        # 扇区方位角跟随站点数据（缺键回退 SECTOR_AZIMUTHS_DEG；空元组 = 全向）。
        azimuths = _azimuths_for_site(site)

        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                d_km = math.hypot(i * resolution_m / 1000.0,
                                  j * resolution_m / 1000.0)
                if d_km > radius_km or d_km < 0.01:
                    continue
                lon = site_lon + (i * resolution_m / 1000.0) * lon_per_km
                lat = site_lat + (j * resolution_m / 1000.0) * lat_per_km
                col = int((lon - min_lon) / dx_deg)
                row = int((max_lat - lat) / dy_deg)
                if not (0 <= row < rows and 0 <= col < cols):
                    continue

                if azimuths:
                    # 定向站：逐扇区取最强，偏离主瓣的方向由方向图施加 3~15dB 额外损失。
                    for azimuth in azimuths:
                        # 接收点相对该扇区的方位角（与 coverage.calculate_rsrp_sector 一致）。
                        rx_angle = math.degrees(math.atan2(
                            (lon - site_lon) * 111.0 * cos_site_lat,
                            (lat - site_lat) * 111.0,
                        )) % 360.0
                        path_loss = path_loss_with_directivity(
                            frequency_mhz, d_km, height, azimuth,
                            SECTOR_BEAMWIDTH_DEG, environment, rx_angle,
                        )
                        rsrp = (tx_dbm + gain_dbi - path_loss
                                - SHADOW_FADE_DB - link_margin_db)
                        if rsrp > grid[row][col]:
                            grid[row][col] = rsrp
                else:
                    # 全向站（num_sectors <= 0）：不施加方向图损失。
                    path_loss = okumura_hata_path_loss(
                        frequency_mhz, d_km, height, environment=environment,
                    )
                    rsrp = (tx_dbm + gain_dbi - path_loss
                            - SHADOW_FADE_DB - link_margin_db)
                    if rsrp > grid[row][col]:
                        grid[row][col] = rsrp

    geotransform = (min_lon, dx_deg, 0.0, max_lat, 0.0, -dy_deg)
    band_key = _band_key_for_config(band_config) or default_band_for(tech)

    return RasterDiagnosis(
        grid=grid,
        geotransform=geotransform,
        bbox=(min_lon, min_lat, max_lon, max_lat),
        resolution_m=resolution_m,
        tech=tech,
        band_key=band_key,
        weak_threshold_dbm=DEFAULT_WEAK_THRESHOLD_DBM,
        blind_threshold_dbm=DEFAULT_BLIND_THRESHOLD_DBM,
        no_coverage_dbm=NO_COVERAGE_DBM,
        weak_cells=[],
        stats={
            "total_cells": rows * cols,
            "site_count": len(sites),
            "link_margin_db": float(link_margin_db),
        },
    )


def diagnose_weak_coverage(
    diag: RasterDiagnosis,
    weak_threshold_dbm: float = DEFAULT_WEAK_THRESHOLD_DBM,
    blind_threshold_dbm: float = DEFAULT_BLIND_THRESHOLD_DBM,
) -> RasterDiagnosis:
    """就地回填 ``diag.weak_cells`` 与 ``diag.stats``（阈值单调性见模块文档）。

    分级规则：``rsrp < blind`` → ``blind``；``blind ≤ rsrp < weak`` → ``weak``；
    ``rsrp ≥ weak`` → 不弱（计入**可用覆盖率**）。无覆盖哨兵值（-200）恒计入盲区。

    v1.7：可用覆盖率 = ``count(rsrp >= weak_threshold_dbm) / total_cells``，与弱/盲
    同一刻度，满足 ``可用覆盖率 + 弱覆盖占比 + 盲区占比 = 100%``；口径字符串写入
    ``stats["coverage_caliber"]``。

    Raises:
        ValueError: ``blind_threshold_dbm > weak_threshold_dbm``。
    """
    if blind_threshold_dbm > weak_threshold_dbm:
        raise ValueError(
            "盲区阈值不得大于弱覆盖阈值："
            f"blind={blind_threshold_dbm} > weak={weak_threshold_dbm}"
        )

    diag.weak_threshold_dbm = weak_threshold_dbm
    diag.blind_threshold_dbm = blind_threshold_dbm

    grid = diag.grid
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    lon_min, dx_deg, _, lat_max, _, neg_dy = diag.geotransform
    dy_deg = -neg_dy
    res = diag.resolution_m

    weak_cells: List[WeakCell] = []
    weak_count = 0
    blind_count = 0
    no_coverage_count = 0
    covered = 0

    for r in range(rows):
        row_vals = grid[r]
        for c in range(cols):
            v = float(row_vals[c])
            if v == NO_COVERAGE_DBM:
                no_coverage_count += 1
            if v >= weak_threshold_dbm:
                covered += 1
            level = ""
            if v < blind_threshold_dbm:
                level = "blind"
                blind_count += 1
            elif v < weak_threshold_dbm:
                level = "weak"
                weak_count += 1
            if level:
                lon = lon_min + (c + 0.5) * dx_deg
                lat = lat_max - (r + 0.5) * dy_deg
                weak_cells.append(WeakCell(
                    row=r, col=c, lon=round(lon, 7), lat=round(lat, 7),
                    rsrp=round(v, 1), level=level, cell_m=float(res),
                ))

    total_cells = rows * cols
    cell_area_km2 = (res / 1000.0) ** 2
    total_area_km2 = total_cells * cell_area_km2
    weak_area_km2 = (weak_count + blind_count) * cell_area_km2
    coverage_rate_pct = calculate_coverage_rate(
        [1] * covered, total_area_km2, res
    ) * 100.0
    # 口径拆两个键，供 T09 报告参数快照 + 面板回显，避免下游自行拼字符串：
    #   coverage_caliber_label —— 固定中文标签「可用覆盖率」；
    #   coverage_caliber       —— 可组合的口径描述（不含标签，避免与标签重复/括号嵌套）。
    coverage_caliber_label = "可用覆盖率"
    coverage_caliber = f"RSRP >= {weak_threshold_dbm} dBm"

    diag.weak_cells = weak_cells
    diag.stats.update({
        "total_cells": total_cells,
        "weak_count": weak_count,
        "blind_count": blind_count,
        "weak_area_km2": round(weak_area_km2, 4),
        "coverage_rate_pct": round(coverage_rate_pct, 1),
        "coverage_caliber_label": coverage_caliber_label,
        "coverage_caliber": coverage_caliber,
        "site_count": diag.stats.get("site_count", 0),
        "no_coverage_count": no_coverage_count,
    })
    return diag


def cluster_weak_cells(
    weak_cells: List[WeakCell],
    cell_m: float,
    min_cells: Optional[int] = None,
    resolution_m: int = DEFAULT_RESOLUTION_M,
) -> List[WeakCluster]:
    """按 ``cell_m`` 米网格分桶聚类，丢弃面积不足的桶。空输入返回 ``[]``。

    ``min_cells`` 为 None 时 = ``max(1, round(0.2 × (cell_m/resolution_m)²))``。

    说明：本实现为"单桶成聚类"（一个桶 = 一个覆盖单元）；跨桶的弱区会被切成
    多片、因此可能产出多条建议站 —— 这是**有意为之**（一个覆盖单元配一个补站）。
    """
    if not weak_cells:
        return []
    if cell_m <= 0:
        raise ValueError("cell_m 必须为正")
    if min_cells is None:
        min_cells = _min_cells_for(cell_m, resolution_m)

    mean_lat = sum(c.lat for c in weak_cells) / len(weak_cells)
    cos_lat = math.cos(math.radians(mean_lat))
    cell_deg_lat = cell_m / 111000.0
    cell_deg_lon = cell_m / (111000.0 * cos_lat) if cos_lat > 1e-9 else cell_deg_lat

    buckets: Dict[Tuple[int, int], List[WeakCell]] = {}
    for cell in weak_cells:
        key = (int(round(cell.lon / cell_deg_lon)), int(round(cell.lat / cell_deg_lat)))
        buckets.setdefault(key, []).append(cell)

    clusters: List[WeakCluster] = []
    for key in sorted(buckets.keys()):
        members = buckets[key]
        if len(members) < min_cells:
            continue
        blind = sum(1 for m in members if m.level == "blind")
        # 需求加权质心：盲区权重 2.0（更紧迫），弱覆盖权重 1.0。
        total_w = 0.0
        w_lon = 0.0
        w_lat = 0.0
        for m in members:
            w = 2.0 if m.level == "blind" else 1.0
            total_w += w
            w_lon += m.lon * w
            w_lat += m.lat * w
        centroid_lon = w_lon / total_w if total_w else members[0].lon
        centroid_lat = w_lat / total_w if total_w else members[0].lat
        mean_rsrp = sum(m.rsrp for m in members) / len(members)
        min_rsrp = min(m.rsrp for m in members)
        clusters.append(WeakCluster(
            cluster_id="",
            cell_key=key,
            centroid_lon=round(centroid_lon, 7),
            centroid_lat=round(centroid_lat, 7),
            cell_count=len(members),
            blind_count=blind,
            mean_rsrp=round(mean_rsrp, 1),
            min_rsrp=round(min_rsrp, 1),
            demand_score=0.0,
            cell_m=float(cell_m),
        ))

    for i, cluster in enumerate(clusters, start=1):
        cluster.cluster_id = f"CLU-{i:03d}"
    return clusters


def score_cluster(
    cluster: WeakCluster,
    weak_threshold_dbm: float,
    blind_threshold_dbm: float,
    weights: Optional[dict] = None,
) -> float:
    """计算需求评分 0~100（三项 RSRP 侧可解释评分）。纯函数，权重可单点校准。

    公式::

        demand_score = 100 × clamp(
              0.4 × min(cell_count / MAX_CELLS_REF, 1.0)                  # 面积项
            + 0.4 × clamp((weak_thr - mean_rsrp)/(weak_thr - blind_thr),0,1)  # 缺口深度项
            + 0.2 × (blind_count / max(cell_count, 1))                    # 盲区占比项
            , 0, 1)
    """
    w = dict(DEFAULT_SCORE_WEIGHTS)
    if weights:
        w.update(weights)

    area_term = min(cluster.cell_count / MAX_CELLS_REF, 1.0) if MAX_CELLS_REF else 1.0

    span = weak_threshold_dbm - blind_threshold_dbm
    if span <= 0:
        depth_term = 1.0 if cluster.mean_rsrp < weak_threshold_dbm else 0.0
    else:
        depth_term = (weak_threshold_dbm - cluster.mean_rsrp) / span
    depth_term = max(0.0, min(1.0, depth_term))

    blind_term = cluster.blind_count / max(cluster.cell_count, 1)

    raw = (w.get("area", 0.0) * area_term
           + w.get("depth", 0.0) * depth_term
           + w.get("blind", 0.0) * blind_term)
    return round(100.0 * max(0.0, min(1.0, raw)), 1)


def build_suggested_sites(
    clusters: List[WeakCluster],
    tech: str,
    band_key: str,
    suggested_radius_km: Optional[float] = None,
    avoidance_fn: Optional[Callable[[float, float], bool]] = None,
) -> List[SuggestedSite]:
    """每个聚类产出恰好一条建议站（A3：聚类数 == 建议站条数）。

    Args:
        clusters: 聚类列表。
        tech: 制式字符串。
        band_key: 频段键。
        suggested_radius_km: 建议覆盖半径；None 时取
            ``TECH_BASELINE[tech].coverage_radius_km``。
        avoidance_fn: **T07 可选注入钩子**，签名 ``(lon, lat) -> bool``；返回
            True 表示该点合法（不在避让区）。``None`` 时全部放行。UI 层可传入
            包装后的 ``AvoidanceChecker``（``design_engine/avoidance.py`` 不依赖
            QGIS，可用 :func:`avoidance_fn_from_checker` 适配）。落在避让区内的
            建议站**不静默丢弃**，只标记 ``needs_review``。
    """
    if suggested_radius_km is None:
        suggested_radius_km = get_baseline(tech).coverage_radius_km

    sites: List[SuggestedSite] = []
    for i, cluster in enumerate(clusters, start=1):
        needs_review = False
        note = ""
        if avoidance_fn is not None:
            try:
                ok = bool(avoidance_fn(cluster.centroid_lon, cluster.centroid_lat))
            except Exception:  # 钩子异常不阻断主流程，保守放行
                ok = True
            if not ok:
                needs_review = True
                note = "落在避让区，需人工复核"
        sites.append(SuggestedSite(
            suggest_id=f"SUG-{i:03d}",
            longitude=cluster.centroid_lon,
            latitude=cluster.centroid_lat,
            demand_score=cluster.demand_score,
            suggested_radius_km=float(suggested_radius_km),
            tech=tech,
            cell_count=cluster.cell_count,
            blind_count=cluster.blind_count,
            mean_rsrp=cluster.mean_rsrp,
            band_key=band_key,
            cluster_id=cluster.cluster_id,
            needs_review=needs_review,
            review_note=note,
        ))
    return sites


def avoidance_fn_from_checker(checker) -> Callable[[float, float], bool]:
    """把 ``AvoidanceChecker`` 适配为 :func:`build_suggested_sites` 的钩子。

    ``design_engine/avoidance.py`` 不依赖 QGIS（仅可选依赖 shapely），故 UI 层可
    直接用它构造钩子：``avoidance_fn=avoidance_fn_from_checker(checker)``。
    """
    def _fn(lon: float, lat: float) -> bool:
        try:
            ok, _reasons = checker.is_site_valid(lon, lat)
            return bool(ok)
        except Exception:
            return True
    return _fn


def dedupe_suggested_sites(
    suggested: List[SuggestedSite],
    existing_sites: List[dict],
    min_dist_m: Optional[float] = None,
    layout_isr_m: Optional[float] = None,
) -> Tuple[List[SuggestedSite], List[str]]:
    """与既有站/本轮已保留建议站去重（< min_dist_m 合并，保留高分者）。

    Args:
        suggested: 本轮建议站列表（会被就地累加被合并者的 cell_count/blind_count）。
        existing_sites: 既有站点裸 dict 列表（读 longitude/latitude）。
        min_dist_m: 去重距离（米）；None 时 = ``min(layout_isr_m/2, 200)``。
        layout_isr_m: 实际布站间距（米）= ``BAND_CONFIGS[band].ideal_isr_km × 1000``。

    Returns:
        ``(保留列表, 被合并的 suggest_id 列表)``。

    ⚠️ 距离口径必须用**实际布站 ISR**（按频段），不是 ``TECH_BASELINE`` 的
    ``suggested_spacing_km`` —— 两表不同源。
    """
    if min_dist_m is None:
        if layout_isr_m is not None and layout_isr_m > 0:
            min_dist_m = min(layout_isr_m / 2.0, DEDUPE_DISTANCE_MAX_M)
        else:
            min_dist_m = DEDUPE_DISTANCE_MAX_M

    existing_pts: List[Tuple[float, float]] = []
    for site in (existing_sites or []):
        lon = site.get("longitude", site.get("lon"))
        lat = site.get("latitude", site.get("lat"))
        if lon is not None and lat is not None:
            existing_pts.append((float(lon), float(lat)))

    order = sorted(range(len(suggested)),
                   key=lambda idx: suggested[idx].demand_score,
                   reverse=True)

    kept: List[Tuple[int, SuggestedSite]] = []
    kept_pos: List[Tuple[float, float]] = []
    merged_ids: List[str] = []

    for idx in order:
        site = suggested[idx]
        if any(_haversine_m(site.longitude, site.latitude, ex, ey) < min_dist_m
               for ex, ey in existing_pts):
            merged_ids.append(site.suggest_id)
            continue

        hit: Optional[int] = None
        for k, (kx, ky) in enumerate(kept_pos):
            if _haversine_m(site.longitude, site.latitude, kx, ky) < min_dist_m:
                hit = k
                break

        if hit is not None:
            target = kept[hit][1]
            target.cell_count += site.cell_count
            target.blind_count += site.blind_count
            target.needs_review = target.needs_review or site.needs_review
            merged_ids.append(site.suggest_id)
        else:
            kept.append((idx, site))
            kept_pos.append((site.longitude, site.latitude))

    kept.sort(key=lambda pair: pair[0])
    return [site for _, site in kept], merged_ids


def suggested_site_to_records(
    sug: SuggestedSite,
    *,
    tech: str,
    band_key: str,
    band_config,
    site_seq: int,
    site_type: str = "MACRO",
    tower_type: str = "MONOPOLE",
    tower_height: float = 35.0,
    mount_type: str = "GROUND",
    scenario: str = "URBAN",
    num_sectors: int = 3,
) -> dict:
    """把一条建议站映射为两套 schema 的完整字段（§3.3 映射表）。

    Returns:
        ``{"ui": {...UI 裸 dict...}, "site_kwargs": {...Site dataclass 构造参数...}}``。
        ``ui`` 含 20 键（§4.1 的 19 键 + 采纳来源标记 ``source``），
        ``site_kwargs`` 含 12 键（见 §4.1）。
    """
    base = get_baseline(tech)
    site_no = int(site_seq)
    site_id = f"BTS-{scenario[:4].upper()}-{site_no:03d}"
    name = f"SUG-补站-{site_no:03d}"

    lon = round(float(sug.longitude), 7)
    lat = round(float(sug.latitude), 7)
    coverage_radius = round(float(sug.suggested_radius_km), 2)
    capacity = base.capacity_ref

    ui = {
        "site_id": site_id,
        "name": name,
        "longitude": lon,
        "latitude": lat,
        "site_type": site_type,
        "tower_type": tower_type,
        "tower_height": tower_height,
        "mount_type": mount_type,
        "scenario": scenario,
        "tech_generation": tech,
        "coverage_radius": coverage_radius,
        "capacity": capacity,
        "band": band_key,
        "frequency": band_config.frequency_mhz,
        "power": band_config.default_power_w,
        "gain": band_config.default_gain_dbi,
        "num_sectors": num_sectors,
        "is_valid": True,
        "demand_score": round(float(sug.demand_score), 1),
        # 采纳来源标记：用于把「采纳补盲站」与「六边形生成的站」区分开，
        # 使 _generate_hex_grid 重生成时能把已采纳站择出并保留（否则会被整体覆盖抹掉）。
        "source": "gap_adopt",
    }
    site_kwargs = {
        "site_id": site_id,
        "name": name,
        "longitude": lon,
        "latitude": lat,
        "site_type": site_type,
        "tower_type": tower_type,
        "tower_height": tower_height,
        "mount_type": mount_type,
        "scenario": scenario,
        "tech_generation": tech,
        "coverage_radius": coverage_radius,
        "capacity": capacity,
    }
    return {"ui": ui, "site_kwargs": site_kwargs}


def next_site_seq(existing_sites) -> int:
    """给「采纳建议站」分配下一个可用站点序号。

    规则：扫描现有站点的 ``site_id``，取形如 ``...-NNN`` 的**数字后缀最大值 + 1**；
    解析不出来的条目一律忽略（手填站号可能不规范）；无可用后缀时返回 1。

    为什么不用 ``len(existing_sites) + 1``：既有 hex 网格站点与采纳站共用
    ``BTS-{场景}-{NNN}`` 编号规则（``hex_grid.py:124``），站点可能被删过、
    序号有洞，用长度会**撞号**。用「全局最大后缀 + 1」可保证唯一。
    """
    max_seq = 0
    for site in existing_sites or []:
        # 站点条目以 dict 为主（self.generated_sites）；对象形态做防御性兼容。
        site_id = site.get("site_id") if isinstance(site, dict) else getattr(site, "site_id", None)
        if not isinstance(site_id, str) or "-" not in site_id:
            continue
        suffix = site_id.rsplit("-", 1)[-1]
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))
    return max_seq + 1


def summarize_diagnosis(diag: RasterDiagnosis) -> str:
    """生成状态回显文案（纯函数）。

    形如：``弱覆盖区 N 处 / 建议站 M 个 / 可用覆盖率 X%（口径 RSRP >= -100.0 dBm）``。
    覆盖率取 ``stats['coverage_rate_pct']``；标签取 ``stats['coverage_caliber_label']``
    （缺键回退 ``"可用覆盖率"``）；口径描述取 ``stats['coverage_caliber']``
    （缺键则不显示括号；v1.7 起**不得**再写死 -80，也不得把标签塞进口径串）。
    ``N`` 优先取 ``stats['cluster_count']``，缺省退化为弱覆盖（含盲区）栅格数；
    ``M`` 取 ``stats['suggested_site_count']``。

    下游（如 T09 报告）如需**完整口径串**，请自行组合 ``f"{label}（{caliber}）"``
    —— 本函数有意不返回该组合，以免标签重复 / 括号嵌套。
    """
    stats = diag.stats or {}
    area_count = stats.get("cluster_count", len(diag.weak_cells))
    site_count = stats.get("suggested_site_count", 0)
    rate = stats.get("coverage_rate_pct", 0.0)
    label = stats.get("coverage_caliber_label", "可用覆盖率")
    caliber = stats.get("coverage_caliber", "")
    caliber_suffix = f"（口径 {caliber}）" if caliber else ""
    return (f"弱覆盖区 {area_count} 处 / 建议站 {site_count} 个 / "
            f"{label} {rate}%{caliber_suffix}")


def build_result_notice(
    stats: Dict,
    cluster_count: int,
    suggested_count: int,
    cell_m: float,
    resolution_m: float,
) -> Optional[Tuple[str, str]]:
    """按诊断结果生成给用户看的说明；正常出了建议站时返回 None。

    ⚠️ 为什么必须分情形：界面上「结果为空」与「结果不可见」长得一模一样，
    而「有弱覆盖但没聚成片」又极易被误读成「没有弱覆盖」。旧实现在 UI 里用
    ``weak_count == 0 or not kept`` 一个条件兜三种情形，会在有几百处弱覆盖时
    弹出「本次未发现弱覆盖区」——与地图上大片橙色弱区自相矛盾。

    Args:
        stats: ``RasterDiagnosis.stats``（读 ``weak_count`` / ``blind_count`` /
            ``coverage_rate_pct`` / ``coverage_caliber``）。
        cluster_count: 聚类片数（``len(clusters)``）。
        suggested_count: 去重后保留的建议站数（``len(kept)``）。
        cell_m: 本次聚类网格尺寸（米）。
        resolution_m: 采样分辨率（米）。

    Returns:
        ``None``（已正常产出建议站，不应弹框）；否则 ``(标题, 正文)`` 二元组。

    四种情形：
        1. ``weak_count > 0 and suggested_count > 0`` → 返回 ``None``（正常）。
        2. ``weak_count == 0`` → 确实无弱覆盖。
        3. ``weak_count > 0 and cluster_count == 0`` → 有弱覆盖但太零散、没聚成片。
        4. ``cluster_count > 0 and suggested_count == 0`` → 已聚成片但被去重合并。

    假定输入自洽：``weak_count == 0`` 时 ``cluster_count`` / ``suggested_count``
    也必为 0（弱格为空则必然聚不出片），故不对矛盾输入另设分支。
    """
    weak_n = int(stats.get("weak_count", 0) or 0)
    blind_n = int(stats.get("blind_count", 0) or 0)
    rate = stats.get("coverage_rate_pct", 0.0)
    caliber = stats.get("coverage_caliber", "")

    # 正常出了建议站 → 不弹框。
    if weak_n > 0 and suggested_count > 0:
        return None

    # 公共头：三档口径与聚片统计，统一在此拼装（各分支不再重写）。
    head = (f"可用覆盖率 {rate}%（口径 {caliber}）\n"
            f"弱覆盖栅格 {weak_n} 处（含盲区 {blind_n} 处）｜聚成 {cluster_count} 片｜"
            f"建议补站 {suggested_count} 个\n\n")

    if weak_n == 0:
        return ("覆盖诊断",
                "本次未发现弱覆盖区。\n\n" + head +
                "可尝试：\n"
                "· 调大第⑥步「链路余量(dB)」\n"
                "· 降低第④步「塔高」\n"
                "· 检查第④步「扇区数」是否为 3（≥6 时方向图缺口消失、弱区会归零）")

    if cluster_count == 0:
        # 门槛与 cluster_weak_cells 同源，避免公式两份实现、守卫口径分叉。
        min_cells = _min_cells_for(cell_m, resolution_m)
        return ("覆盖诊断",
                "有弱覆盖，但太零散、没聚成可补站的片。\n\n" + head +
                f"判定门槛：每片至少 {min_cells} 个弱覆盖栅格"
                f"（聚类网格 {cell_m:.0f}m 的 20%，采样 {resolution_m}m）\n\n"
                "可尝试：\n"
                "· 调大「链路余量(dB)」（弱区连成更大的片）\n"
                "· 降低「塔高」\n"
                "· 检查「扇区数」是否为 3")

    # 其余：cluster_count > 0 且 suggested_count == 0（去重合并后的正常结论）。
    return ("覆盖诊断",
            "弱覆盖已聚成片，但补站位置与现有基站过近，被去重合并掉了。"
            "（去重半径 = 半站间距）说明这些弱区可由现有基站调优解决，无需新增站"
            " —— 这是正常结论。\n\n" + head)


def build_success_notice(
    stats: Dict,
    cluster_count: int,
    suggested_count: int,
) -> Tuple[str, str]:
    """正常产出补站建议时的说明（成功也要弹框，避免「没弹框 = 没跑」的误读）。

    与 :func:`build_result_notice` 互补：那个函数只负责「异常/空结果」三情形，
    本函数负责它返回 ``None`` 的那一种（``weak_count > 0 and suggested_count > 0``）。

    Args:
        stats: ``RasterDiagnosis.stats``。
        cluster_count: 聚类片数（``len(clusters)``）。
        suggested_count: 去重后保留的建议站数（``len(kept)``）。

    Returns:
        ``(标题, 正文)`` 二元组，恒不为 ``None``。
    """
    weak_n = int(stats.get("weak_count", 0) or 0)
    blind_n = int(stats.get("blind_count", 0) or 0)
    rate = stats.get("coverage_rate_pct", 0.0)
    caliber = stats.get("coverage_caliber", "")
    caliber_suffix = f"（口径 {caliber}）" if caliber else ""
    return ("覆盖诊断 · 已生成补站建议",
            f"发现弱覆盖栅格 {weak_n} 处（含盲区 {blind_n} 处），"
            f"聚成 {cluster_count} 片，已生成 {suggested_count} 个建议补站。\n\n"
            f"可用覆盖率 {rate}%{caliber_suffix}\n\n"
            "查看方式：在左侧「图层」面板勾选「诊断·弱覆盖区」「诊断·建议补站」。\n"
            "在右侧第⑥步「覆盖分析」的「建议补站」列表点【采纳】即可加入基站设计（自动 1:1 建机房）。\n"
            "建议站按需求评分着色：灰 <40 / 黄 40–70 / 红 ≥70，"
            "标注数字即评分。\n"
            "（出诊断图层时会自动隐藏「覆盖热力图」——两者口径不同，需要对比时手动勾回）")


# ══════════════════════════════════════════════════════════════════════
#  补盲前后对比（采纳闭环的「补盲前 vs 补盲后」报告）
# ══════════════════════════════════════════════════════════════════════
#  8 个对比指标：prefer 表示「越大越好(up) / 越小越好(down) / 无关(neutral)」。
#  颜色由 UI 层决定，纯函数只给 direction 语义，不染颜色。
COMPARISON_METRICS: List[Dict] = [
    {"key": "site_count", "label": "基站数", "unit": "个", "prefer": "neutral", "fmt": "{:.0f}",
     "tip": "当前在网站点总数（含已采纳的补盲站）。只统计数量，不评价好坏——补盲前后变化反映采纳了几座补盲站。"},
    {"key": "coverage_rate_pct", "label": "可用覆盖率", "unit": "%", "prefer": "up", "fmt": "{:.1f}",
     "tip": "RSRP 达到「可用门限」的栅格占比。越大越好：覆盖率越高，用户能正常通话/上网的范围越广。"},
    {"key": "weak_count", "label": "弱覆盖栅格", "unit": "格", "prefer": "down", "fmt": "{:.0f}",
     "tip": "RSRP 介于弱覆盖门限与盲区门限之间、信号勉强可用的栅格数。越小越好：弱覆盖点越少，掉话/卡顿风险越低。"},
    {"key": "blind_count", "label": "盲区栅格", "unit": "格", "prefer": "down", "fmt": "{:.0f}",
     "tip": "RSRP 低于盲区门限、基本无信号的栅格数。越小越好：盲区越少，完全断网的点越少。"},
    {"key": "weak_area_km2", "label": "弱覆盖面积", "unit": "km²", "prefer": "down", "fmt": "{:.3f}",
     "tip": "弱覆盖栅格折算成的实际地理面积。越小越好：用面积而非栅格数，更直观反映受影响的区域大小。"},
    {"key": "no_coverage_count", "label": "无覆盖栅格", "unit": "格", "prefer": "down", "fmt": "{:.0f}",
     "tip": "没有任何基站信号覆盖的栅格数。越小越好：这是比弱覆盖更严重的「零信号」区域。"},
    {"key": "cluster_count", "label": "聚成片数", "unit": "片", "prefer": "down", "fmt": "{:.0f}",
     "tip": "弱覆盖/盲区连成的连续成片区域数。越小越好：成片区域少，说明待补盲的热点更分散、更易逐个击破。"},
    {"key": "suggested_site_count", "label": "仍需补站", "unit": "个", "prefer": "down", "fmt": "{:.0f}",
     "tip": "系统仍建议新增的补盲站点数。越小越好：数值下降说明已采纳的补盲站正在消除弱覆盖；归零即全部消除。"},
]


def _metrics_from_diag(diag: "RasterDiagnosis", cluster_count: int,
                       suggested_count: int) -> Dict[str, float]:
    """从一次诊断结果 + 聚类/建议站计数，抽出 8 指标字典（供 before/after 共用）。"""
    s = diag.stats
    return {
        "site_count": float(s.get("site_count", 0) or 0),
        "coverage_rate_pct": float(s.get("coverage_rate_pct", 0.0) or 0.0),
        "weak_count": float(s.get("weak_count", 0) or 0),
        "blind_count": float(s.get("blind_count", 0) or 0),
        "weak_area_km2": float(s.get("weak_area_km2", 0.0) or 0.0),
        "no_coverage_count": float(s.get("no_coverage_count", 0) or 0),
        "cluster_count": float(cluster_count),
        "suggested_site_count": float(suggested_count),
    }


def shadow_diagnose_metrics(
    sites: List[dict],
    gap_params: Dict,
    band_config,
) -> Dict[str, float]:
    """影子诊断：用**历史诊断参数**对**当前站点集**重算覆盖。

    ⚠️ 只算不画：本函数**严禁**调用 ``remove_gap_layers`` / ``build_rsrp_weak_layer`` /
    ``build_suggested_sites_layer``，也**不**改写调用方的 ``_suggested_sites``。
    它纯粹吃站点列表 + 参数、吐出 8 指标字典，用于「补盲后」口径。

    与 :func:`compute_rsrp_grid` 共用同一套 RSRP 链路预算；``bbox`` / ``link_margin_db`` /
    ``resolution_m`` / ``tower_height`` / ``num_sectors`` 一律取自 ``gap_params`` 快照，
    保证「补盲前 / 补盲后」同参数同范围，对比不因用户中途改面板而失真。

    Args:
        sites: 当前 ``generated_sites``（含已采纳补盲站）。
        gap_params: 诊断时快照的参数（须含 band_key/tech/scenario/tower_height/
            num_sectors/link_margin_db/resolution_m/bbox）。
        band_config: ``design_engine.rules.BandConfig``（由 UI 从 ``BAND_CONFIGS`` 取后传入，
            本函数不 import rules，保持纯计算、可在无 QGIS 环境单测）。

    Returns:
        8 指标字典（``_metrics_from_diag`` 结构）。
    """
    raw = [{"longitude": s["longitude"], "latitude": s["latitude"],
            "tower_height": float(gap_params["tower_height"]),
            "num_sectors": s.get("num_sectors", gap_params["num_sectors"])}
           for s in sites]
    diag = compute_rsrp_grid(raw, gap_params["bbox"], band_config, gap_params["tech"],
                             resolution_m=gap_params["resolution_m"],
                             environment=gap_params["scenario"],
                             link_margin_db=gap_params["link_margin_db"])
    diagnose_weak_coverage(diag)
    cell_m = grid_size_for_band(gap_params["band_key"])
    clusters = cluster_weak_cells(diag.weak_cells, cell_m=cell_m,
                                 resolution_m=gap_params["resolution_m"])
    for c in clusters:
        c.demand_score = score_cluster(c, DEFAULT_WEAK_THRESHOLD_DBM,
                                      DEFAULT_BLIND_THRESHOLD_DBM)
    sugs = build_suggested_sites(clusters, gap_params["tech"], gap_params["band_key"])
    kept, merged = dedupe_suggested_sites(
        sugs, raw, layout_isr_m=band_config.ideal_isr_km * 1000)
    return _metrics_from_diag(diag, len(clusters), len(kept))


def build_comparison_rows(before: Dict[str, float],
                         after: Dict[str, float]) -> List[Dict]:
    """把「补盲前 / 补盲后」两个指标字典，逐指标算出 delta 与 direction。

    direction ∈ ``improved``（变好）/ ``worsened``（变差）/ ``unchanged``（零变化）/
    ``neutral``（该指标无关方向，如基站数）。颜色由 UI 决定，这里只给语义。
    """
    rows = []
    for m in COMPARISON_METRICS:
        b = float(before.get(m["key"], 0.0) or 0.0)
        a = float(after.get(m["key"], 0.0) or 0.0)
        delta = a - b
        if m["prefer"] == "neutral":
            direction = "neutral"
        elif delta == 0:
            direction = "unchanged"
        else:
            improved = (delta < 0) if m["prefer"] == "down" else (delta > 0)
            direction = "improved" if improved else "worsened"
        rows.append({
            "key": m["key"], "label": m["label"], "unit": m["unit"],
            "before": b, "after": a, "delta": delta, "direction": direction,
            "fmt": m["fmt"], "tip": m.get("tip", ""),
        })
    return rows


def format_comparison_report(rows: List[Dict]) -> str:
    """把对比行渲染成纯文本报告（用于「复制对比报告」按钮）。不含颜色。"""
    arrow = {"improved": "↑好", "worsened": "↓差", "unchanged": "＝", "neutral": "·"}
    lines = ["补盲前后覆盖对比（采纳补盲站后）："]
    for r in rows:
        b_txt = r["fmt"].format(r["before"])
        a_txt = r["fmt"].format(r["after"])
        d_txt = f"{r['delta']:+.1f}"
        lines.append(
            f"· {r['label']}：{b_txt}{r['unit']} → {a_txt}{r['unit']} "
            f"（{d_txt}{r['unit']}）{arrow[r['direction']]}"
        )
    return "\n".join(lines)
