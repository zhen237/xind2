# -*- coding: utf-8 -*-
"""topology.py 单元测试（T5 验收支撑）

无需 QGIS / 第三方库，纯标准库即可运行：
    python qgis-plugin/design_engine/tests/test_topology.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from design_engine.topology import (  # noqa: E402
    design_star,
    design_tree,
    design_redundant,
    design_topology,
    route_topology_edges,
)


def _sites(n=5, step=0.001):
    return [{"id": "SITE-%d" % (i + 1), "lon": i * step, "lat": 0.0} for i in range(n)]


def _hub():
    return {"id": "ROOM-001", "lon": -0.001, "lat": 0.0}


def test_star():
    sites = _sites(5)
    r = design_star(sites, _hub())
    assert r["topology_type"] == "star"
    assert len(r["edges"]) == 5
    assert all(e["kind"] == "access" and e["to"] == "ROOM-001" for e in r["edges"])
    assert len(r["nodes"]) == 6  # 5 sites + hub


def test_tree_subhubs():
    sites = _sites(10)
    r = design_tree(sites, _hub())
    assert r["topology_type"] == "tree"
    subhubs = [n for n in r["nodes"] if n["kind"] == "subhub"]
    assert len(subhubs) >= 1
    # 每个 subhub 有回传边到 hub
    backhaul = [e for e in r["edges"] if e["kind"] == "backhaul"]
    assert len(backhaul) == len(subhubs)
    assert all(e["to"] == "ROOM-001" for e in backhaul)
    # 非种子站点有接入边
    access = [e for e in r["edges"] if e["kind"] == "access"]
    assert len(access) >= 1
    # 无自环边
    assert all(e["from"] != e["to"] for e in r["edges"])


def test_redundant_ring():
    sites = _sites(5)
    r = design_redundant(sites, _hub())
    assert r["topology_type"] == "redundant"
    access = [e for e in r["edges"] if e["kind"] == "access"]
    ring = [e for e in r["edges"] if e["kind"] == "ring"]
    assert len(access) == 5
    assert len(ring) == 5  # 站点间成环
    # 冗余：每个站点至少 2 条出/入边
    degree = {}
    for e in r["edges"]:
        degree[e["from"]] = degree.get(e["from"], 0) + 1
        degree[e["to"]] = degree.get(e["to"], 0) + 1
    site_ids = {s["id"] for s in sites}
    assert all(degree[sid] >= 2 for sid in site_ids)


def test_dispatcher():
    sites = _sites(4)
    assert design_topology(sites, _hub(), "star")["topology_type"] == "star"
    assert design_topology(sites, _hub(), "tree")["topology_type"] == "tree"
    assert design_topology(sites, _hub(), "redundant")["topology_type"] == "redundant"
    # 默认 star
    assert design_topology(sites, _hub())["topology_type"] == "star"


def test_route_topology_no_road():
    sites = _sites(3)
    r = design_star(sites, _hub())
    out = route_topology_edges(r, None)
    for e in out["edges"]:
        assert "coordinates" in e and "distance_m" in e
        assert e["coordinates"] == [e["from"], e["to"]] or len(e["coordinates"]) == 2


def test_route_topology_with_road():
    # 构造一条横贯道路，验证边获得路网坐标
    nodes, segs = [], []
    for i in range(6):
        nodes.append((i * 0.001, 0.0))
    for i in range(5):
        segs.append([nodes[i], nodes[i + 1]])
    sites = [{"id": "SITE-%d" % (i + 1), "lon": i * 0.001, "lat": 0.0} for i in range(6)]
    r = design_star(sites, {"id": "ROOM-001", "lon": -0.001, "lat": 0.0})
    out = route_topology_edges(r, segs, algorithm="dijkstra")
    for e in out["edges"]:
        assert e["found"] if "found" in e else True
        assert isinstance(e["coordinates"], list) and len(e["coordinates"]) >= 2
        assert e["distance_m"] > 0


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print("  ✓ %s" % t.__name__)
            passed += 1
        except AssertionError as e:
            print("  ✗ %s: %s" % (t.__name__, e))
        except Exception as e:  # noqa: BLE001
            print("  ✗ %s 异常: %s" % (t.__name__, e))
    print("\n通过 %d/%d" % (passed, len(tests)))
    return passed == len(tests)


if __name__ == "__main__":
    ok = _run_all()
    sys.exit(0 if ok else 1)
