# -*- coding: utf-8 -*-
"""cad_export.py 单元测试（纯标准库，可在沙箱运行）

验证：
- DXF 文本结构合法（SECTION/LAYER/ENTITIES/EOF 齐全，含 AC1009）
- 站点/管线/机房/覆盖实体均被正确写入
- DWG 在无转换器时优雅降级（仍产出 DXF，不报错）
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_engine.cad_export import (  # noqa: E402
    entities_to_dxf,
    export_design_to_dxf,
    export_design_to_dwg,
    export_design_to_cad,
    LAYER_SITES, LAYER_PIPELINES, LAYER_ROOMS, LAYER_COVERAGE,
)


def _sample_design():
    return {
        "sites": [
            {"siteId": "S001", "longitude": 111.0, "latitude": 35.0},
            {"siteId": "S002", "longitude": 111.001, "latitude": 35.001},
        ],
        "pipelines": [
            {"pipeline_id": "PL-1", "coordinates": [(111.0, 35.0), (111.001, 35.001)]},
        ],
        "rooms": [
            {"room_id": "ROOM-001", "name": "汇聚机房1",
             "longitude": 111.0005, "latitude": 35.0005, "capacity": 12},
        ],
        "coverage": {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[
                    [111.0, 35.0], [111.002, 35.0],
                    [111.002, 35.002], [111.0, 35.002], [111.0, 35.0],
                ]]},
                "properties": {},
            }],
        },
    }


class TestCadExport(unittest.TestCase):

    def test_entities_to_dxf_structure(self):
        entities = [
            {"type": "point", "layer": LAYER_SITES, "x": 1.0, "y": 2.0},
            {"type": "line", "layer": LAYER_PIPELINES, "x1": 1, "y1": 2, "x2": 3, "y2": 4},
            {"type": "circle", "layer": LAYER_ROOMS, "cx": 1, "cy": 2, "r": 0.001},
            {"type": "text", "layer": LAYER_SITES, "x": 1, "y": 2, "text": "S1"},
        ]
        dxf = entities_to_dxf(entities)
        # 结构关键字
        self.assertIn("AC1009", dxf)
        self.assertIn("SECTION", dxf)
        self.assertIn("LAYER", dxf)
        self.assertIn("ENTITIES", dxf)
        self.assertIn("EOF", dxf)
        # 实体类型
        self.assertIn("\nPOINT\n", dxf)
        self.assertIn("\nLINE\n", dxf)
        self.assertIn("\nCIRCLE\n", dxf)
        self.assertIn("\nTEXT\n", dxf)
        # 图层定义
        for layer in (LAYER_SITES, LAYER_PIPELINES, LAYER_ROOMS, LAYER_COVERAGE):
            self.assertIn(layer, dxf)

    def test_export_design_to_dxf_writes_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "out.dxf")
            written = export_design_to_dxf(_sample_design(), path)
            self.assertTrue(os.path.exists(written))
            with open(written, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("S001", content)      # 站点标注
            self.assertIn("ROOM-001", content)  # 机房标注
            self.assertIn("\nLINE\n", content)  # 管线/覆盖边界

    def test_export_design_to_dwg_graceful_without_converter(self):
        # 沙箱无 DWG 转换器 → 应退化产出 DXF 且不抛异常
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "out.dwg")
            res = export_design_to_dwg(_sample_design(), path)
            self.assertIsNone(res["dwg_path"])
            self.assertFalse(res["dwg_created"])
            self.assertTrue(os.path.exists(res["dxf_path"]))
            self.assertIn("DXF", res["note"])

    def test_export_design_to_cad_dxf(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "plan.dxf")
            res = export_design_to_cad(
                sites=_sample_design()["sites"],
                pipelines=_sample_design()["pipelines"],
                rooms=_sample_design()["rooms"],
                path=path, fmt="dxf",
            )
            self.assertTrue(os.path.exists(res["dxf_path"]))
            self.assertFalse(res["dwg_created"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
