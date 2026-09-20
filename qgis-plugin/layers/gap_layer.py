# -*- coding: utf-8 -*-
"""补盲补热 · 第二档：诊断图层渲染（QGIS 渲染层）。

本模块只做**渲染**，不含任何判定逻辑：
    纯计算的诊断内核在 ``design_engine/gap_diagnosis.py``（无 QGIS 依赖），
    本模块把其产出的 :class:`WeakCell` / :class:`SuggestedSite` 变成 QGIS 内存图层。

对外接口（与《02-架构设计与任务清单》§4.2 逐字对齐）
----------------------------------------------------
* :func:`build_rsrp_weak_layer`  —— 弱覆盖区（每格一个正方形面，按 level 着色）
* :func:`build_suggested_sites_layer` —— 建议补站（点 + demand_score 分级符号 + 标注）
* :func:`remove_gap_layers`      —— 重跑 / 清空时移除上述两个图层

硬约束（勿违反）
----------------
* **禁止**引用 ``ui/design_dock.py`` 的 ``_suggested_sites_layer``（已弃用）。
* **禁止**复用 ``ftth/coverage_gap.py`` 的 ``analyze_coverage_gap`` 判定逻辑。
* 图层 CRS **固定 EPSG:4326**，与 ``generated_sites`` 一致。
* 面几何"米 → 度"换算**必须按该格纬度做 cos 修正**，不得写死常量。
* ``SuggestedSite.needs_review=True`` 的站点**不得静默丢弃**，须可视化区分
  （本模块采用「字段 + 标注『需复核』」的合规方式）。

注意：本机无 QGIS 运行环境，本模块仅做了 ``py_compile`` 与静态自检，
真机显示效果需在 QGIS 内人工验收（见交付清单）。
"""
import math
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning, module="qgis")

from typing import List

# 诊断内核（纯计算，无 QGIS 依赖）。绝对导入为主、相对导入为回退，
# 与 design_engine/gap_diagnosis.py 的导入写法保持一致。
try:
    from design_engine.gap_diagnosis import SuggestedSite, WeakCell
except ImportError:  # pragma: no cover - 作为包内子模块导入时的回退
    from ..design_engine.gap_diagnosis import SuggestedSite, WeakCell


# ───────────────────────────── 模块常量 ─────────────────────────────

# 图层名（与下方 3 个函数默认值必须保持一致；集中定义供 remove_gap_layers 复用）。
_WEAK_LAYER_NAME = "诊断·弱覆盖区"
_SUGGESTED_LAYER_NAME = "诊断·建议补站"

# 弱覆盖分类着色（§4.2：weak=橙 #FFA500，blind=红 #DC143C）。
_WEAK_COLOR = "#FFA500"      # 弱覆盖 —— 橙
_BLIND_COLOR = "#DC143C"     # 盲区   —— 猩红
_FACE_OPACITY = 0.85         # 面不透明度（取 0.85 以便在卫星/热力图底图上可辨）

# 建议补站按 demand_score 分级符号（低 → 高：灰 → 黄 → 红）。
# 上界 100.0 → 100.5：score_cluster 是 round(100×clamp(raw,0,1),1)，**恰好等于 100.0
# 是可达的**；QGIS 分级区间为 [下界, 上界)，100.0 会落在所有区间之外 → 该站点无符号、
# 在地图上凭空消失（"站点看不见"的同一类缺陷）。上界放宽后 [0,100] 全覆盖。
_SCORE_GRADES = (
    # (下界, 上界, 颜色, 图例标签)
    (0.0, 40.0, "#A6A6A6", "低需求"),
    (40.0, 70.0, "#FFD400", "中需求"),
    (70.0, 100.5, "#E53935", "高需求"),
)
# 形状用三角形而非圆形：现有基站也是圆点，同形状在缩小的视野下无法区分
# （用户真机验收时把建议站误当成基站 / 直接没看见）。
_SUGGESTED_MARKER_SHAPE = "triangle"
# 6 → 7：同名义尺寸下三角形面积约为圆的一半，视觉重量会掉；补到 7 才与原圆点相当。
_SUGGESTED_MARKER_SIZE = "7"
# 白描边 → 深灰：#FFFFFF 描边压在橙色弱区（#FFA500）上几乎无对比，等于没描边。
# 深色描边同时解决"黄/红点压在橙面上"与"灰点压在浅底图上"两种情况。
_SUGGESTED_OUTLINE = "#212121"

# 米 → 度换算常量（按纬度做 cos 修正；勿在业务代码里内联魔数）。
_M_PER_DEG_LAT = 110540.0     # 1° 纬度 ≈ 110.54 km
_M_PER_DEG_LON_EQ = 111320.0  # 赤道 1° 经度 ≈ 111.32 km（纬度方向需 ×cos(lat)）
_COS_EPS = 1e-9               # cos(lat) 近零保护阈值


# ───────────────────────────── 内部工具 ─────────────────────────────

def _cell_side_m(cell, default_m: float) -> float:
    """该格建面用边长（米）：**优先用格自带的 cell_m**（= 采样分辨率），
    取不到才回退调用方传入值。

    见 ``gap_diagnosis.WeakCell.cell_m`` 注释「采样栅格边长（米）…用于建面」——
    建面必须用**采样**边长，不能用聚类网格尺寸，否则弱区轮廓会被放大
    （100m 格按 1000m 画 = 单格面积 ×100、四周各外扩 450m）。
    """
    own = getattr(cell, "cell_m", None)
    try:
        own = float(own)
    except (TypeError, ValueError):
        own = 0.0
    if own > 0:
        return own
    return float(default_m)


def _square_ring(lon: float, lat: float, cell_m: float) -> list:
    """以 (lon, lat) 为中心构造边长 cell_m 米的正方形环（4 个角，EPSG:4326）。

    "米 → 度"换算**按该格自身纬度做 cos 修正**：
        * 纬度方向：1° ≈ ``_M_PER_DEG_LAT`` 米（与纬度无关）。
        * 经度方向：1° ≈ ``_M_PER_DEG_LON_EQ × cos(lat)`` 米（高纬处经度 1° 更短，
          故同样米数对应的度数更大）。

    Args:
        lon: 方格中心经度（度）。
        lat: 方格中心纬度（度）。
        cell_m: 方格边长（米，> 0）。

    Returns:
        4 个角点 ``[(x0,y0), (x1,y0), (x1,y1), (x0,y1)]``（未闭合）。
    """
    half = float(cell_m) / 2.0
    cos_lat = math.cos(math.radians(lat))
    dlat = half / _M_PER_DEG_LAT
    # 高纬 / 极点附近 cos→0，退化为与纬度同尺度，避免除零得到 inf。
    dlon = dlat if abs(cos_lat) < _COS_EPS else half / (_M_PER_DEG_LON_EQ * cos_lat)
    x0, x1 = lon - dlon, lon + dlon
    y0, y1 = lat - dlat, lat + dlat
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _ring_to_wkt(ring: list) -> str:
    """把 (未闭合) 环形点列转成闭合的 ``POLYGON((...))`` WKT 字符串。"""
    closed = list(ring) + [ring[0]]  # 显式闭合，规避部分版本的环闭合校验
    pts = ", ".join(f"{x:.9f} {y:.9f}" for x, y in closed)
    return f"POLYGON(({pts}))"


def _remove_layer_by_name(layer_name: str) -> None:
    """按图层名移除项目内所有同名图层（重跑前先调用，避免叠加）。"""
    from qgis.core import QgsProject

    project = QgsProject.instance()
    for layer in project.mapLayersByName(layer_name):
        try:
            project.removeMapLayer(layer.id())
        except Exception as e:  # pragma: no cover - 防御性
            print(f"[WARN] 移除同名图层失败 {layer_name}: {e}")


def _apply_weak_style(layer) -> None:
    """弱覆盖区分类样式：level ∈ {weak, blind} → 橙 / 红，面半透明。"""
    try:
        from qgis.core import (
            QgsFillSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
        )

        # 面符号：实心填充 + 无描边（相邻格拼成连续色块）。
        # 不透明度取 0.85 是为在卫星/热力图底图上可辨；无描边保持不变。
        symbol_weak = QgsFillSymbol.createSimple({"color": _WEAK_COLOR, "outline_style": "no"})
        symbol_weak.setOpacity(_FACE_OPACITY)
        symbol_blind = QgsFillSymbol.createSimple({"color": _BLIND_COLOR, "outline_style": "no"})
        symbol_blind.setOpacity(_FACE_OPACITY)

        categories = [
            QgsRendererCategory("weak", symbol_weak, "弱覆盖"),
            QgsRendererCategory("blind", symbol_blind, "盲区"),
        ]
        renderer = QgsCategorizedSymbolRenderer("level", categories)
        layer.setRenderer(renderer)
    except Exception as e:  # pragma: no cover - 样式失败不阻断出图
        print(f"[WARN] 弱覆盖区样式应用失败: {e}")


def _apply_suggested_style(layer) -> None:
    """建议补站分级样式：按 demand_score 分三级（灰 → 黄 → 红）。

    符号形状为三角形（区别于现有基站的圆点），深色描边以保证压在橙色弱覆盖区上仍可辨。
    """
    try:
        from qgis.core import (
            QgsGraduatedSymbolRenderer, QgsMarkerSymbol, QgsRendererRange,
        )

        ranges = []
        for bottom, top, color, label in _SCORE_GRADES:
            symbol = QgsMarkerSymbol.createSimple({
                "name": _SUGGESTED_MARKER_SHAPE,
                "color": color,
                "size": _SUGGESTED_MARKER_SIZE,
                "outline_color": _SUGGESTED_OUTLINE,
                "outline_width": "1.0",
            })
            ranges.append(QgsRendererRange(bottom, top, symbol, label))

        renderer = QgsGraduatedSymbolRenderer("demand_score", ranges)
        renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
        layer.setRenderer(renderer)
    except Exception as e:  # pragma: no cover - 样式失败不阻断出图
        print(f"[WARN] 建议补站样式应用失败: {e}")


def _enable_suggested_labels(layer) -> None:
    """标注 demand_score；``needs_review=1`` 的站点追加『需复核』文字。

    采用「字段 + 标注」方式满足 §4.2 对 needs_review 的可视化要求，
    不静默忽略该字段。
    """
    try:
        from qgis.core import (
            QgsPalLayerSettings, QgsTextBufferSettings, QgsTextFormat,
            QgsVectorLayerSimpleLabeling,
        )
        from PyQt5.QtGui import QColor, QFont

        # 表达式：常规显示需求评分；需复核站点追加 " 需复核"。
        label_expression = (
            'round("demand_score", 1) || '
            'CASE WHEN "needs_review" = 1 THEN \' 需复核\' ELSE \'\' END'
        )

        settings = QgsPalLayerSettings()
        settings.fieldName = label_expression
        settings.isExpression = True
        settings.enabled = True

        text_format = QgsTextFormat()
        font = QFont()
        font.setPointSize(9)
        text_format.setFont(font)
        text_format.setSize(9)
        text_format.setColor(QColor(40, 40, 40))

        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(1.5)
        buffer_settings.setColor(QColor(255, 255, 255, 200))
        text_format.setBuffer(buffer_settings)

        settings.setFormat(text_format)

        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
    except Exception as e:  # pragma: no cover - 标注失败不阻断图层
        print(f"[WARN] 建议补站标注设置失败: {e}")


# ───────────────────────────── 对外接口 ─────────────────────────────

def build_rsrp_weak_layer(
    weak_cells: List[WeakCell],
    cell_m: float,
    layer_name: str = "诊断·弱覆盖区",
    crs: str = "EPSG:4326",
):
    """弱覆盖区图层：每格一个正方形面，按 level 分类着色
    （weak=橙 #FFA500，blind=红 #DC143C），半透明。已存在同名图层先移除。返回 QgsVectorLayer。

    Args:
        weak_cells: 诊断内核产出的弱覆盖/盲区栅格列表（读 lon/lat/rsrp/level）。
        cell_m: **兜底**边长（米）；正常情况下每格用其自带的 ``cell_m``（采样分辨率），
            仅在格缺该字段/非正时回退为此值，用于把每格渲染为边长 cell_m 的正方形面。
        layer_name: 图层名称（默认「诊断·弱覆盖区」）。
        crs: 目标坐标系（固定 EPSG:4326，与 generated_sites 一致）。

    Returns:
        QgsVectorLayer（已加入当前项目）；非 QGIS 环境返回 None。

    Raises:
        ValueError: ``weak_cells`` 非空且 ``cell_m`` 非正时（无法建面）。
    """
    try:
        from qgis.core import (
            QgsFeature, QgsField, QgsGeometry, QgsProject, QgsVectorLayer,
        )
        from PyQt5.QtCore import QVariant

        if weak_cells and float(cell_m) <= 0:
            raise ValueError(f"cell_m 必须为正才能建面，当前={cell_m}")

        # 先移除同名旧图层，避免重跑叠加。
        _remove_layer_by_name(layer_name)

        layer = QgsVectorLayer(f"Polygon?crs={crs}", layer_name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("level", QVariant.String),
            QgsField("rsrp", QVariant.Double),
        ])
        layer.updateFields()

        features = []
        for cell in weak_cells:
            ring = _square_ring(float(cell.lon), float(cell.lat),
                                _cell_side_m(cell, cell_m))
            geom = QgsGeometry.fromWkt(_ring_to_wkt(ring))
            if geom is None or geom.isEmpty():
                continue
            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom)
            feat.setAttributes([cell.level, float(cell.rsrp)])
            features.append(feat)

        if features:
            provider.addFeatures(features)
        layer.updateExtents()

        _apply_weak_style(layer)

        QgsProject.instance().addMapLayer(layer)
        return layer

    except ImportError:
        print("[INFO] 非QGIS环境，跳过弱覆盖区图层创建")
        return None


def build_suggested_sites_layer(
    suggested: List[SuggestedSite],
    layer_name: str = "诊断·建议补站",
    crs: str = "EPSG:4326",
):
    """建议补站图层：点几何 + 字段
    id/lon/lat/demand_score/radius_km/tech/cell_count/blind_count；
    符号按 demand_score 分级（低→高：灰→黄→红），标注 demand_score。返回 QgsVectorLayer。

    另附 ``needs_review`` / ``review_note`` 字段：需复核站点在标注中追加
    「需复核」，不静默丢弃（见 :func:`_enable_suggested_labels`）。

    Args:
        suggested: 诊断内核产出的建议站列表。
        layer_name: 图层名称（默认「诊断·建议补站」）。
        crs: 目标坐标系（固定 EPSG:4326）。

    Returns:
        QgsVectorLayer（已加入当前项目）；非 QGIS 环境返回 None。
    """
    try:
        from qgis.core import (
            QgsFeature, QgsField, QgsGeometry, QgsProject, QgsVectorLayer,
        )
        from PyQt5.QtCore import QVariant

        # 先移除同名旧图层，避免重跑叠加。
        _remove_layer_by_name(layer_name)

        layer = QgsVectorLayer(f"Point?crs={crs}", layer_name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("id", QVariant.String),
            QgsField("lon", QVariant.Double),
            QgsField("lat", QVariant.Double),
            QgsField("demand_score", QVariant.Double),
            QgsField("radius_km", QVariant.Double),
            QgsField("tech", QVariant.String),
            QgsField("cell_count", QVariant.Int),
            QgsField("blind_count", QVariant.Int),
            QgsField("needs_review", QVariant.Int),
            QgsField("review_note", QVariant.String),
        ])
        layer.updateFields()

        features = []
        for site in suggested:
            lon = float(site.longitude)
            lat = float(site.latitude)
            geom = QgsGeometry.fromWkt(f"POINT({lon} {lat})")
            if geom is None or geom.isEmpty():
                continue
            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom)
            feat.setAttributes([
                site.suggest_id,
                lon,
                lat,
                float(site.demand_score),
                float(site.suggested_radius_km),
                site.tech,
                int(site.cell_count),
                int(site.blind_count),
                1 if getattr(site, "needs_review", False) else 0,
                getattr(site, "review_note", "") or "",
            ])
            features.append(feat)

        if features:
            provider.addFeatures(features)
        layer.updateExtents()

        _apply_suggested_style(layer)
        _enable_suggested_labels(layer)

        QgsProject.instance().addMapLayer(layer)
        return layer

    except ImportError:
        print("[INFO] 非QGIS环境，跳过建议补站图层创建")
        return None


def remove_gap_layers() -> None:
    """移除「诊断·弱覆盖区」「诊断·建议补站」两个图层（重跑/清空时先调用）。"""
    try:
        from qgis.core import QgsProject  # noqa: F401 - 触发 ImportError 判定
    except ImportError:
        print("[INFO] 非QGIS环境，跳过诊断图层移除")
        return

    for name in (_WEAK_LAYER_NAME, _SUGGESTED_LAYER_NAME):
        _remove_layer_by_name(name)
