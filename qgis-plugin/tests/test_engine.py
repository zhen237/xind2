"""设计引擎单元测试"""
import sys
import os
import math
import tempfile

# 添加插件目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.site import Site
from models.antenna import Antenna
from design_engine.rules import BAND_CONFIGS, DEFAULT_SITE_PARAMS
from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
from design_engine.coverage import (
    okumura_hata_path_loss, calculate_rsrp, power_w_to_dbm,
    generate_coverage_raster, rsrp_to_color,
)
from design_engine.avoidance import AvoidanceChecker
from design_engine.persistence import save_design, load_design, list_designs
from models.machine_room import MachineRoom
from design_engine.coverage_heatmap import generate_coverage_heatmap_data


def test_antenna_model():
    """测试天线数据模型"""
    ant = Antenna(
        antenna_type="AAU5313",
        azimuth=120.0,
        mechanical_tilt=2.0,
        electrical_tilt=6.0,
        height=35.0,
        band="3.5GHz",
        power=200.0,
        gain=24.0,
    )
    d = ant.to_dict()
    assert d["type"] == "AAU5313"
    assert d["azimuth"] == 120.0
    assert d["band"] == "3.5GHz"

    # 测试反序列化
    ant2 = Antenna.from_dict(d)
    assert ant2.antenna_type == "AAU5313"
    assert ant2.azimuth == 120.0
    print("  [PASS] Antenna model")


def test_site_model():
    """测试站点数据模型"""
    ant = Antenna(azimuth=0.0, band="3.5GHz")
    site = Site(
        site_id="BTS-WH-001",
        name="光谷广场站",
        longitude=114.390,
        latitude=30.506,
        site_type="MACRO",
        tower_height=45.0,
        antennas=[ant],
    )

    # 测试GeoJSON序列化
    feature = site.to_geojson_feature()
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Point"
    assert feature["properties"]["siteId"] == "BTS-WH-001"
    assert len(feature["properties"]["antennas"]) == 1

    # 测试反序列化
    site2 = Site.from_geojson_feature(feature)
    assert site2.site_id == "BTS-WH-001"
    assert site2.longitude == 114.390
    assert len(site2.antennas) == 1
    print("  [PASS] Site model")


def test_site_distance():
    """测试站点距离计算"""
    s1 = Site("A", "A", 114.390, 30.506)
    s2 = Site("B", "B", 114.400, 30.516)
    dist = s1.distance_to(s2)
    assert 1.0 < dist < 2.0  # 大约1.4km
    print(f"  [PASS] Site distance: {dist:.2f} km")


def test_hex_grid():
    """测试六边形网格生成"""
    bbox = (114.35, 30.48, 114.45, 30.55)
    centers = generate_hex_grid(bbox, isr_km=0.5)
    assert len(centers) > 0
    print(f"  [PASS] Hex grid: {len(centers)} centers generated")

    # 验证所有点在bbox范围内（允许少量超出）
    in_range = sum(1 for lon, lat in centers
                   if 114.34 <= lon <= 114.46 and 30.47 <= lat <= 30.56)
    assert in_range == len(centers)
    print(f"  [PASS] All {in_range} centers in extended range")


def test_generate_sites():
    """测试站点生成"""
    bbox = (114.35, 30.48, 114.45, 30.55)
    band_config = BAND_CONFIGS["3.5GHz"]
    centers = generate_hex_grid(bbox, isr_km=band_config.ideal_isr_km)
    sites = generate_sites_from_grid(
        centers, band_config=band_config,
        site_type="MACRO", tower_height=35.0,
        num_sectors=3, bbox=bbox,
    )
    assert len(sites) > 0
    assert all(s.site_type == "MACRO" for s in sites)
    assert all(len(s.antennas) == 3 for s in sites)
    print(f"  [PASS] Generated {len(sites)} sites with 3 antennas each")


def test_okumura_hata():
    """测试Okumura-Hata传播模型"""
    # 城市场景，1km距离
    loss = okumura_hata_path_loss(3500, 1.0, 35.0, 1.5, "URBAN")
    assert 100 < loss < 180  # 合理范围
    print(f"  [PASS] Okumura-Hata path loss at 1km: {loss:.1f} dB")

    # 距离增加，损耗增大
    loss2 = okumura_hata_path_loss(3500, 2.0, 35.0, 1.5, "URBAN")
    assert loss2 > loss
    print(f"  [PASS] Path loss increases with distance: {loss2:.1f} dB at 2km")

    # 郊区场景损耗应小于城市
    loss_sub = okumura_hata_path_loss(3500, 1.0, 35.0, 1.5, "SUBURBAN")
    assert loss_sub < loss
    print(f"  [PASS] Suburban loss < Urban loss: {loss_sub:.1f} dB")


def test_rsrp_calculation():
    """测试RSRP计算"""
    tx_power_dbm = power_w_to_dbm(200)  # 200W = 53dBm
    assert 52 < tx_power_dbm < 54

    path_loss = okumura_hata_path_loss(3500, 0.5, 35.0)
    rsrp = calculate_rsrp(tx_power_dbm, 24.0, path_loss)
    assert -120 < rsrp < -50
    print(f"  [PASS] RSRP at 500m: {rsrp:.1f} dBm")


def test_coverage_raster():
    """测试覆盖栅格生成"""
    raster = generate_coverage_raster(
        site_lon=114.390,
        site_lat=30.506,
        tx_height_m=35.0,
        frequency_mhz=3500,
        tx_power_w=200.0,
        antenna_gain_dbi=24.0,
        radius_km=0.5,
        resolution_m=100,
        rsrp_threshold_dbm=-110,
    )
    assert raster["type"] == "FeatureCollection"
    assert len(raster["features"]) > 0
    print(f"  [PASS] Coverage raster: {len(raster['features'])} points")

    # 验证所有点都有RSRP值
    for feat in raster["features"][:10]:
        assert "rsrp" in feat["properties"]
        assert "distance_km" in feat["properties"]
    print("  [PASS] All points have RSRP values")


def test_rsrp_color():
    """测试RSRP颜色映射"""
    r, g, b, a = rsrp_to_color(-50)   # 强信号 → 绿色
    assert g > r
    r, g, b, a = rsrp_to_color(-110)  # 弱信号 → 红色
    assert r > g
    r, g, b, a = rsrp_to_color(-85)   # 中等 → 黄色
    assert r > 200 and g > 200
    print("  [PASS] RSRP color mapping")


def test_avoidance_checker():
    """测试避让检查器"""
    checker = AvoidanceChecker()

    # 手动添加一个避让区域
    checker.add_manual_polygon(
        [(114.38, 30.50), (114.40, 30.50), (114.40, 30.52), (114.38, 30.52)],
        "测试区域",
        buffer_m=0,
    )

    # 区域内的点应该无效
    ok, reasons = checker.is_site_valid(114.39, 30.51)
    assert not ok
    assert len(reasons) > 0
    print(f"  [PASS] Site in avoidance zone detected: {reasons}")

    # 区域外的点应该有效
    ok, reasons = checker.is_site_valid(114.45, 30.55)
    assert ok
    assert len(reasons) == 0
    print("  [PASS] Site outside avoidance zone is valid")


def test_band_configs():
    """测试频段配置"""
    assert "3.5GHz" in BAND_CONFIGS
    assert "700MHz" in BAND_CONFIGS
    assert BAND_CONFIGS["3.5GHz"].frequency_mhz == 3500
    assert BAND_CONFIGS["3.5GHz"].ideal_isr_km == 0.5
    print("  [PASS] Band configs")


def test_save_load_design():
    """测试方案保存和加载"""
    ant = Antenna(band="3.5GHz", power=200.0, gain=24.0)
    sites = [
        Site(site_id="BTS-001", name="站点1", longitude=114.39, latitude=30.48, antennas=[ant]),
        Site(site_id="BTS-002", name="站点2", longitude=114.40, latitude=30.49, antennas=[ant]),
    ]
    params = {"band": "3.5GHz", "tower_height": 35, "grid_size": 0.5}

    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_design(sites, params, tmpdir, name="test_design")
        assert os.path.exists(path), f"文件未创建: {path}"
        assert path.endswith(".geojson")

        loaded_sites, loaded_params = load_design(path)
        assert len(loaded_sites) == 2, f"站点数量不匹配: {len(loaded_sites)}"
        assert loaded_sites[0].name == "站点1"
        assert loaded_sites[1].longitude == 114.40
        assert loaded_params["band"] == "3.5GHz"
        assert loaded_params["tower_height"] == 35
    print("  [PASS] save/load design")


def test_list_designs():
    """测试方案列表"""
    ant = Antenna(band="3.5GHz")
    site = Site(site_id="BTS-001", name="测试站", longitude=114.39, latitude=30.48, antennas=[ant])

    with tempfile.TemporaryDirectory() as tmpdir:
        save_design([site], {"band": "3.5GHz"}, tmpdir, name="design_a")
        save_design([site, site], {"band": "2.6GHz"}, tmpdir, name="design_b")

        designs = list_designs(tmpdir)
        assert len(designs) == 2, f"方案数量不匹配: {len(designs)}"
        assert all("name" in d for d in designs), "缺少name字段"
        assert all("site_count" in d for d in designs), "缺少site_count字段"
    print("  [PASS] list designs")


    print("  [PASS] list designs")


def test_machine_room():
    """测试机房数据模型"""
    room = MachineRoom(
        room_id="ROOM-001",
        name="光谷机房",
        longitude=114.390,
        latitude=30.506,
        room_type="汇聚机房",
        capacity=100.0,
    )
    d = room.to_dict()
    assert d["room_id"] == "ROOM-001"
    assert d["capacity"] == 100.0

    room2 = MachineRoom.from_dict(d)
    assert room2.name == "光谷机房"
    assert room2.longitude == 114.390
    print("  [PASS] MachineRoom model")


def test_pipeline_routes():
    """测试管线路由生成"""
    from design_engine.pipeline import (
        calculate_distance, generate_direct_route,
        generate_manhattan_route, generate_pipelines_for_sites,
        generate_shared_pipelines, find_shared_segments,
        calculate_shared_engineering_volume,
    )
    from design_engine.pipeline import PipelineType

    # 计算距离
    dist = calculate_distance(114.39, 30.50, 114.40, 30.51)
    assert 1000 < dist < 2000  # 约1.4km
    print(f"  [PASS] Distance: {dist:.0f}m")

    # 直线路由
    direct = generate_direct_route(114.39, 30.50, 114.40, 30.51, num_points=5)
    assert len(direct) == 6
    assert direct[0] == (114.39, 30.50)
    assert direct[-1] == (114.40, 30.51)
    print("  [PASS] Direct route")

    # 曼哈顿路由
    manhattan = generate_manhattan_route(114.39, 30.50, 114.40, 30.51)
    assert len(manhattan) > 2
    assert manhattan[0] == (114.39, 30.50)
    assert manhattan[-1] == (114.40, 30.51)
    print("  [PASS] Manhattan route")

    # 批量管线生成
    sites = [
        {"site_id": "S1", "longitude": 114.39, "latitude": 30.50},
        {"site_id": "S2", "longitude": 114.40, "latitude": 30.51},
    ]
    pipelines = generate_pipelines_for_sites(
        sites, room_lon=114.38, room_lat=30.49,
        pipeline_type=PipelineType.DIRECT_BURIED, route_type="direct",
    )
    assert len(pipelines) == 2
    assert pipelines[0].pipeline_id == "PL-0001"
    assert pipelines[0].start_site_id == "S1"
    print(f"  [PASS] Generated {len(pipelines)} pipelines")

    # 共享管线检测
    shared_pipelines, shared_segments = generate_shared_pipelines(
        sites, room_lon=114.38, room_lat=30.49,
        pipeline_type=PipelineType.DIRECT_BURIED, route_type="direct",
    )
    assert len(shared_pipelines) == 2
    print(f"  [PASS] Shared segments: {len(shared_segments)}")

    # 共享工程量计算
    volume = calculate_shared_engineering_volume(shared_pipelines, shared_segments)
    assert volume["管线总数"] == 2
    assert volume["原始总长度(m)"] > 0
    print(f"  [PASS] Shared volume: {volume['节省比例(%)']:.1f}% saved")


def test_coverage_heatmap():
    """测试覆盖热力图数据生成"""
    data = generate_coverage_heatmap_data(
        site_lon=114.390,
        site_lat=30.506,
        tx_height_m=35.0,
        frequency_mhz=3500,
        tx_power_w=200.0,
        antenna_gain_dbi=24.0,
        radius_km=0.5,
        resolution_m=100,
        rsrp_threshold_dbm=-110,
    )
    assert isinstance(data, list)
    assert len(data) > 0
    assert "rsrp" in data[0]
    assert "distance_km" in data[0]
    print(f"  [PASS] Coverage heatmap: {len(data)} points")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("QGIS 插件设计引擎 — 单元测试")
    print("=" * 50)

    tests = [
        ("Antenna Model", test_antenna_model),
        ("Site Model", test_site_model),
        ("Site Distance", test_site_distance),
        ("Hex Grid", test_hex_grid),
        ("Site Generation", test_generate_sites),
        ("Okumura-Hata", test_okumura_hata),
        ("RSRP Calculation", test_rsrp_calculation),
        ("Coverage Raster", test_coverage_raster),
        ("RSRP Color", test_rsrp_color),
        ("Avoidance Checker", test_avoidance_checker),
        ("Band Configs", test_band_configs),
        ("Save/Load Design", test_save_load_design),
        ("List Designs", test_list_designs),
        ("MachineRoom Model", test_machine_room),
        ("Pipeline Routes", test_pipeline_routes),
        ("Coverage Heatmap", test_coverage_heatmap),
    ]

    passed = 0
    failed = 0
    for name, test_func in tests:
        print(f"\n[TEST] {name}")
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 个测试")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
