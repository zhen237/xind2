"""生成试运行样例数据（对应需求 R-4：样例 CAD/GeoJSON 由 AI 生成）

产出：
  samples/yuncheng_site.dxf         —— 通信工程样例图纸（CGCS2000 3度带 GK CM 111E）
  samples/gis/well_point.geojson    —— GIS 基准：管井（含 1 个与 CAD 同名同位置的井）
  samples/gis/building_outline.geojson —— GIS 基准：建筑（含 1 个同名属性冲突）

坐标系：CGCS2000 / 3-degree Gauss-Kruger CM 111E（运城区域）
坐标范围：x 500000~502000 m, y 3876000~3878000 m
运行：python samples/make_samples.py
"""

import os
import sys

import ezdxf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cad_engine.transformer import CoordinateTransformer  # noqa: E402
from cad_engine.geojson_writer import write_layer_geojson  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DXF_PATH = os.path.join(HERE, "yuncheng_site.dxf")
GIS_DIR = os.path.join(HERE, "gis")

# 关键控制点（GK 米）——GIS 基准数据生成用
WELL3_GK = (501200.0, 3876680.0)          # 与 CAD 3号井完全同位置 → 去重
BUILDING_A_CAD_RIGHT = 500940.0           # CAD 机房A 右边缘
BUILDING_A_GIS_CENTER = (500985.0, 3877010.0)  # 距 CAD 机房A 约 45m → 属性冲突


def build_dxf():
    doc = ezdxf.new("R2010", setup=False)
    doc.header["$INSUNITS"] = 6  # meters
    msp = doc.modelspace()

    layers = ["JZW-建筑轮廓", "DL-道路中心线", "DLX-10kV", "DLX-110kV",
              "GJ-管井", "DGX-等高线", "HX-红线", "标注"]
    for name in layers:
        doc.layers.add(name)

    # ---------- 建筑轮廓（Polygon ×3）----------
    buildings = [
        # (角点列表, 楼层标注文本, 文本位置)
        ([(500880, 3876980), (500940, 3876980), (500940, 3877040),
          (500880, 3877040)], "机房A", (500900, 3877012)),
        ([(501300, 3877100), (501380, 3877100), (501380, 3877160),
          (501300, 3877160)], "机房B", (501320, 3877132)),
        ([(500400, 3877400), (500450, 3877400), (500450, 3877440),
          (500400, 3877440)], None, None),
    ]
    for pts, label, tpos in buildings:
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "JZW-建筑轮廓"})
        if label:
            msp.add_text(label, dxfattribs={"layer": "JZW-建筑轮廓",
                                            "insert": tpos, "height": 3.0})

    # ---------- 道路中心线（LineString ×2）----------
    msp.add_lwpolyline([(500000, 3876500), (500800, 3876550), (501500, 3876600),
                        (502000, 3876650)], dxfattribs={"layer": "DL-道路中心线"})
    msp.add_lwpolyline([(500300, 3876000), (500350, 3876800), (500380, 3877800)],
                       dxfattribs={"layer": "DL-道路中心线"})

    # ---------- 电力线路（LineString ×2，电压等级在图层名）----------
    msp.add_lwpolyline([(500000, 3877700), (500700, 3877650), (501400, 3877700)],
                       dxfattribs={"layer": "DLX-110kV"})
    msp.add_lwpolyline([(500200, 3876200), (500900, 3876250), (501800, 3876300)],
                       dxfattribs={"layer": "DLX-10kV"})

    # ---------- 管井（Point ×5 + 文本标注）----------
    wells = [
        ((500600, 3876600), "1号井"),
        ((500900, 3876650), "2号井"),
        ((501200, 3876680), "3号井"),
        ((501500, 3876710), "4号井"),
        ((501800, 3876740), "5号井"),
    ]
    for (x, y), name in wells:
        msp.add_point((x, y), dxfattribs={"layer": "GJ-管井"})
        msp.add_text(name, dxfattribs={"layer": "GJ-管井",
                                       "insert": (x + 1.0, y + 1.0), "height": 2.0})

    # ---------- 等高线（LineString + 高程 ×3）----------
    contours = [
        (780.0, [(500000, 3876300), (500600, 3876330), (501200, 3876360),
                 (501800, 3876390)]),
        (790.0, [(500000, 3876900), (500600, 3876935), (501200, 3876970),
                 (501800, 3877005)]),
        (800.0, [(500000, 3877500), (500600, 3877540), (501200, 3877580),
                 (501800, 3877620)]),
    ]
    for elev, pts in contours:
        pl = msp.add_lwpolyline(pts, dxfattribs={"layer": "DGX-等高线"})
        pl.dxf.elevation = elev  # 组码 38

    # ---------- 红线（Polygon ×1，闭合）----------
    msp.add_lwpolyline([(500100, 3876400), (501900, 3876400), (501900, 3877800),
                        (500100, 3877800)], close=True,
                       dxfattribs={"layer": "HX-红线"})

    # ---------- 未匹配图层（验证 unmatched 处理）----------
    msp.add_text("项目名称：运城通信枢纽配套工程",
                 dxfattribs={"layer": "标注", "insert": (500200, 3877900),
                            "height": 5.0})

    doc.saveas(DXF_PATH)
    print(f"样例 DXF 已生成: {DXF_PATH}")
    return DXF_PATH


def gk_to_wgs84(points):
    t = CoordinateTransformer(source="cgcs2000_gk111", target="EPSG:4326")
    return [t.transform_point(x, y) for (x, y) in points]


def build_gis_baseline():
    """GIS 基准数据（WGS84），包含验证融合规则的场景。"""
    os.makedirs(GIS_DIR, exist_ok=True)

    # 管井：GIS 已有 1号井（与 CAD 同位置同名 → CAD 侧去重）+ 6号井（CAD 没有 → 新增保留）
    well_pts = gk_to_wgs84([WELL3_GK, (501950.0, 3876770.0)])
    wells = [
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [round(well_pts[0][0], 8),
                                                       round(well_pts[0][1], 8)]},
         "properties": {"label": "3号井", "well_type": "通信管道井", "source": "GIS"}},
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [round(well_pts[1][0], 8),
                                                       round(well_pts[1][1], 8)]},
         "properties": {"label": "6号井", "well_type": "通信管道井", "source": "GIS"}},
    ]
    write_layer_geojson(os.path.join(GIS_DIR, "well_point.geojson"), wells,
                        "EPSG:4326", "EPSG:4326")

    # 建筑：GIS 已有“机房A”（距 CAD 机房A 约 20m，楼层 5 vs CAD 默认 1 → 属性冲突）
    b_pts = gk_to_wgs84([BUILDING_A_GIS_CENTER])
    bx, by = b_pts[0]
    dx, dy = 0.00018, 0.00015  # ~20m/13m 的经纬度差 → 约 20×30m 建筑
    building = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[
            [round(bx - dx, 8), round(by - dy, 8)],
            [round(bx + dx, 8), round(by - dy, 8)],
            [round(bx + dx, 8), round(by + dy, 8)],
            [round(bx - dx, 8), round(by + dy, 8)],
            [round(bx - dx, 8), round(by - dy, 8)],
        ]]},
        "properties": {"label": "机房A", "floors": 5, "usage": "通信机房",
                       "source": "GIS"},
    }
    write_layer_geojson(os.path.join(GIS_DIR, "building_outline.geojson"),
                        [building], "EPSG:4326", "EPSG:4326")
    print(f"GIS 基准数据已生成: {GIS_DIR}")


if __name__ == "__main__":
    build_dxf()
    build_gis_baseline()
