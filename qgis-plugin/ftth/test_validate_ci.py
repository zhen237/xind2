# -*- coding: utf-8 -*-
"""
FTTH 校验离线回归测试 (CI 友好，零第三方依赖)
============================================
- 不依赖 qgis / pyshp / dbfread：直接构造 FtthProject + add_records 合成数据。
- validate_project(project) 不传 shape_dir -> 跳过几何检查(_check_geometry skip)。
- 聚焦验证:
    1) 合法网络零异常 (anomalies 各层为空, 占位标记已过滤)
    2) 孤立箱 / 幽灵缆端点 正确归层到 BOITE / SITE / CABLE
    3) 5.4 修正回归: 仅经非配线缆(TRANSPORT)连接的节点不应误报高亮

运行:
    cd qgis-plugin
    python -m pytest ftth/test_validate_ci.py -q      # CI
    python ftth/test_validate_ci.py                    # 无 pytest 时直跑
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)  # qgis-plugin/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ftth.model import FtthProject
from ftth.validate import validate_project


def _clean_project() -> FtthProject:
    """8 层最小占位 + 合法拓扑，使 5.1/5.2/5.3/5.4 全部 pass（零异常基线）。

    关键: PM1 作为一条 DISTRIBUTION 缆端点被覆盖，避免 5.4 把 PM 站点误判为孤儿
    (真实竣工数据里 PM 通常不是缆端点，属 5.4 既有灰色行为，本地实测时复核)。
    """
    p = FtthProject()
    rows = {
        "ZNRO": [{"CODE": "ZR1"}],
        "ZPM": [{"CODE": "ZPM1"}],
        "SITE": [{"CODE": "ZPM1", "TYPE": "PM", "REF_ZPM": "ZPM1"}],
        "BOITE": [{"CODE": "B1", "TYPE": "PBO", "REF_PM": "ZPM1"}],
        "CABLE": [{"CODE": "C1", "TYPE_CABLE": "DISTRIBUTION", "REF_PM": "ZPM1",
                   "ORIGINE": "ZPM1", "EXTREMITE": "B1", "REF_PBO": "B1"}],
        "IMB": [{"CODE": "I1"}],
        "PTECH": [{"CODE": "P1"}],
        "INFRASTRUCTURE": [{"CODE": "F1"}],
    }
    for layer, data in rows.items():
        p.add_records(layer, data)
    return p


def test_clean_network_zero_anomalies():
    """合法网络应零异常（所有层 anomalies 为空）。"""
    anomalies = validate_project(_clean_project())["anomalies"]
    assert all(len(codes) == 0 for codes in anomalies.values()), anomalies
    for codes in anomalies.values():
        for c in codes:
            assert not c.startswith("__")


def test_orphan_and_ghost_grouping():
    """孤立箱 + 幽灵缆端点应正确归层到 BOITE / SITE / CABLE。"""
    p = _clean_project()
    # 完全孤立箱(无 REF_PM，不连任何缆)
    p.add_records("BOITE", [{"CODE": "GHOST_BOX", "TYPE": "PBO"}])
    # 配线缆端点指向不存在节点 NOPE -> 幽灵引用
    p.add_records("CABLE", [{"CODE": "CAB_G", "TYPE_CABLE": "DISTRIBUTION",
                             "REF_PM": "ZPM1", "ORIGINE": "B1", "EXTREMITE": "NOPE"}])
    anomalies = validate_project(p)["anomalies"]
    assert "GHOST_BOX" in anomalies.get("BOITE", [])
    assert "GHOST_BOX" in anomalies.get("SITE", [])
    assert "CAB_G" in anomalies.get("CABLE", [])
    assert "NOPE" in anomalies.get("BOITE", [])
    assert "NOPE" in anomalies.get("SITE", [])
    # 正常要素不应出现
    assert "B1" not in anomalies.get("BOITE", [])
    assert "C1" not in anomalies.get("CABLE", [])
    for codes in anomalies.values():
        for c in codes:
            assert not c.startswith("__")


def test_54_non_distribution_not_flagged():
    """5.4 修正回归: 仅经非配线缆(TRANSPORT)连接的节点不应误报高亮。"""
    p = _clean_project()
    # PBO3 合法归属 PM，但只被一条 TRANSPORT 缆连接（规范范围外连接）
    p.add_records("BOITE", [{"CODE": "PBO3", "TYPE": "PBO", "REF_PM": "ZPM1"}])
    p.add_records("CABLE", [{"CODE": "CAB_T", "TYPE_CABLE": "TRANSPORT",
                             "REF_PM": "ZPM1", "ORIGINE": "B1", "EXTREMITE": "PBO3"}])
    anomalies = validate_project(p)["anomalies"]
    # 核心断言: PBO3 不因"经非配线缆连接"被误报
    assert "PBO3" not in anomalies.get("BOITE", []), anomalies
    assert "PBO3" not in anomalies.get("SITE", []), anomalies
    # 整个网络除基线外无真实异常
    assert all(len(codes) == 0 for codes in anomalies.values()), anomalies


if __name__ == "__main__":
    import traceback
    funcs = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
