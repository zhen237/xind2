# -*- coding: utf-8 -*-
"""图册布局打桩回归：create_standard_engineering_sheet（A/B 缺陷修复后语义）。

源自 QA 的 qa_regress_eaf152a.py 打桩框架（fake qgis 注入 + FakeItem 记录型
断言），本版将 A/B 探针更新为修复后的正确语义：

  缺陷一  appendPage 不存在 → 改用 QgsLayoutItemPage + addPage，恰 2 次
  缺陷二  setPage 不存在    → bind_page 走 attemptMove(page=p)
  缺陷 A  BOM 表/技术要求未绑第 3 页 → 辅助函数返回 item，
          调用点 bind_page(item, 2)（attemptMove 收到 page=2）
  缺陷 B  draw_frame/add_title_block 手工 y+=PH*index 跨页 → 改为
          页内坐标 + attemptMove(page=page_index)，无 y>=PH 的越界项

运行方式（不依赖 QGIS/pytest）：
    python tests/test_drawset_layout_regress.py   # exit 0 = 全部通过
"""
import sys
import os
import types
import glob
import tempfile
import importlib

TEMP = tempfile.gettempdir()

# ---------------------------------------------------------------- fake qgis
class FakePoint:
    def __init__(self, x, y, units=None):
        self._x, self._y = float(x), float(y)

    def x(self): return self._x
    def y(self): return self._y


class FakeSize:
    def __init__(self, w, h, units=None):
        self._w, self._h = float(w), float(h)

    def width(self): return self._w
    def height(self): return self._h


PAGE_GAP = 10.0  # QGIS spaceBetweenPages 默认值（非 0 即可复现错位）


def predict_page(y, heights, gap=PAGE_GAP):
    """镜像 QgsLayoutPageCollection.predictPageNumberForPoint 的语义：
    point 为页内相对坐标，页判定不含页间隙。"""
    cur, i = 0.0, 0
    for h in heights:
        if y < cur + h:
            return i
        cur += h + gap
        i += 1
    return len(heights) - 1


class FakeRectangle:
    def __init__(self, *a):
        if len(a) == 1 and isinstance(a[0], FakeRectangle):
            self._v = tuple(a[0]._v)
        elif len(a) >= 4:
            self._v = tuple(float(x) for x in a[:4])
        else:
            self._v = (111.0, 35.0, 112.0, 36.0)

    def xMinimum(self): return self._v[0]
    def yMinimum(self): return self._v[1]
    def xMaximum(self): return self._v[2]
    def yMaximum(self): return self._v[3]
    def width(self): return self._v[2] - self._v[0]
    def height(self): return self._v[3] - self._v[1]
    def isEmpty(self):
        return self._v[2] <= self._v[0] or self._v[3] <= self._v[1]

    def buffered(self, d):
        return FakeRectangle(self._v[0] - d, self._v[1] - d,
                             self._v[2] + d, self._v[3] + d)


class FakeItem:
    def __init__(self, kind, layout=None):
        self.kind = kind
        self.moves = []          # (x, y, page_kwarg_or_None)
        self.last = (0.0, 0.0)

    def attemptMove(self, point, *a, **kw):
        self.moves.append((point.x(), point.y(), kw.get("page")))
        self.last = (point.x(), point.y())

    def attemptResize(self, size, *a, **kw):
        pass

    def positionWithUnits(self):
        return FakePoint(*self.last)

    def setPageSize(self, size):
        self._psize = (size.width(), size.height())

    def pageSize(self):
        return FakeSize(*getattr(self, "_psize", (420.0, 297.0)))

    def extent(self):
        return FakeRectangle()

    def setPage(self, p):
        raise AssertionError("item.setPage 不应再被调用（缺陷二回归）")

    def __getattr__(self, name):
        def _noop(*a, **kw):
            return None
        return _noop


class FakePage:
    def __init__(self, kind, layout=None):
        self.kind = kind
        self._size = (420.0, 297.0)

    def setPageSize(self, size):
        self._size = (size.width(), size.height())

    def pageSize(self):
        return FakeSize(*self._size)

    def __getattr__(self, name):
        return lambda *a, **kw: None


class FakePageCollection:
    def __init__(self):
        self._pages = [FakePage("page")]
        self.add_page_calls = []

    def addPage(self, page):
        self.add_page_calls.append(page)
        self._pages.append(page)

    def pages(self):
        return list(self._pages)

    def __getattr__(self, name):
        return lambda *a, **kw: None


class FakeLayout:
    def __init__(self, kind, project=None):
        self.kind = kind
        self.items = []
        self._pc = FakePageCollection()

    def pageCollection(self):
        return self._pc

    def addLayoutItem(self, item):
        self.items.append(item)

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _Exporter:
    Success = object()

    class PdfExportSettings:
        pass

    def __init__(self, layout):
        pass

    def exportToPdf(self, path, settings):
        with open(path, "wb") as f:
            f.write(b"%PDF-fake")
        return _Exporter.Success


def build_fake_qgis():
    core = types.ModuleType("qgis.core")

    def item_factory(kind):
        def make(layout=None, *a, **kw):
            return FakeItem(kind, layout)
        return make

    core.QgsProject = lambda *a, **kw: None
    core.QgsPrintLayout = lambda *a, **kw: FakeLayout(
        "layout", a[0] if a else None)
    for name in ("QgsLayoutItemMap", "QgsLayoutItemLabel",
                 "QgsLayoutItemLegend", "QgsLayoutItemScaleBar",
                 "QgsLayoutItemPicture"):
        setattr(core, name, item_factory(name))

    class _QgsLayoutItemShape:
        Rectangle = 0
        Ellipse = 1
        Triangle = 2

        def __new__(cls, layout=None, *a, **kw):
            return FakeItem("shape", layout)
    core.QgsLayoutItemShape = _QgsLayoutItemShape
    core.QgsLayoutItemPage = item_factory("page")
    core.QgsLayoutPoint = FakePoint
    core.QgsLayoutSize = FakeSize
    core.QgsRectangle = FakeRectangle  # 支持拷贝构造 / buffered
    core.QgsUnitTypes = types.SimpleNamespace(LayoutMillimeters="mm")
    core.QgsLayoutExporter = _Exporter
    for name in ("QgsMapSettings", "QgsCoordinateReferenceSystem",
                 "QgsCoordinateTransform", "QgsLayoutItemMapGrid",
                 "QgsPalLayerSettings", "QgsVectorLayerSimpleLabeling",
                 "QgsTextFormat"):
        setattr(core, name, lambda *a, **kw: None)

    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.QPointF = FakePoint
    qtcore.QSizeF = FakeSize
    qtcore.Qt = types.SimpleNamespace(WindowModal=1)
    qtcore.QCoreApplication = types.SimpleNamespace(
        processEvents=lambda *a: None)
    qtcore.QEventLoop = lambda *a, **kw: types.SimpleNamespace(
        quit=lambda: None, exec=lambda: None)
    qtcore.QTimer = types.SimpleNamespace(singleShot=lambda *a: None)

    qtgui = types.ModuleType("qgis.PyQt.QtGui")

    class QFont:
        Bold = "bold"

        def __init__(self, *a, **kw):
            pass
    qtgui.QFont = QFont
    qtgui.QColor = lambda *a, **kw: None

    qgis = types.ModuleType("qgis")
    pyqt = types.ModuleType("qgis.PyQt")
    qutils = types.ModuleType("qgis.utils")
    qutils.iface = None
    qgis.core = core
    qgis.PyQt = pyqt
    qgis.utils = qutils
    pyqt.QtCore = qtcore
    pyqt.QtGui = qtgui
    for name, mod in (("qgis", qgis), ("qgis.core", core), ("qgis.PyQt", pyqt),
                      ("qgis.PyQt.QtCore", qtcore), ("qgis.PyQt.QtGui", qtgui),
                      ("qgis.utils", qutils)):
        sys.modules[name] = mod


# ---------------------------------------------------------------- fake data
class FakeSite:
    name = "回归测试站"
    tower_type = "LATTICE"
    tower_height = 45.0
    longitude = 111.0
    latitude = 35.0

    def bill_of_materials(self):
        return {"items": [{"name": "角钢塔", "spec": "45m", "qty": 1,
                           "unit": "座"}],
                "summary": "汇总测试"}


class FakeExtent(FakeRectangle):
    def __init__(self):
        super().__init__(111.0, 35.0, 112.0, 36.0)


# ---------------------------------------------------------------- run
def main():
    build_fake_qgis()
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mod = importlib.import_module("design_engine.layout_export")

    before = set(glob.glob(os.path.join(TEMP, "eng_*")))
    failures = []

    def check(name, cond, detail=""):
        print(("PASS  " if cond else "FAIL  ") + name +
              (f"  [{detail}]" if detail else ""))
        if not cond:
            failures.append(name)

    # ---- 成功路径 ----
    layout_ref = {}
    orig_print_layout = mod.QgsPrintLayout

    def capture_layout(project=None):
        lay = orig_print_layout(project)
        layout_ref["layout"] = lay
        return lay
    mod.QgsPrintLayout = capture_layout

    result = mod.create_standard_engineering_sheet(
        project=None, sites=[FakeSite()], machine_rooms=[],
        map_extent=FakeExtent(),
        output_path=os.path.join(TEMP, "qa_regress_out.pdf"),
        progress_callback=None)
    layout = layout_ref["layout"]

    # 1. addPage 恰好 2 次，且每页 setPageSize(420,297)
    pc = layout.pageCollection()
    check("缺陷一: addPage 恰好调用 2 次", len(pc.add_page_calls) == 2,
          f"实际 {len(pc.add_page_calls)} 次")
    check("缺陷一: 每个新页 setPageSize(420,297)",
          all(abs(p.pageSize().width() - 420) < 1e-6 and
              abs(p.pageSize().height() - 297) < 1e-6
              for p in pc.add_page_calls))
    check("缺陷一: 布局总页数 == 3", len(pc.pages()) == 3,
          f"实际 {len(pc.pages())}")

    # 2. attemptMove page 参数分布 + setPage 不再被调用（setPage 定义为 raise）
    #    分布构成（A/B 修复后）：
    #      bind_page 绑定项: P1 标题/地图/图例/比例尺/指北针 = 5 个 page=0；
    #                        P2 标题+立面 SVG = 2 个 page=1；
    #                        P3 标题+机房 SVG+BOM+技术要求 = 4 个 page=2
    #      draw_frame: 每页外框+内框 = 2 个 → 3 页共 6 个
    #      add_title_block: 每页 7 分隔线 + 8 标签 + 8 值 + 1 外框 = 24
    #                       → 3 页共 72 个
    #    => page0: 5+2+24=31, page1: 2+2+24=28, page2: 4+2+24=30
    dist = {}
    for it in layout.items:
        for (x, y, p) in it.moves:
            if p is not None:
                dist[p] = dist.get(p, 0) + 1
    check("缺陷二: attemptMove page 参数分布 == {0:31, 1:28, 2:30}",
          dist == {0: 31, 1: 28, 2: 30}, f"实际 {dist}")
    check("缺陷二: 无任何 item 调用 setPage（定义 raise 未触发）", True)  # 未抛即过

    # 3. 缺陷 A 探针（修复后语义）：BOM 表 / 技术要求必须绑定第 3 页
    #    （辅助函数内部初次 attemptMove 无 page 属预期，随后由 bind_page
    #     以 page=2 重新定位；此处断言每个目标 item 存在 page=2 的绑定移动）
    bom_item = next((it for it in layout.items
                     if it.kind == "QgsLayoutItemPicture" and it.moves
                     and abs(it.moves[0][0] - 270) < 1), None)
    check("新缺陷A修复: BOM 表已绑定第 3 页（attemptMove page=2）",
          bom_item is not None
          and any(p == 2 for (_, _, p) in bom_item.moves),
          "未找到 BOM 图项或无 page=2 绑定")
    tech_item = next((it for it in layout.items
                      if it.kind == "QgsLayoutItemLabel" and it.moves
                      and abs(it.moves[0][0] - 18) < 1
                      and abs(it.moves[0][1] - 235) < 1), None)
    check("新缺陷A修复: 技术要求已绑定第 3 页（attemptMove page=2）",
          tech_item is not None
          and any(p == 2 for (_, _, p) in tech_item.moves),
          "未找到技术要求标签或无 page=2 绑定")

    # 4. 缺陷 B 探针（修复后语义）：图框/图衔 shape 一律页内坐标 + page 绑定，
    #    不允许出现 y>=PH 的手工跨页偏移（页间隙未计入的标志）
    bad_shapes = []
    for it in layout.items:
        if it.kind != "shape":
            continue
        for (x, y, p) in it.moves:
            if p is None or y >= 297.0:
                bad_shapes.append((x, y, p))
    check("新缺陷B修复: 图框/图衔 shape 全部页内坐标且带 page 绑定",
          not bad_shapes, str(bad_shapes))
    bad_tb_labels = [(x, y, p) for it in layout.items
                     if it.kind == "QgsLayoutItemLabel"
                     for (x, y, p) in it.moves
                     if y >= 268.0 and p is None]  # 268=A3 图衔条带顶部
    check("新缺陷B修复: 图衔 label 无手工跨页偏移（y>=268 项均带 page）",
          not bad_tb_labels, str(bad_tb_labels))

    # 5. 成功路径 temp 清理
    after = set(glob.glob(os.path.join(TEMP, "eng_*")))
    check("temp: 成功路径无新增 eng_* 残留", not (after - before),
          str(after - before))

    # ---- 异常路径 ----
    def boom(*a, **kw):
        raise RuntimeError("模拟导出崩溃")
    orig_export = mod.export_layout_to_pdf
    mod.export_layout_to_pdf = boom
    raised = False
    try:
        mod.create_standard_engineering_sheet(
            project=None, sites=[FakeSite()], machine_rooms=[],
            map_extent=FakeExtent(),
            output_path=os.path.join(TEMP, "qa_regress_out2.pdf"))
    except RuntimeError:
        raised = True
    mod.export_layout_to_pdf = orig_export
    after2 = set(glob.glob(os.path.join(TEMP, "eng_*")))
    check("temp: 异常路径异常向上抛出（无静默降级）", raised)
    check("temp: 异常路径无新增 eng_* 残留（try/finally 生效）",
          not (after2 - before), str(after2 - before))

    print()
    if failures:
        print(f"RESULT: {len(failures)} 项失败 -> {failures}")
        return 1
    print("RESULT: 全部断言通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
