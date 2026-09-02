"""DXF 实体解析（ezdxf）—— FR-1 / FR-2

将 DXF 模型空间实体解析为统一的中间表示：
  {type, layer, points, closed, elevation, text, handle}
points 为 [(x, y), ...] 平面坐标（米，源坐标系）。
支持：LWPOLYLINE / POLYLINE / LINE / CIRCLE / ARC / POINT / TEXT / MTEXT / INSERT。
"""

import math

import ezdxf
from ezdxf import recover

# 圆/弧离散化的角度步长（度）
ARC_STEP_DEG = 10.0


def _pts_from_lwpolyline(entity):
    return [(p[0], p[1]) for p in entity.get_points("xy")]


def _pts_from_polyline(entity):
    return [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]


def _discretize_arc(cx, cy, r, start_deg, end_deg):
    """把圆弧按固定角度步长离散为折线点（闭合圆：start=0,end=360）。"""
    if end_deg < start_deg:
        end_deg += 360.0
    pts = []
    steps = max(int(math.ceil((end_deg - start_deg) / ARC_STEP_DEG)), 2)
    for i in range(steps + 1):
        a = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _entity_elevation(entity):
    """取实体高程（组码 38 / Z 值），用于等高线。"""
    try:
        if entity.dxftype() == "LWPOLYLINE":
            return float(entity.dxf.get("elevation", 0) or 0)
        if entity.dxftype() in ("LINE",):
            return float(entity.dxf.start.z)
        if entity.dxftype() in ("POLYLINE",):
            return float(entity.dxf.get("elevation", 0) or 0)
    except Exception:
        pass
    return 0.0


def _parse_entity(entity, out):
    etype = entity.dxftype()
    layer = str(entity.dxf.layer)
    handle = entity.dxf.handle
    common = {"layer": layer, "handle": handle, "elevation": _entity_elevation(entity)}

    if etype == "LWPOLYLINE":
        pts = _pts_from_lwpolyline(entity)
        if len(pts) >= 2:
            out.append(dict(common, type="polyline", points=pts,
                            closed=bool(entity.closed), text=None))
    elif etype == "POLYLINE":
        pts = _pts_from_polyline(entity)
        if len(pts) >= 2:
            out.append(dict(common, type="polyline", points=pts,
                            closed=bool(entity.is_closed), text=None))
    elif etype == "LINE":
        s, e = entity.dxf.start, entity.dxf.end
        out.append(dict(common, type="polyline",
                        points=[(s.x, s.y), (e.x, e.y)],
                        closed=False, text=None))
    elif etype == "CIRCLE":
        c = entity.dxf.center
        pts = _discretize_arc(c.x, c.y, entity.dxf.radius, 0.0, 360.0)
        out.append(dict(common, type="polyline", points=pts,
                        closed=True, text=None))
    elif etype == "ARC":
        c = entity.dxf.center
        pts = _discretize_arc(c.x, c.y, entity.dxf.radius,
                              entity.dxf.start_angle, entity.dxf.end_angle)
        out.append(dict(common, type="polyline", points=pts,
                        closed=False, text=None))
    elif etype == "POINT":
        p = entity.dxf.location
        out.append(dict(common, type="point", points=[(p.x, p.y)],
                        closed=False, text=None))
    elif etype in ("TEXT", "MTEXT"):
        if etype == "TEXT":
            text = str(entity.dxf.text).strip()
            ip = entity.dxf.insert
        else:
            text = entity.plain_text().strip()
            ip = entity.dxf.insert
        if text:
            out.append(dict(common, type="text", points=[(ip.x, ip.y)],
                            closed=False, text=text))
    elif etype == "INSERT":
        # 块引用：展开虚拟实体后递归解析
        try:
            for ve in entity.virtual_entities():
                _parse_entity(ve, out)
        except Exception:
            pass


def parse_dxf(path):
    """解析 DXF 文件，返回 (entities, doc_info)。容错读取（recover）。"""
    doc, auditor = recover.readfile(str(path))
    msp = doc.modelspace()

    entities = []
    for entity in msp:
        _parse_entity(entity, entities)

    layers = sorted({e["layer"] for e in entities})
    doc_info = {
        "dxf_version": doc.dxfversion,
        "acad_release": doc.acad_release,
        "layer_count": len(layers),
        "entity_count": len(entities),
        "layers": layers,
        "audit_errors": len(auditor.errors) if auditor else 0,
    }
    return entities, doc_info
