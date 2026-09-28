"""
拓扑引擎 fail-fast 回归测试。

覆盖两个真实生产事故：
  1. Java 端把 `frequency_band` 显式下发为 null → Pydantic 覆盖默认值 → get_frequency_mhz
     对 None 调 .lower() → 500。修复后应返回 200（频段走 2000MHz 兜底）。
  2. 漏传中心点 → 引擎曾静默回退北京默认坐标，页面落出 61 个北京点。修复后应返回
     422 且 detail 明确指出缺少 center_longitude/center_latitude。

运行：在 packages/m03-topology-engine 下 `pytest -q`
"""
import main
from fastapi.testclient import TestClient


def test_generate_missing_center_returns_422():
    """① 不传中心点 → 422，且 detail 指明缺少 center_longitude（禁止静默回退默认中心点）"""
    client = TestClient(main.app)
    resp = client.post("/generate", json={
        "project_id": 1,
        "frequency_band": None,
    })
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"
    detail = resp.json()["detail"]
    assert "center_longitude" in detail, f"detail 未指明缺失中心点: {detail}"


def test_generate_frequency_band_null_returns_200():
    """② 显式 frequency_band=null（带显式中心点）→ 200，证明不再 500"""
    client = TestClient(main.app)
    resp = client.post("/generate", json={
        "center_longitude": -8.53,
        "center_latitude": 33.21,
        "frequency_band": None,
        "coverage_radius": 200,
        "grid_size": 200,
    })
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"


def test_generate_sites_land_in_morocco():
    """③ 摩洛哥中心点 → 200，且所有站点经度均为负（落在摩洛哥，而非北京）"""
    client = TestClient(main.app)
    resp = client.post("/generate", json={
        "center_longitude": -8.53,
        "center_latitude": 33.21,
        "frequency_band": "fdd-lte-1800",
        "coverage_radius": 200,
        "grid_size": 200,
    })
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert len(body["sites"]) > 0, "站点列表为空"
    lons = [s["longitude"] for s in body["sites"]]
    assert all(lon < 0 for lon in lons), f"存在非负经度(疑似北京落点): {lons}"
