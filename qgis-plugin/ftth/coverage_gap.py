# -*- coding: utf-8 -*-
"""
覆盖缺口识别 + 智能站点建议 (S1 增强：真实数据 → 设计输入)
==============================================================

把"真实 FTTH 现网"变成"智能辅助设计"的输入：
  ① 合并 ZNRO(OLT覆盖范围) + ZPM(PM/SRO范围) 覆盖区面
  ② 判断每个 IMB(楼栋点) 是否落在覆盖区内
  ③ 落在覆盖区外的楼栋 = 覆盖缺口
  ④ 对缺口楼栋按地理网格聚类，每格生成一个"建议新增 NRO 站点"候选点
     （位置取簇质心，容量=簇内楼栋住户数之和）

这就是把 S1 从"空白画布从零设计"升级为"基于真实现网的智能增量设计"的关键一环：
系统读出真实网络的盲区，辅助设计人员决定"在哪补站"。
"""
from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
    QgsField,
    QgsFeature,
    QgsVectorLayer,
    QgsProject,
)
from qgis.PyQt.QtCore import QVariant


def _live_layers(layers: dict) -> dict:
    """返回仍存活于 QgsProject 中的层，剔除已被用户删除的层。

    用户在 QGIS 图层面板手动删除图层后，缓存的 QgsVectorLayer 引用会变成
    “wrapped C/C++ object has been deleted”，直接调用 getFeatures() 会抛
    RuntimeError。这里统一用 layer.id() 去工程重新取活对象；取不到（已删除）
    或损坏的引用一律跳过，避免下游崩溃。
    """
    proj = QgsProject.instance()
    live = {}
    for name, lyr in (layers or {}).items():
        if lyr is None:
            continue
        try:
            lid = lyr.id()
        except RuntimeError:
            # C++ 对象已被销毁，引用失效
            continue
        cur = proj.mapLayer(lid)
        if cur is not None:
            live[name] = cur
        # cur is None → 层已从工程移除，跳过
    return live


def _coverage_geometry(layers: dict):
    """合并 ZNRO + ZPM 覆盖区面为单一几何（用于 contains 判断）。"""
    geoms = []
    for name in ("ZNRO", "ZPM"):
        lyr = layers.get(name)
        if lyr is None:
            continue
        for feat in lyr.getFeatures():
            g = feat.geometry()
            if g is not None and not g.isEmpty():
                geoms.append(QgsGeometry(g.constGet().clone()))
    if not geoms:
        return None
    if len(geoms) == 1:
        return geoms[0]
    return QgsGeometry.unaryUnion(geoms)


def _to_int(v) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


def analyze_coverage_gap(layers: dict, weights: dict = None) -> dict:
    """分析 IMB 楼栋相对覆盖区(ZNRO/ZPM)的覆盖缺口。

    weights: 需求评分权重 {w1:缺口楼栋, w2:投诉密度, w3:路测弱覆盖}，
             默认 {0.5, 0.3, 0.2}。仅当 layers 含 COMPLAINT/ROADTEST 时生效。

    返回结构化结果，供 UI 展示与建议站点生成：
      has_coverage : 是否存在覆盖区面
      total_imb    : 楼栋总数
      covered      : 已覆盖楼栋数
      gap          : 缺口楼栋数
      gap_features : [(lon, lat, nb_loc_tot, code), ...]
      suggested_sites : [{lon, lat, imb_cnt, capacity, demand_score,
                          complaint_cnt, roadtest_area_frac}, ...]
    """
    result = {
        "has_coverage": False,
        "total_imb": 0,
        "covered": 0,
        "gap": 0,
        "gap_features": [],
        "suggested_sites": [],
    }
    # 关键：只保留仍存活于工程中的层，剔除已被用户删除的层引用
    layers = _live_layers(layers)
    imb = layers.get("IMB")
    if imb is None:
        return result

    coverage = _coverage_geometry(layers)
    result["has_coverage"] = coverage is not None
    result["total_imb"] = imb.featureCount()

    for feat in imb.getFeatures():
        g = feat.geometry()
        if g is None or g.isEmpty():
            continue
        pt = g.asPoint()
        lon, lat = pt.x(), pt.y()
        nb = _to_int(feat["NB_LOC_TOT"])
        code = str(feat["CODE"] or "")
        covered = False
        if coverage is not None:
            # 用 WKT 构造点几何，绕开部分 QGIS 版本 QgsPointXY SIP 构造问题
            covered = coverage.contains(QgsGeometry.fromWkt(f"POINT({lon} {lat})"))
        if covered:
            result["covered"] += 1
        else:
            result["gap"] += 1
            result["gap_features"].append((lon, lat, nb, code))

    result["suggested_sites"] = _cluster_gap_sites(result["gap_features"], layers, weights)
    return result


def _read_points(layer):
    """读取点图层所有点坐标 (x, y) 列表（容错：非点/空几何跳过）。"""
    pts = []
    if layer is None:
        return pts
    for f in layer.getFeatures():
        g = f.geometry()
        if g is None or g.isEmpty():
            continue
        try:
            p = g.asPoint()
            pts.append((p.x(), p.y()))
        except Exception:
            pass
    return pts


def _read_polys(layer):
    """读取面图层所有面几何（克隆，避免 C++ 对象失效）。"""
    polys = []
    if layer is None:
        return polys
    for f in layer.getFeatures():
        g = f.geometry()
        if g is None or g.isEmpty():
            continue
        try:
            polys.append(QgsGeometry(g.constGet().clone()))
        except Exception:
            pass
    return polys


def _cluster_gap_sites(gap_features: list, layers: dict = None,
                       weights: dict = None, cell_m: float = 400.0) -> list:
    """将缺口楼栋按地理网格(约 cell_m 一格)聚类，每格一个建议站点。

    增强（S1 #1）：若 layers 含 COMPLAINT(投诉点)/ROADTEST(路测弱覆盖面)，
    则对每个簇计算『需求评分』并按加权需求方向偏移质心：
        demand_score = 缺口楼栋数×w1 + 簇内投诉点数×w2 + 路测弱覆盖占比×w3
    无投诉/路测数据时退化为纯几何质心（与旧行为一致，零破坏）。
    """
    if weights is None:
        weights = {"w1": 0.5, "w2": 0.3, "w3": 0.2}
    w1 = float(weights.get("w1", 0.5))
    w2 = float(weights.get("w2", 0.3))
    w3 = float(weights.get("w3", 0.2))

    if not gap_features:
        return []
    cell_deg = cell_m / 111320.0
    clusters = {}
    for lon, lat, nb, code in gap_features:
        key = (round(lon / cell_deg), round(lat / cell_deg))
        c = clusters.setdefault(key, {"lon": 0.0, "lat": 0.0, "n": 0, "cap": 0, "imb": 0})
        c["lon"] += lon
        c["lat"] += lat
        c["n"] += 1
        c["cap"] += max(0, nb)
        c["imb"] += 1

    # 一次性读取投诉点 / 路测弱覆盖面（与 IMB 同一坐标系，直接按坐标比较）
    complaint_pts = _read_points(layers.get("COMPLAINT") if layers else None)
    roadtest_polys = _read_polys(layers.get("ROADTEST") if layers else None)
    has_feedback = bool(complaint_pts) or bool(roadtest_polys)

    sites = []
    for key, c in clusters.items():
        geo_cx = c["lon"] / c["n"]
        geo_cy = c["lat"] / c["n"]

        # 簇对应网格单元（用于判断投诉点落入 & 路测面交叠）
        x0 = key[0] * cell_deg
        y0 = key[1] * cell_deg
        x1 = x0 + cell_deg
        y1 = y0 + cell_deg
        cell_area = abs((x1 - x0) * (y1 - y0)) or 1e-12
        cell_poly = QgsGeometry.fromPolygonXY([
            QgsPointXY(x0, y0), QgsPointXY(x1, y0),
            QgsPointXY(x1, y1), QgsPointXY(x0, y1), QgsPointXY(x0, y0),
        ])

        # 簇内投诉点数 + 投诉点平均位置
        ccnt = 0
        dlon = 0.0
        dlat = 0.0
        for px, py in complaint_pts:
            if x0 <= px < x1 and y0 <= py < y1:
                ccnt += 1
                dlon += px
                dlat += py

        # 簇内路测弱覆盖交叠面积（占单元比，封顶避免爆量）
        r_area = 0.0
        r_wcx = 0.0
        r_wcy = 0.0
        r_n = 0
        if roadtest_polys:
            for rg in roadtest_polys:
                try:
                    inter = cell_poly.intersection(rg)
                    if inter is not None and not inter.isEmpty():
                        a = inter.area()
                        if a > 0:
                            r_area += a
                            cen = inter.centroid()
                            if cen is not None and not cen.isEmpty():
                                r_wcx += cen.x() * a
                                r_wcy += cen.y() * a
                                r_n += 1
                except Exception:
                    pass
        r_frac = min(r_area / cell_area, 5.0)

        demand_score = c["imb"] * w1 + ccnt * w2 + r_frac * w3

        # 质心按加权需求方向偏移（投诉/弱覆盖越密，拉得越狠，封顶 0.6）
        if has_feedback and (ccnt > 0 or r_n > 0):
            wx = 0.0
            wy = 0.0
            wt = 0.0
            if ccnt > 0:
                wx += dlon
                wy += dlat
                wt += ccnt
            if r_n > 0:
                wx += r_wcx
                wy += r_wcy
                wt += r_n
            dem_cx = wx / wt
            dem_cy = wy / wt
            alpha = min(0.6, (ccnt + r_n) * 0.08)
            fx = geo_cx * (1 - alpha) + dem_cx * alpha
            fy = geo_cy * (1 - alpha) + dem_cy * alpha
        else:
            fx, fy = geo_cx, geo_cy

        sites.append({
            "lon": round(fx, 6),
            "lat": round(fy, 6),
            "imb_cnt": c["imb"],
            "capacity": c["cap"],
            "demand_score": round(demand_score, 3),
            "complaint_cnt": ccnt,
            "roadtest_area_frac": round(r_frac, 3),
        })
    return sites


def build_suggested_sites_layer(result: dict, name: str = "S1-建议站点(NRO候选)",
                                 crs: str = "EPSG:4326", transform=None):
    """将建议站点生成为内存点图层并加进工程。

    Args:
        result: analyze_coverage_gap 的返回
        name:   图层名
        crs:    图层 CRS(authid 字符串)。默认 EPSG:4326。
                关键：必须与实际显示坐标系一致。若 FTTH 数据 .prj 虽标 4326 但坐标
                实为投影网格(如 extent 出现 ±90 之外的纬度)，应传入画布真实 CRS，
                否则 4326 图层在异源画布上会被重投影到错误位置 → 标记不显示。
        transform: 可选 QgsCoordinateTransform，在写入前把 (lon,lat) 从源 CRS
                   变换到 crs。传 None 则原样写入(假设源坐标已在 crs 下)。
    """
    layer = QgsVectorLayer(f"Point?crs={crs}", name, "memory")
    pr = layer.dataProvider()
    pr.addAttributes([
        QgsField("id", QVariant.Int),
        QgsField("lon", QVariant.Double),
        QgsField("lat", QVariant.Double),
        QgsField("imb_cnt", QVariant.Int),
        QgsField("capacity", QVariant.Int),
        QgsField("demand_score", QVariant.Double),
        QgsField("complaint_cnt", QVariant.Int),
    ])
    layer.updateFields()
    feats = []
    for i, s in enumerate(result.get("suggested_sites", []), 1):
        x, y = s["lon"], s["lat"]
        if transform is not None:
            try:
                pt = transform.transform(x, y)
                x, y = pt.x(), pt.y()
            except Exception:
                pass  # 变换失败则保留原坐标
        f = QgsFeature()
        # 用 WKT 构造点，绕开部分 QGIS 版本 QgsPointXY SIP 构造问题
        geom = QgsGeometry.fromWkt(f"POINT({x} {y})")
        if geom is None or geom.isEmpty():
            continue
        f.setGeometry(geom)
        f.setAttributes([i, x, y, s["imb_cnt"], s["capacity"],
                         s.get("demand_score", 0.0), s.get("complaint_cnt", 0)])
        feats.append(f)
    pr.addFeatures(feats)
    layer.updateExtents()
    return layer
