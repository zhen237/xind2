"""诊断内核单元测试 — design_engine/gap_diagnosis.py

覆盖 T01（诊断内核）+ T07（建议站避让过滤）。
硬约束：本测试**不得**依赖 QGIS / PyQt，可在普通 Python 下用 pytest 运行。
"""
import os
import sys
import math

# 添加插件目录到路径（沿用 tests/test_engine.py 的写法）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from design_engine.rules import BAND_CONFIGS
from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
from design_engine.gap_diagnosis import (
    NO_COVERAGE_DBM,
    DEFAULT_WEAK_THRESHOLD_DBM,
    DEFAULT_BLIND_THRESHOLD_DBM,
    DEFAULT_LINK_MARGIN_DB,
    SHADOW_FADE_DB,
    SECTOR_AZIMUTHS_DEG,
    SECTOR_BEAMWIDTH_DEG,
    DEDUPE_DISTANCE_MAX_M,
    MIN_WEAK_AREA_RATIO,
    MAX_SECTORS,
    _azimuths_for_site,
    WeakCell,
    RasterDiagnosis,
    WeakCluster,
    SuggestedSite,
    grid_size_for_band,
    grid_size_for_tech,
    compute_rsrp_grid,
    diagnose_weak_coverage,
    cluster_weak_cells,
    score_cluster,
    build_suggested_sites,
    dedupe_suggested_sites,
    suggested_site_to_records,
    next_site_seq,
    summarize_diagnosis,
    build_result_notice,
    build_success_notice,
)

# ── §4.1 / §3.3 契约：两套 schema 的必备键（逐键断言，防静默缺项）──
# 注：ui 比 §4.1 多 1 个采纳来源标记 "source"（=20 键）；site_kwargs 仍 12 键。
UI_KEYS = {
    "site_id", "name", "longitude", "latitude", "site_type", "tower_type",
    "tower_height", "mount_type", "scenario", "tech_generation",
    "coverage_radius", "capacity", "band", "frequency", "power", "gain",
    "num_sectors", "is_valid", "demand_score", "source",
}
SITE_KWARGS_KEYS = {
    "site_id", "name", "longitude", "latitude", "site_type", "tower_type",
    "tower_height", "mount_type", "scenario", "tech_generation",
    "coverage_radius", "capacity",
}


# ──────────────────────────── 辅助构造 ────────────────────────────

def _make_cluster(cluster_id="CLU-001", cell_count=10, blind_count=0,
                  mean_rsrp=-105.0, min_rsrp=-108.0, cell_m=1000.0):
    """构造一个 WeakCluster（用于评分/建站等纯函数测试）。"""
    return WeakCluster(
        cluster_id=cluster_id,
        cell_key=(0, 0),
        centroid_lon=-7.6,
        centroid_lat=33.58,
        cell_count=cell_count,
        blind_count=blind_count,
        mean_rsrp=mean_rsrp,
        min_rsrp=min_rsrp,
        demand_score=0.0,
        cell_m=cell_m,
    )


def _make_diag(grid, resolution_m=100, weak=-100.0, blind=-110.0):
    """由手写栅格构造 RasterDiagnosis（diagnose_weak_coverage 的纯输入）。"""
    rows = len(grid)
    cols = len(grid[0])
    lon_min, lon_max = -0.01, 0.01
    lat_min, lat_max = -0.01, 0.01
    dx = (lon_max - lon_min) / cols
    dy = (lat_max - lat_min) / rows
    gt = (lon_min, dx, 0.0, lat_max, 0.0, -dy)
    return RasterDiagnosis(
        grid=grid,
        geotransform=gt,
        bbox=(lon_min, lat_min, lon_max, lat_max),
        resolution_m=resolution_m,
        tech="4G LTE",
        band_key="2.6GHz",
        weak_threshold_dbm=weak,
        blind_threshold_dbm=blind,
        no_coverage_dbm=NO_COVERAGE_DBM,
        weak_cells=[],
        stats={},
    )


def _lattice_cells(n, level="weak", rsrp=-105.0, base_lon=0.0, base_lat=0.0):
    """在一个 1000m 网格桶内按 100m 间隔铺 n 个 WeakCell（5 列 × ceil 行）。

    保证全部落在同一个桶内（cell_m=1000, resolution_m=100）。
    """
    step = 100.0 / 111000.0  # 100m 对应的纬度度数
    cells = []
    for i in range(n):
        col = i % 5
        row = i // 5
        lon = base_lon + col * step
        lat = base_lat + row * step
        cells.append(WeakCell(row=row, col=col, lon=lon, lat=lat,
                              rsrp=rsrp, level=level, cell_m=100.0))
    return cells


def _site(lon, lat, height=35.0):
    return {
        "longitude": lon,
        "latitude": lat,
        "tower_height": height,
        "site_type": "MACRO",
    }


def _dist_m(lon1, lat1, lon2, lat2):
    """Haversine 距离（米），与实现口径一致。"""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _demo_bbox():
    """摩洛哥演示场景 bbox：西南角 (-6.8400, 34.0200) 起 5km × 5km。"""
    lon0, lat0 = -6.8400, 34.0200
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(34.0200)))
    lat_per_km = 1.0 / 111.0
    return (lon0, lat0, lon0 + 5 * lon_per_km, lat0 + 5 * lat_per_km)


def _demo_sites(num_sectors="OMIT"):
    """按演示场景生成 12 个站点 dict；num_sectors="OMIT" 时不带该键（测回退）。"""
    bbox = _demo_bbox()
    cfg = BAND_CONFIGS["2.6GHz"]
    centers = generate_hex_grid(bbox, cfg.ideal_isr_km)
    engine_sites = generate_sites_from_grid(
        centers, cfg, site_type="MACRO", tower_height=35.0,
        scenario="URBAN", bbox=bbox,
    )
    sites = []
    for es in engine_sites:
        d = {"longitude": es.longitude, "latitude": es.latitude,
             "tower_height": es.tower_height}
        if num_sectors != "OMIT":
            d["num_sectors"] = num_sectors
        sites.append(d)
    return sites


def _demo_diagnose(num_sectors="OMIT"):
    """跑演示场景诊断，返回 (diag, cfg, bbox)。"""
    bbox = _demo_bbox()
    cfg = BAND_CONFIGS["2.6GHz"]
    diag = compute_rsrp_grid(_demo_sites(num_sectors), bbox, cfg, "4G LTE",
                             resolution_m=100, environment="URBAN")
    diagnose_weak_coverage(diag, weak_threshold_dbm=-100.0, blind_threshold_dbm=-110.0)
    return diag, cfg, bbox


# ════════════════════ 1. 网格尺寸口径（按频段）════════════════════

def test_grid_size_by_band_v15_caliber():
    """聚类网格尺寸 = clamp(ideal_isr_km × 1000, 100, 2000) 米，按频段。"""
    assert grid_size_for_band("700MHz") == 2000.0   # 2.5km → clamp 上限 2000
    assert grid_size_for_band("2.6GHz") == 1000.0
    assert grid_size_for_band("3.5GHz") == 500.0
    assert grid_size_for_band("4.9GHz") == 300.0


def test_grid_size_for_tech_uses_default_band():
    """grid_size_for_tech 经制式默认频段推导（不是 radius/5 旧口径）。"""
    assert grid_size_for_tech("4G LTE") == 1000.0        # 默认 2.6GHz
    assert grid_size_for_tech("5G NR(Sub-6)") == 500.0   # 默认 3.5GHz
    assert grid_size_for_tech("5G NR(mmWave)") == 300.0  # 默认 4.9GHz


# ════════════════════ 2. 最小弱区面积口径（20%）════════════════════

def test_min_cells_area_caliber_2p6ghz():
    """cell_m=1000, resolution_m=100 → min_cells = round(0.2×100) = 20。

    19 个同桶栅格 → 丢弃（0 聚类）；20 个 → 保留（1 聚类）。
    """
    assert MIN_WEAK_AREA_RATIO == 0.2
    dropped = cluster_weak_cells(_lattice_cells(19), cell_m=1000.0, resolution_m=100)
    assert dropped == []
    kept = cluster_weak_cells(_lattice_cells(20), cell_m=1000.0, resolution_m=100)
    assert len(kept) == 1
    assert kept[0].cell_count == 20


# ════════════════════ 3. 阈值单调性（A2）════════════════════

def test_threshold_monotonicity():
    """同一栅格，weak_threshold 从 -100 调到 -90，弱覆盖格数单调不减。"""
    # 手工栅格：-80 良好 / -95 弱 / -105 弱 / -120 盲 / -200 无覆盖
    grid = [
        [-80.0, -95.0, -105.0, -120.0, NO_COVERAGE_DBM],
        [-80.0, -80.0, -95.0, -105.0, -120.0],
        [-200.0, -80.0, -80.0, -95.0, -105.0],
        [-120.0, -120.0, -80.0, -80.0, -95.0],
    ]
    diag = _make_diag(grid)

    diagnose_weak_coverage(diag, weak_threshold_dbm=-100.0, blind_threshold_dbm=-110.0)
    weak1 = diag.stats["weak_count"]
    blind1 = diag.stats["blind_count"]
    total1 = weak1 + blind1

    diagnose_weak_coverage(diag, weak_threshold_dbm=-90.0, blind_threshold_dbm=-110.0)
    weak2 = diag.stats["weak_count"]
    blind2 = diag.stats["blind_count"]
    total2 = weak2 + blind2

    assert weak2 >= weak1, "调高弱覆盖阈值后弱覆盖格数不得减少"
    assert blind2 == blind1, "盲区仅由盲区阈值决定，不应随弱覆盖阈值变化"
    assert total2 >= total1


# ════════════════════ 4. 聚类数 == 建议站数（A3）════════════════════

def test_suggested_count_equals_cluster_count():
    """每个聚类恰好产出一条建议站。"""
    clusters = [_make_cluster("CLU-001", cell_count=25),
                _make_cluster("CLU-002", cell_count=12, blind_count=5, mean_rsrp=-150.0)]
    for c in clusters:
        c.demand_score = score_cluster(c, -100.0, -110.0)
    sites = build_suggested_sites(clusters, tech="4G LTE", band_key="2.6GHz")
    assert len(sites) == len(clusters) == 2
    assert [s.suggest_id for s in sites] == ["SUG-001", "SUG-002"]


def test_suggested_count_equals_cluster_count_with_avoidance():
    """避让函数拒绝所有点，仍不静默丢弃 —— 条数不变，只打标。"""
    clusters = [_make_cluster("CLU-001")]
    clusters[0].demand_score = 50.0
    sites = build_suggested_sites(clusters, tech="4G LTE", band_key="2.6GHz",
                                  avoidance_fn=lambda lon, lat: False)
    assert len(sites) == 1
    assert sites[0].needs_review is True
    assert "复核" in sites[0].review_note


# ════════════════════ 5. 去重（不写死 200 / 保留高分）════════════════════

def test_dedupe_keeps_higher_score():
    """两个相距 ~50m 的建议站，layout_isr_m=1000 → 去重后剩 1 个，保留高分者。"""
    a = SuggestedSite("SUG-001", 0.0, 0.0, 30.0, 2.0, "4G LTE", 5, 1, -105.0,
                      "2.6GHz", "CLU-001")
    b = SuggestedSite("SUG-002", 0.0, 0.00045, 80.0, 2.0, "4G LTE", 3, 0, -98.0,
                      "2.6GHz", "CLU-002")
    assert _dist_m(0.0, 0.0, 0.0, 0.00045) < 60.0

    kept, merged = dedupe_suggested_sites([a, b], existing_sites=[], layout_isr_m=1000.0)
    assert len(kept) == 1
    assert kept[0].suggest_id == "SUG-002"  # 80 > 30，保留高分
    assert merged == ["SUG-001"]
    # 被合并者的栅格数累加到保留者
    assert kept[0].cell_count == 8
    assert kept[0].blind_count == 1


def test_dedupe_distance_not_hardcoded_200():
    """去重距离 = min(layout_isr_m/2, 200)，不得写死 200。

    两点相距 ~180m：
      - layout_isr_m=300  → 阈值 min(150,200)=150 → 两点皆保留（2）
      - layout_isr_m=1000 → 阈值 min(500,200)=200 → 合并为 1
    """
    step_lat = 180.0 / 111000.0
    p1 = SuggestedSite("SUG-001", 0.0, 0.0, 50.0, 2.0, "4G LTE", 4, 0, -100.0,
                       "4.9GHz", "CLU-001")
    p2 = SuggestedSite("SUG-002", 0.0, step_lat, 60.0, 2.0, "4G LTE", 4, 0, -100.0,
                       "4.9GHz", "CLU-002")
    d = _dist_m(0.0, 0.0, 0.0, step_lat)
    assert 170.0 < d < 190.0

    kept_small, _ = dedupe_suggested_sites([p1, p2], [], layout_isr_m=300.0)
    assert len(kept_small) == 2  # 阈值 150 < 180

    kept_big, _ = dedupe_suggested_sites(
        [SuggestedSite("SUG-001", 0.0, 0.0, 50.0, 2.0, "4G LTE", 4, 0, -100.0,
                       "4.9GHz", "CLU-001"),
         SuggestedSite("SUG-002", 0.0, step_lat, 60.0, 2.0, "4G LTE", 4, 0, -100.0,
                       "4.9GHz", "CLU-002")],
        [], layout_isr_m=1000.0)
    assert len(kept_big) == 1  # 阈值 200 > 180


def test_dedupe_against_existing_sites():
    """与既有站 < min_dist 的建议站被合并掉。"""
    sug = SuggestedSite("SUG-001", 0.0, 0.0, 70.0, 2.0, "4G LTE", 6, 0, -100.0,
                        "2.6GHz", "CLU-001")
    existing = [{"longitude": 0.0, "latitude": 0.0002}]  # ~22m
    kept, merged = dedupe_suggested_sites([sug], existing_sites=existing,
                                          layout_isr_m=1000.0)
    assert kept == []
    assert merged == ["SUG-001"]


# ════════════════════ 6. 评分边界与排序 ════════════════════

def test_score_bounds_and_ordering():
    """demand_score 恒落 0~100；全盲区聚类 > 全弱覆盖聚类。"""
    c_blind = _make_cluster("CLU-001", cell_count=10, blind_count=10,
                            mean_rsrp=-200.0, min_rsrp=-200.0)
    c_weak = _make_cluster("CLU-002", cell_count=10, blind_count=0,
                           mean_rsrp=-105.0, min_rsrp=-108.0)
    s_blind = score_cluster(c_blind, -100.0, -110.0)
    s_weak = score_cluster(c_weak, -100.0, -110.0)
    assert 0.0 <= s_blind <= 100.0
    assert 0.0 <= s_weak <= 100.0
    assert s_blind > s_weak


def test_score_clamped_to_100_with_extreme_weights():
    c = _make_cluster("CLU-001", cell_count=9999, blind_count=9999, mean_rsrp=-200.0)
    s = score_cluster(c, -100.0, -110.0, weights={"area": 10.0, "depth": 10.0, "blind": 10.0})
    assert s == 100.0


# ════════════════════ 7. schema 完整（20 + 12 键，逐键）════════════════════

def test_suggested_site_to_records_schema_complete():
    """ui 含 §4.1 的 19 键 + 采纳来源标记 source（共 20），site_kwargs 含全部 12 键 —— 逐键断言。"""
    sug = SuggestedSite("SUG-001", -7.6123456, 33.5891234, 82.4, 2.0,
                        "4G LTE", 12, 3, -112.0, "2.6GHz", "CLU-001")
    rec = suggested_site_to_records(
        sug, tech="4G LTE", band_key="2.6GHz",
        band_config=BAND_CONFIGS["2.6GHz"], site_seq=1,
    )
    ui = rec["ui"]
    site_kwargs = rec["site_kwargs"]

    # 逐键存在
    for k in sorted(UI_KEYS):
        assert k in ui, f"ui 缺少键: {k}"
    for k in sorted(SITE_KWARGS_KEYS):
        assert k in site_kwargs, f"site_kwargs 缺少键: {k}"
    # 无缺无多
    assert set(ui.keys()) == UI_KEYS
    assert set(site_kwargs.keys()) == SITE_KWARGS_KEYS
    assert len(ui) == 20
    assert len(site_kwargs) == 12


def test_suggested_site_to_records_ui_has_source_marker():
    """ui 必须带采纳来源标记 ``source == "gap_adopt"``（重生成时据此区分/保留采纳站）。"""
    sug = SuggestedSite("SUG-001", -7.61, 33.58, 82.4, 2.0,
                        "4G LTE", 12, 3, -112.0, "2.6GHz", "CLU-001")
    rec = suggested_site_to_records(
        sug, tech="4G LTE", band_key="2.6GHz",
        band_config=BAND_CONFIGS["2.6GHz"], site_seq=1,
    )
    assert rec["ui"].get("source") == "gap_adopt"
    # site_kwargs 是 Site dataclass 构造参数，不应带 source。
    assert "source" not in rec["site_kwargs"]


def test_suggested_site_to_records_values():
    """映射取值口径：编号命名、频段派生、制式基线容量/半径。"""
    sug = SuggestedSite("SUG-007", -7.6123456, 33.5891234, 82.4, 2.0,
                        "4G LTE", 12, 3, -112.0, "2.6GHz", "CLU-007")
    rec = suggested_site_to_records(
        sug, tech="4G LTE", band_key="2.6GHz",
        band_config=BAND_CONFIGS["2.6GHz"], site_seq=7,
        scenario="URBAN",
    )
    ui = rec["ui"]
    site_kwargs = rec["site_kwargs"]
    assert ui["site_id"] == "BTS-URBA-007"
    assert ui["name"] == "SUG-补站-007"
    assert ui["longitude"] == round(-7.6123456, 7)
    assert ui["latitude"] == round(33.5891234, 7)
    assert ui["tech_generation"] == "4G LTE"
    assert ui["coverage_radius"] == 2.0          # TECH_BASELINE[4G].coverage_radius_km
    assert ui["capacity"] == 40.0                # TECH_BASELINE[4G].capacity_ref
    assert ui["band"] == "2.6GHz"
    assert ui["frequency"] == 2600
    assert ui["power"] == 160.0
    assert ui["gain"] == 22.0
    assert ui["num_sectors"] == 3
    assert ui["site_type"] == "MACRO"
    assert ui["mount_type"] == "GROUND"
    assert ui["is_valid"] is True
    assert ui["demand_score"] == 82.4
    # site_kwargs 与 ui 的 12 个公共键取值一致
    for k in SITE_KWARGS_KEYS:
        assert site_kwargs[k] == ui[k]


# ════════════════════ 8. RSRP 栅格装配（扇区化 + 链路余量）════════════════════

def test_compute_rsrp_grid_keeps_sub_threshold_points():
    """内核不做 -110 过滤：低于 -110dBm 的**已计算**栅格必须保留（旧口径#4 的等价回归守卫）。

    背景：v1.6 起 compute_rsrp_grid 改为扇区化自算，不再调用会被默认 -110 过滤的
    ``generate_coverage_heatmap_data``。但"不得丢弃盲/弱区点"这一约束依然有效：
    扇区后瓣（-15dB）+ 20dB 链路余量下，栅格里必然出现 RSRP ∈ (NO_COVERAGE, -110)
    的已计算值，它们必须原样保留，而不是被丢成哨兵或消失。
    """
    sites = [_site(-7.60, 33.58)]
    bbox = (-7.65, 33.55, -7.55, 33.61)
    diag = compute_rsrp_grid(sites, bbox, BAND_CONFIGS["2.6GHz"], "4G LTE",
                             resolution_m=200)
    vals = [v for row in diag.grid for v in row]
    assert any(NO_COVERAGE_DBM < v < DEFAULT_BLIND_THRESHOLD_DBM for v in vals), (
        "扇区化 + 余量下应存在 (NO_COVERAGE, -110) 的已计算栅格"
    )


def test_compute_rsrp_grid_shape_and_no_coverage():
    """栅格形状与 bbox 一致；站点覆盖外的格子保持 NO_COVERAGE_DBM。"""
    sites = [_site(-7.60, 33.58), _site(-7.60, 33.60)]
    bbox = (-7.70, 33.50, -7.50, 33.68)  # 明显大于两站覆盖范围
    diag = compute_rsrp_grid(sites, bbox, BAND_CONFIGS["2.6GHz"], "4G LTE",
                             resolution_m=500)
    rows = len(diag.grid)
    cols = len(diag.grid[0])
    assert rows > 0 and cols > 0
    assert all(len(r) == cols for r in diag.grid)
    # 至少存在被覆盖的格子
    assert any(v > NO_COVERAGE_DBM for row in diag.grid for v in row)
    # 覆盖外 → 哨兵值（按盲区计）
    assert any(v == NO_COVERAGE_DBM for row in diag.grid for v in row)
    assert diag.stats["total_cells"] == rows * cols
    assert diag.stats["site_count"] == 2


def test_compute_rsrp_grid_empty_sites_raises():
    with pytest.raises(ValueError):
        compute_rsrp_grid([], (-7.6, 33.5, -7.5, 33.6),
                          BAND_CONFIGS["2.6GHz"], "4G LTE")


def test_compute_rsrp_grid_invalid_bbox_raises():
    with pytest.raises(ValueError):
        compute_rsrp_grid([_site(-7.6, 33.58)], (-7.5, 33.6, -7.6, 33.5),
                          BAND_CONFIGS["2.6GHz"], "4G LTE")


# ════════════════════ 9. 诊断分级与统计 ════════════════════

def test_diagnose_levels_and_stats():
    """blind/weak/不弱 三档分级与 stats 键齐全。"""
    grid = [
        [-80.0, -105.0, -115.0],
        [NO_COVERAGE_DBM, -100.0, -70.0],
    ]
    diag = _make_diag(grid, resolution_m=100)
    diagnose_weak_coverage(diag, weak_threshold_dbm=-100.0, blind_threshold_dbm=-110.0)

    levels = sorted((c.row, c.col, c.level) for c in diag.weak_cells)
    # -105 弱（-110 ≤ v < -100）；-115 盲；-200 盲；-100 不弱（>= weak）；-80/-70 不弱
    assert (0, 1, "weak") in levels
    assert (0, 2, "blind") in levels
    assert (1, 0, "blind") in levels
    assert diag.stats["weak_count"] == 1
    assert diag.stats["blind_count"] == 2
    assert diag.stats["no_coverage_count"] == 1
    for key in ("total_cells", "weak_count", "blind_count", "weak_area_km2",
                "coverage_rate_pct", "site_count", "no_coverage_count"):
        assert key in diag.stats


def test_diagnose_blind_gt_weak_raises():
    diag = _make_diag([[-90.0]])
    with pytest.raises(ValueError):
        diagnose_weak_coverage(diag, weak_threshold_dbm=-100.0, blind_threshold_dbm=-90.0)


def test_cluster_empty_returns_empty_list():
    assert cluster_weak_cells([], cell_m=1000.0) == []


# ════════════════════ 10. 状态回显 ════════════════════

def test_summarize_diagnosis_returns_text():
    grid = [[-80.0, -95.0], [NO_COVERAGE_DBM, -70.0]]
    diag = _make_diag(grid)
    diagnose_weak_coverage(diag, weak_threshold_dbm=-100.0, blind_threshold_dbm=-110.0)
    text = summarize_diagnosis(diag)
    assert isinstance(text, str)
    assert "弱覆盖区" in text
    assert "建议站" in text
    assert "可用覆盖率" in text
    assert "-100.0" in text          # 口径串引用弱覆盖阈值，不再写死 -80
    assert "-80" not in text
    assert text.count("可用覆盖率") == 1        # 标签不重复
    assert "（可用覆盖率）" not in text          # 无括号嵌套
    assert "口径 RSRP >= -100.0 dBm" in text


# ════════════════════ 11. 扇区化 + 链路余量（v1.6 口径修正）════════════════════

def test_diagnosis_caliber_constants():
    """链路余量/阴影衰落/扇区参数常量值固定（面板 T03 依赖其默认值）。"""
    assert DEFAULT_LINK_MARGIN_DB == 20.0
    assert SHADOW_FADE_DB == 8.0
    assert SECTOR_AZIMUTHS_DEG == (0.0, 120.0, 240.0)
    assert SECTOR_BEAMWIDTH_DEG == 65.0


def test_stats_records_link_margin():
    """stats 记录本次诊断所用链路余量（T09 报告参数快照）。"""
    bbox = (-7.65, 33.55, -7.55, 33.61)
    diag = compute_rsrp_grid([_site(-7.60, 33.58)], bbox,
                             BAND_CONFIGS["2.6GHz"], "4G LTE")
    assert diag.stats["link_margin_db"] == 20.0
    diag2 = compute_rsrp_grid([_site(-7.60, 33.58)], bbox,
                              BAND_CONFIGS["2.6GHz"], "4G LTE", link_margin_db=15.0)
    assert diag2.stats["link_margin_db"] == 15.0


def test_link_margin_monotonicity():
    """链路余量越大，弱覆盖格数单调不减：0 ≤ 20 ≤ 30。"""
    sites = [_site(-7.60, 33.58), _site(-7.57, 33.60)]
    bbox = (-7.64, 33.54, -7.53, 33.64)
    counts = []
    for margin in (0.0, 20.0, 30.0):
        diag = compute_rsrp_grid(sites, bbox, BAND_CONFIGS["2.6GHz"], "4G LTE",
                                 resolution_m=200, link_margin_db=margin)
        diagnose_weak_coverage(diag, -100.0, -110.0)
        counts.append(diag.stats["weak_count"] + diag.stats["blind_count"])
    assert counts[0] <= counts[1] <= counts[2], f"余量单调性被破坏: {counts}"


def test_link_margin_negative_raises():
    """link_margin_db 为负 → ValueError。"""
    with pytest.raises(ValueError):
        compute_rsrp_grid([_site(-7.60, 33.58)], (-7.65, 33.55, -7.55, 33.61),
                          BAND_CONFIGS["2.6GHz"], "4G LTE", link_margin_db=-1.0)


def test_sector_directivity_back_lobe_lower():
    """同距离下后瓣方向 RSRP 比主瓣低 ≥10dB（扇区方向性生效）。

    站点正北 1.5km 落在方位角 0° 扇区主瓣（约 -3dB 方向性损耗）；
    正南 1.5km 落在全部 3 个扇区的后瓣（约 -15dB 损耗）。
    """
    s_lon, s_lat = -7.60, 33.58
    half = 0.100 / 111.0  # ±100m 采样框
    off = 1.5 / 111.0     # 1.5km 的纬度偏移
    bb_north = (s_lon - half, s_lat + off - half, s_lon + half, s_lat + off + half)
    bb_south = (s_lon - half, s_lat - off - half, s_lon + half, s_lat - off + half)
    one = [_site(s_lon, s_lat)]

    diag_n = compute_rsrp_grid(one, bb_north, BAND_CONFIGS["2.6GHz"], "4G LTE",
                               resolution_m=100)
    diag_s = compute_rsrp_grid(one, bb_south, BAND_CONFIGS["2.6GHz"], "4G LTE",
                               resolution_m=100)
    north_max = max(v for row in diag_n.grid for v in row if v > NO_COVERAGE_DBM)
    south_max = max(v for row in diag_s.grid for v in row if v > NO_COVERAGE_DBM)
    assert north_max - south_max >= 10.0, (
        f"主瓣/后瓣 RSRP 差不足 10dB: north={north_max:.2f} south={south_max:.2f}"
    )


def test_demo_scenario_produces_weak_clusters():
    """集成锚点：复现摩洛哥 5km×5km 演示场景，必须产出 ≥1 片弱区。

    旧"全向 + 仅 8dB 阴影"口径下该场景三类频段均为 0 片（功能形同不存在）；
    扇区化 + 20dB 余量后：team-lead 实测 6 片，本地实测 **7 片**。
    断言写 ≥1 以抗数值漂移，注释保留实测值便于日后发现退化。
    """
    lon0, lat0 = -6.8400, 34.0200
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(34.0200)))
    lat_per_km = 1.0 / 111.0
    bbox = (lon0, lat0, lon0 + 5 * lon_per_km, lat0 + 5 * lat_per_km)

    cfg = BAND_CONFIGS["2.6GHz"]
    centers = generate_hex_grid(bbox, cfg.ideal_isr_km)
    engine_sites = generate_sites_from_grid(
        centers, cfg, site_type="MACRO", tower_height=35.0,
        scenario="URBAN", bbox=bbox,
    )
    assert len(engine_sites) == 12  # 演示场景固定 12 站
    sites = [{"longitude": s.longitude, "latitude": s.latitude,
              "tower_height": s.tower_height} for s in engine_sites]

    diag = compute_rsrp_grid(sites, bbox, cfg, "4G LTE",
                             resolution_m=100, environment="URBAN")
    diagnose_weak_coverage(diag, weak_threshold_dbm=-100.0, blind_threshold_dbm=-110.0)
    clusters = cluster_weak_cells(
        diag.weak_cells, cell_m=grid_size_for_band("2.6GHz"), resolution_m=100,
    )
    assert len(clusters) >= 1, f"演示场景应产出 ≥1 片弱区，实测 {len(clusters)} 片"
    assert diag.stats["link_margin_db"] == 20.0


# ════════════════════ 12. 扇区数跟随站点数据 + 可用覆盖率（v1.7）════════════════════

def test_azimuths_for_site_semantics():
    """方位角推导：缺键回退 / 0(全向)→空元组 / N>0 均分且起始 0°。"""
    assert _azimuths_for_site({"longitude": 0.0, "latitude": 0.0}) == SECTOR_AZIMUTHS_DEG
    # ⚠️ 0 是 falsy，绝不能被误判成"缺省" —— 必须返回空元组（全向）
    assert _azimuths_for_site({"num_sectors": 0}) == ()
    assert _azimuths_for_site({"num_sectors": 3}) == (0.0, 120.0, 240.0)
    assert _azimuths_for_site({"num_sectors": 6}) == (0.0, 60.0, 120.0, 180.0, 240.0, 300.0)


def test_azimuths_for_site_clamps_large_value():
    """num_sectors=999999 → 静默截断到 MAX_SECTORS=64，间距 360/64，前 3 项按 i*360/64。"""
    assert MAX_SECTORS == 64
    az = _azimuths_for_site({"num_sectors": 999999})
    assert len(az) == 64
    assert az[:3] == pytest.approx((0.0, 360.0 / 64, 720.0 / 64))
    assert az[1] - az[0] == pytest.approx(360.0 / 64)
    assert az[-1] == pytest.approx(63 * 360.0 / 64)


def test_azimuths_for_site_clamp_at_64_not_truncated():
    """边界：num_sectors=64 不截断（长度仍 64）。"""
    assert len(_azimuths_for_site({"num_sectors": 64})) == 64


def test_azimuths_for_site_clamp_65_truncated():
    """边界：num_sectors=65 截断到 64。"""
    az = _azimuths_for_site({"num_sectors": 65})
    assert len(az) == 64
    assert az == _azimuths_for_site({"num_sectors": 64})


def test_azimuths_for_site_regression_counts():
    """回归：3→3；0 与 -5→()；缺键→3（clamp 不得改变这三条分支）。"""
    assert len(_azimuths_for_site({"num_sectors": 3})) == 3
    assert _azimuths_for_site({"num_sectors": 0}) == ()
    assert _azimuths_for_site({"num_sectors": -5}) == ()
    assert len(_azimuths_for_site({"longitude": 0.0, "latitude": 0.0})) == 3


def test_demo_numbers_unchanged_after_clamp():
    """防回归锚点：演示场景（12站/2.6GHz/5×5km/100m/余量20/3扇区）仍是 340/8/7/86.1。"""
    diag, _, _ = _demo_diagnose(3)
    stats = diag.stats
    clusters = cluster_weak_cells(
        diag.weak_cells, cell_m=grid_size_for_band("2.6GHz"), resolution_m=100,
    )
    assert stats["weak_count"] == 340
    assert stats["blind_count"] == 8
    assert len(clusters) == 7
    assert abs(stats["coverage_rate_pct"] - 86.1) <= 0.1


def test_omni_sector_count_lowers_weak():
    """num_sectors=0（全向）不施加方向图损失 → 弱格数 < 同场景 3 扇区。"""
    weak_omni = _demo_diagnose(0)[0].stats["weak_count"]
    weak_3 = _demo_diagnose(3)[0].stats["weak_count"]
    assert weak_omni < weak_3, f"全向({weak_omni}) 应少于 3 扇区({weak_3})"


def test_six_sectors_lowers_weak_and_saturates():
    """6 扇区弱格 < 3 扇区（实测 39 vs 340）；且 6 与 12 扇区逐格一致（缺口消失后饱和）。"""
    diag3, _, _ = _demo_diagnose(3)
    diag6, _, _ = _demo_diagnose(6)
    diag12, _, _ = _demo_diagnose(12)
    assert diag6.stats["weak_count"] < diag3.stats["weak_count"]
    assert diag6.grid == diag12.grid, "6/12 扇区应逐格一致（角向缺口已消失）"


def test_missing_num_sectors_falls_back_to_three():
    """站点 dict 不含 num_sectors 时，结果必须与显式 3 扇区**逐格一致**。"""
    diag_fallback, _, _ = _demo_diagnose("OMIT")
    diag3, _, _ = _demo_diagnose(3)
    assert diag_fallback.grid == diag3.grid


def test_available_coverage_complementary():
    """可用覆盖率 + 弱覆盖占比 + 盲区占比 = 100%（容差 0.1）。"""
    stats = _demo_diagnose(3)[0].stats
    comp = (stats["coverage_rate_pct"]
            + (stats["weak_count"] + stats["blind_count"]) / stats["total_cells"] * 100.0)
    assert abs(comp - 100.0) <= 0.1, f"三档占比不互补: {comp}"


def test_demo_available_coverage_and_caliber():
    """演示场景可用覆盖率 ≈ 86.1%；caliber 为纯描述、label 为标签（拆分后不互相包含）。"""
    stats = _demo_diagnose(3)[0].stats
    assert abs(stats["coverage_rate_pct"] - 86.1) <= 0.5
    assert stats["coverage_caliber"] == "RSRP >= -100.0 dBm"
    assert "可用覆盖率" not in stats["coverage_caliber"]     # 后缀已移除
    assert stats["coverage_caliber_label"] == "可用覆盖率"


def test_summarize_label_not_duplicated():
    """状态回显里「可用覆盖率」只出现 1 次，且无「（可用覆盖率）」嵌套片段。"""
    diag, _, _ = _demo_diagnose(3)
    text = summarize_diagnosis(diag)
    assert text.count("可用覆盖率") == 1
    assert "（可用覆盖率）" not in text
    assert "口径 RSRP >= -100.0 dBm" in text


# ════════════════════ 13. 结果说明分流 build_result_notice ════════════════════

def _notice_stats(weak_count, blind_count=0, rate=90.9):
    return {
        "weak_count": weak_count,
        "blind_count": blind_count,
        "coverage_rate_pct": rate,
        "coverage_caliber": "RSRP >= -100.0 dBm",
    }


def test_result_notice_none_when_suggested():
    """正常产出建议站（弱格>0 且建议站>0）→ 返回 None，不弹框。"""
    notice = build_result_notice(
        _notice_stats(340, 8, 86.1), cluster_count=7, suggested_count=7,
        cell_m=1000.0, resolution_m=100)
    assert notice is None


def test_result_notice_no_weak():
    """确实无弱覆盖 → 非 None，正文含「未发现弱覆盖区」。"""
    notice = build_result_notice(
        _notice_stats(0, 0, 100.0), cluster_count=0, suggested_count=0,
        cell_m=1000.0, resolution_m=100)
    assert notice is not None
    assert notice[0] == "覆盖诊断"
    assert "未发现弱覆盖区" in notice[1]
    assert "太零散" not in notice[1]
    assert "去重" not in notice[1]


def test_result_notice_scattered_not_reported_as_empty():
    """弱格>0 但聚不成片 → 必须说「太零散」，且**不得**说「未发现弱覆盖区」。"""
    notice = build_result_notice(
        _notice_stats(214, 0, 91.4), cluster_count=0, suggested_count=0,
        cell_m=1000.0, resolution_m=100)
    assert notice is not None
    body = notice[1]
    assert "太零散" in body
    assert "未发现弱覆盖区" not in body
    assert "高频段" not in body
    # 判定门槛：cell_m=1000 / res=100 → max(1, round(0.2*100)) = 20 格
    assert "至少 20 个弱覆盖栅格" in body


def test_result_notice_deduped():
    """已聚成片但建议站被去重合并 → 说明去重，属正常结论。"""
    notice = build_result_notice(
        _notice_stats(214, 0, 91.4), cluster_count=2, suggested_count=0,
        cell_m=1000.0, resolution_m=100)
    assert notice is not None
    body = notice[1]
    assert "去重" in body
    assert "未发现弱覆盖区" not in body
    assert "太零散" not in body


def test_result_notice_never_mentions_higher_band():
    """防回归：任何分支的正文都不得出现「换用更高频段 / 高频段」字样。"""
    cases = [
        (_notice_stats(0, 0, 100.0), 0, 0),
        (_notice_stats(214, 0, 91.4), 0, 0),
        (_notice_stats(214, 0, 91.4), 2, 0),
        (_notice_stats(340, 8, 86.1), 7, 7),
    ]
    for stats, cluster_count, suggested_count in cases:
        notice = build_result_notice(stats, cluster_count, suggested_count,
                                     cell_m=1000.0, resolution_m=100)
        if notice is not None:
            assert "换用更高频段" not in notice[1]
            assert "高频段" not in notice[1]


def test_success_notice_mentions_counts():
    """成功说明必须回显弱格数 / 聚片数 / 建议站数（成功也要弹框告知）。"""
    notice = build_success_notice(_notice_stats(340, 12, 86.1), 7, 7)
    assert notice is not None
    assert notice[0] == "覆盖诊断 · 已生成补站建议"
    body = notice[1]
    assert "340" in body
    assert "7 片" in body
    assert "7 个建议补站" in body


def test_success_notice_tolerates_missing_keys():
    """空 stats 不得抛异常，需回显 0 处 / 0 个建议补站。"""
    notice = build_success_notice({}, 0, 0)
    assert notice is not None
    body = notice[1]
    assert "0 处" in body
    assert "0 个建议补站" in body


def test_success_notice_never_none_on_success_path():
    """成功路径：build_result_notice 返回 None，但 build_success_notice 恒非 None（成功也弹）。"""
    stats = _notice_stats(340, 12, 86.1)
    assert build_result_notice(stats, 7, 7, cell_m=1000.0, resolution_m=100) is None
    assert build_success_notice(stats, 7, 7) is not None


def test_notice_fallback_never_none_for_all_eight_combos():
    """全 8 组合穷尽：UI 的 ``notice[0]`` / ``notice[1]`` 对每组都必须拿到 2 元组，绝不 None。

    防回归 1：若有人把某个分支改成返回 ``None``，UI 那行 ``QMessageBox.information(
    self, notice[0], notice[1])`` 会直接 ``AttributeError`` 崩掉。
    防回归 2：固化历史 bug 场景分流（340 弱格 / 0 聚类 → 「太零散」，
    绝不说「未发现弱覆盖区」）。
    """
    for weak_count in (0, 340):
        for cluster_count in (0, 7):
            for suggested_count in (0, 7):
                stats = _notice_stats(weak_count, 0, 86.1)
                notice = (build_result_notice(stats, cluster_count, suggested_count,
                                              1000, 100)
                          or build_success_notice(stats, cluster_count, suggested_count))
                assert notice is not None, (
                    f"组合 weak={weak_count} cluster={cluster_count} "
                    f"suggested={suggested_count} 回退后仍为 None")
                assert isinstance(notice, tuple) and len(notice) == 2
                assert notice[0] and notice[1]

    # 历史 bug 场景：340 弱格 / 0 聚类 → 「太零散」，绝不说「未发现弱覆盖区」。
    scattered = build_result_notice(_notice_stats(340, 0, 86.1), 0, 0, 1000, 100)
    assert scattered is not None
    assert "太零散" in scattered[1]
    assert "未发现弱覆盖区" not in scattered[1]


# ──────────────────────── next_site_seq（采纳站序号分配）────────────────────────

def test_next_site_seq_basic():
    """空列表 → 1；连续 001..003 → 4；有洞（001/005）→ 6；四位后缀 → 1001。"""
    assert next_site_seq([]) == 1
    assert next_site_seq([
        {"site_id": "BTS-URBA-001"},
        {"site_id": "BTS-URBA-002"},
        {"site_id": "BTS-URBA-003"},
    ]) == 4
    # 洞：用 len+1 会得到 3（撞已存在的 005 之外又会撞 003 之后的空号策略），
    # 用「最大后缀+1」得到 6，保证唯一。
    assert next_site_seq([
        {"site_id": "BTS-URBA-001"},
        {"site_id": "BTS-URBA-005"},
    ]) == 6
    # 四位后缀不被 3 位格式化截断。
    assert next_site_seq([{"site_id": "BTS-X-1000"}]) == 1001


def test_next_site_seq_tolerates_nonstandard_ids():
    """容忍 site_id 缺失 / None / 非字符串 / 无 '-' / 后缀非数字：均忽略。"""
    assert next_site_seq([
        {"site_id": "BTS-URBA-002"},
        {"site_id": None},
        {"site_id": "A"},
        {"site_id": "SITE"},
        {"site_id": "BTS-X-"},        # 无后缀数字
        {"site_id": "BTS-X-abc"},     # 后缀非数字
        {},                            # 缺 site_id
        {"name": "no-id"},
    ]) == 3
    # 全为非规范项 → 回退到 1（不能抛异常）。
    assert next_site_seq([{"site_id": None}, {"site_id": "A"}, {}]) == 1
