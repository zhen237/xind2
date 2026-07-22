"""
拓扑引擎传播模型 + 接口测试。

与 Java 端 PropagationModelTest 共享同一权威基准（Okumura-Hata）：
    f=900MHz, hb=30m, hm=1.5m, d=1km, 城区 → 路径损耗 ≈ 126.4 dB
两种独立语言实现都通过该基准，互相审计（交叉验证）。

运行：在 packages/m03-topology-engine 下 `pytest -q`
"""
import math

import main
from fastapi.testclient import TestClient

# 共享 Oracle（与 Java computePathLossDb 同一基准）
ORACLE_900_1KM_URBAN = 126.4


def test_okumura_hata_oracle():
    """① Oracle：与 Okumura-Hata 文献经典值对齐"""
    L = main.calculate_okumura_hata_path_loss(900, 1.0, 30, 1.5, "URBAN")
    assert abs(L - ORACLE_900_1KM_URBAN) < 0.5


def test_pathloss_monotonic_distance():
    """② Invariant：路径损耗随距离单调递增"""
    near = main.calculate_okumura_hata_path_loss(1800, 0.5, 30, 1.5, "URBAN")
    far = main.calculate_okumura_hata_path_loss(1800, 2.0, 30, 1.5, "URBAN")
    assert far > near


def test_pathloss_monotonic_frequency():
    """② Invariant：路径损耗随频率单调递增（>200MHz 频段内）"""
    low = main.calculate_okumura_hata_path_loss(1800, 0.5, 30, 1.5, "URBAN")
    high = main.calculate_okumura_hata_path_loss(2600, 0.5, 30, 1.5, "URBAN")
    assert high > low


def test_scenario_ordering():
    """② Invariant：环境修正顺序 城区>郊区>农村 路径损耗"""
    urban = main.calculate_okumura_hata_path_loss(1800, 0.5, 30, 1.5, "URBAN")
    suburban = main.calculate_okumura_hata_path_loss(1800, 0.5, 30, 1.5, "SUBURBAN")
    rural = main.calculate_okumura_hata_path_loss(1800, 0.5, 30, 1.5, "RURAL")
    assert urban > suburban > rural


def test_rsrp_monotonic_oracle():
    """① Oracle：1800MHz/30m/0.5km/城区 的 RSRP ≈ -54.7dBm"""
    rsrp = main.calculate_rsrp(1800, 30)
    assert abs(rsrp - (-54.7)) < 0.2


def test_generate_hex_grid_count():
    """确定性回归：覆盖半径1000m、网格200m → 61 个候选站址（与线上一致）"""
    req = main.GenerateRequest(
        center_longitude=111.0,
        center_latitude=35.0,
        coverage_radius=1000,
        grid_size=200,
    )
    centers = main.generate_hex_grid(req)
    assert len(centers) == 61


def test_health_endpoint():
    """接口：/health 返回 200 + ok"""
    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_generate_endpoint_site_count():
    """接口：/generate 返回 200 且站点数为确定性 61"""
    client = TestClient(main.app)
    resp = client.post("/generate", json={
        "project_id": 1,
        "scheme_name": "测试方案",
        "template_type": "macro",
        "center_longitude": 111.0,
        "center_latitude": 35.0,
        "coverage_radius": 1000,
        "grid_size": 200,
        "frequency_band": "fdd-lte-1800",
        "scenario": "urban",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_sites"] == 61
    assert body["valid_sites"] >= 1
