"""补盲前后对比 · 纯函数单测 + AST 锁 — design_engine/gap_diagnosis.py

硬约束：不依赖 QGIS/PyQt，普通 pytest 可跑。
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_engine.rules import BAND_CONFIGS
from design_engine.gap_diagnosis import (
    compute_rsrp_grid,
    diagnose_weak_coverage,
    cluster_weak_cells,
    score_cluster,
    build_suggested_sites,
    dedupe_suggested_sites,
    grid_size_for_band,
    shadow_diagnose_metrics,
    build_comparison_rows,
    format_comparison_report,
    _metrics_from_diag,
    COMPARISON_METRICS,
    DEFAULT_WEAK_THRESHOLD_DBM,
    DEFAULT_BLIND_THRESHOLD_DBM,
)

GD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "design_engine", "gap_diagnosis.py")

# 小场地：摩洛哥附近，约 3km × 3.3km
BBOX = (-8.55, 33.20, -8.52, 33.23)
TECH = "4G LTE"
SCENARIO = "URBAN"
RES = 100
MARGIN = 22.0

METRIC_KEYS = {
    "site_count", "coverage_rate_pct", "weak_count", "blind_count",
    "weak_area_km2", "no_coverage_count", "cluster_count", "suggested_site_count",
}


def _fake_sites(n, spacing=0.005):
    sites = []
    for i in range(n):
        sites.append({
            "longitude": BBOX[0] + 0.010 + i * spacing,
            "latitude": (BBOX[1] + BBOX[3]) / 2.0,
            "tower_height": 35.0,
            "num_sectors": 3,
        })
    return sites


def _gap_params():
    return {
        "band_key": "2.6GHz", "tech": TECH, "scenario": SCENARIO,
        "tower_height": 35.0, "num_sectors": 3,
        "link_margin_db": MARGIN, "resolution_m": RES, "bbox": BBOX,
    }


def test_metrics_from_diag_has_all_eight_keys():
    diag = compute_rsrp_grid(_fake_sites(3), BBOX, BAND_CONFIGS["2.6GHz"], TECH,
                             resolution_m=RES, environment=SCENARIO,
                             link_margin_db=MARGIN)
    diagnose_weak_coverage(diag)
    m = _metrics_from_diag(diag, 2, 1)
    assert set(m.keys()) == METRIC_KEYS


def test_comparison_rows_direction_semantics():
    before = {"site_count": 5, "coverage_rate_pct": 80.0, "weak_count": 100,
              "blind_count": 10, "weak_area_km2": 1.2, "no_coverage_count": 5,
              "cluster_count": 3, "suggested_site_count": 4}
    after = {"site_count": 6, "coverage_rate_pct": 90.0, "weak_count": 50,
             "blind_count": 5, "weak_area_km2": 0.6, "no_coverage_count": 2,
             "cluster_count": 2, "suggested_site_count": 1}
    rows = build_comparison_rows(before, after)
    assert len(rows) == len(COMPARISON_METRICS) == 8
    by_key = {r["key"]: r for r in rows}
    assert by_key["coverage_rate_pct"]["direction"] == "improved"   # up + 升
    assert by_key["weak_count"]["direction"] == "improved"          # down + 降
    assert by_key["suggested_site_count"]["direction"] == "improved"
    assert by_key["site_count"]["direction"] == "neutral"           # 基站数无关方向
    # delta 符号正确
    assert by_key["weak_count"]["delta"] == -50.0


def test_comparison_rows_unchanged_and_neutral():
    before = {"site_count": 5, "coverage_rate_pct": 80.0, "weak_count": 100,
              "blind_count": 10, "weak_area_km2": 1.2, "no_coverage_count": 5,
              "cluster_count": 3, "suggested_site_count": 4}
    rows = build_comparison_rows(before, dict(before))
    for r in rows:
        assert r["direction"] in ("unchanged", "neutral")


def test_format_comparison_report_contains_all_metrics():
    before = {"site_count": 5, "coverage_rate_pct": 80.0, "weak_count": 100,
              "blind_count": 10, "weak_area_km2": 1.2, "no_coverage_count": 5,
              "cluster_count": 3, "suggested_site_count": 4}
    after = {"site_count": 6, "coverage_rate_pct": 90.0, "weak_count": 50,
             "blind_count": 5, "weak_area_km2": 0.6, "no_coverage_count": 2,
             "cluster_count": 2, "suggested_site_count": 1}
    rep = format_comparison_report(build_comparison_rows(before, after))
    for label in ("基站数", "可用覆盖率", "弱覆盖栅格", "盲区栅格", "弱覆盖面积",
                  "无覆盖栅格", "聚成片数", "仍需补站"):
        assert label in rep
    assert "↑好" in rep and "·" in rep


def test_shadow_diagnose_deterministic():
    """同输入同输出（幂等/确定性）= 零采纳自洽自检的基石。"""
    sites = _fake_sites(3)
    cfg = BAND_CONFIGS["2.6GHz"]
    params = _gap_params()
    m1 = shadow_diagnose_metrics(sites, params, cfg)
    m2 = shadow_diagnose_metrics(sites, params, cfg)
    assert m1 == m2
    assert set(m1.keys()) == METRIC_KEYS


def test_shadow_diagnose_before_equals_after_same_sites():
    """零采纳自洽：同一组站点、同一参数，影子诊断结果必须 == 诊断时快照。"""
    sites = _fake_sites(4)
    cfg = BAND_CONFIGS["2.6GHz"]
    params = _gap_params()
    diag = compute_rsrp_grid(sites, params["bbox"], cfg, params["tech"],
                             resolution_m=params["resolution_m"],
                             environment=params["scenario"],
                             link_margin_db=params["link_margin_db"])
    diagnose_weak_coverage(diag)
    cell_m = grid_size_for_band(params["band_key"])
    clusters = cluster_weak_cells(diag.weak_cells, cell_m=cell_m,
                                 resolution_m=params["resolution_m"])
    for c in clusters:
        c.demand_score = score_cluster(c, DEFAULT_WEAK_THRESHOLD_DBM,
                                      DEFAULT_BLIND_THRESHOLD_DBM)
    sugs = build_suggested_sites(clusters, params["tech"], params["band_key"])
    kept, merged = dedupe_suggested_sites(
        sugs, sites, layout_isr_m=cfg.ideal_isr_km * 1000)
    before = _metrics_from_diag(diag, len(clusters), len(kept))
    after = shadow_diagnose_metrics(sites, params, cfg)
    assert before == after


def test_shadow_diagnose_monotonic_improves_with_extra_site_in_weak_area():
    """在弱/盲区补一个站：弱+盲区格总数应严格下降（prefer=down 的单调自检）。"""
    sites = _fake_sites(2)
    cfg = BAND_CONFIGS["2.6GHz"]
    params = _gap_params()
    before = shadow_diagnose_metrics(sites, params, cfg)
    # 取一个弱/盲区格中心，在其上补站（必然改善该格及其邻域）
    diag = compute_rsrp_grid(sites, params["bbox"], cfg, params["tech"],
                             resolution_m=params["resolution_m"],
                             environment=params["scenario"],
                             link_margin_db=params["link_margin_db"])
    diagnose_weak_coverage(diag)
    weak = [c for c in diag.weak_cells if c.level in ("weak", "blind")]
    assert weak, "构造的场景应存在弱/盲区，否则单调性断言无意义"
    target = weak[0]
    extra = [{"longitude": target.lon, "latitude": target.lat,
              "tower_height": 35.0, "num_sectors": 3}]
    after = shadow_diagnose_metrics(sites + extra, params, cfg)
    assert (after["weak_count"] + after["blind_count"]) < \
           (before["weak_count"] + before["blind_count"])
    assert after["site_count"] == before["site_count"] + 1


def test_shadow_diagnose_must_not_draw_layers():
    """AST 锁：shadow_diagnose_metrics 不得调用任何图层函数
    （remove_gap_layers / build_rsrp_weak_layer / build_suggested_sites_layer），
    也不得 import layers.gap_layer。违反 = 影子诊断污染/重画诊断图层，
    违背「只算不画」铁律，也会改写调用方的 _suggested_sites 语义。"""
    with open(GD_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    fn = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "shadow_diagnose_metrics":
            fn = n
            break
    assert fn is not None, "未找到 shadow_diagnose_metrics"
    calls = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f1 = n.func
            if isinstance(f1, ast.Attribute):
                calls.add(f1.attr)
            elif isinstance(f1, ast.Name):
                calls.add(f1.id)
    for forbidden in ("remove_gap_layers", "build_rsrp_weak_layer",
                     "build_suggested_sites_layer"):
        assert forbidden not in calls, \
            f"shadow_diagnose_metrics 调用了 {forbidden} —— 违反「只算不画」铁律"
    has_layers_import = any(
        isinstance(n, ast.ImportFrom) and n.module == "layers.gap_layer"
        for n in ast.walk(tree))
    assert not has_layers_import, "gap_diagnosis.py 不应 import layers.gap_layer"
