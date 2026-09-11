#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设计报告字段级自动化率统计脚本（PPT 可引用、可复现）。

用途
----
量化「通信设施智能设计方案报告」的自动生成程度，为挑战杯 PPT 提供可复现数字：
    python scripts/measure_report_automation.py [--sites N] [--out DIR]

做法（不引入 QGIS GUI 依赖）
--------------------------
1. 用 `ast` 从 `qgis-plugin/ui/design_dock.py` 中抽取方法
   `_build_local_design_report`（设计报告的**真实生产代码**，不复制/不改写）；
2. 注入一个「合成 self」（合成 N 个站点/机房/管线/设备 + FTTH 统计），
   在纯 Python 环境下直接执行该方法，得到真实的 Markdown 报告；
3. 解析 Markdown 表格，统计表数 / 数据行数 / 字段单元格总数 / 字符数 / 行数；
4. 产出报告样例 `.md` 与指标 `.json`（默认写到仓库外的 .workbuddy/tmp_measure）。

口径（**引用 PPT 时请连同口径一起说明**）
--------------------------------------
- 分母 = 报告内所有表格的「数据单元格」总数（不含表头行与 Markdown 分隔行）。
- 分子 = 由插件自动计算/汇总生成的字段单元格。
- 人工填表单元格 = 0：本脚本注入的是合成配置（仅 N 站点等少量入参），
  报告全部内容由 `_build_local_design_report` 生成，无人工填写单元格，
  故当前口径下 **字段级自动化率 = 100%**。
- 与之互补的「章节级」口径：报告 8 个章节全部由代码成文（人工撰写 0 句）。

局限性（**不要在 PPT 里省略**）
---------------------------
1. 配置为**合成数据**（N 个站点，见 `build_synthetic_dock`），非真实片区数据；
   站点/机房/设备数变化时，报告行数与单元格数随之变化（线性，见下）。
2. **非 QGIS GUI 真跑**：报告生成逻辑逐字取自设计插件的真实函数，但未在
   QGIS 界面中点击按钮；`_analyze_signal_strength` 为与插件同源的
   Okumura-Hata 采样实现的等价替身（同样调用 design_engine.coverage_heatmap）。
3. 行数随站点/设备数线性增长（本脚本默认规则：每站 1 机房 + 1 管线 + 2 台设备）：
   `数据行数 = 36 + 12N`、`字段单元格总数 = 116 + 73N`（N = 站点数；
   其中 BOM 明细表为 8 类物料 × 6 列 × N 站 = 48N，是单元格的主体）。
4. 「自动化率」只反映“报告文本/字段由程序生成的比例”，**不等于**设计本身的
   自动化程度（设计参数选型、区域框选、成果审核仍需人工，见 docs/ 说明）。
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "qgis-plugin"
DESIGN_DOCK = PLUGIN_ROOT / "ui" / "design_dock.py"
DEFAULT_OUT = REPO_ROOT / ".workbuddy" / "tmp_measure"
TARGET_METHOD = "_build_local_design_report"

# 与 design_dock.py 中第三步/第四步下拉框一致的默认值
BAND_KEY = "3.5GHz"
TECH_KEY = "5G 独立组网(SA)"
SCENARIO_TEXT = "城市(URBAN)"


# --------------------------------------------------------------------------- #
#  1. ast 抽取真实方法源码
# --------------------------------------------------------------------------- #
def extract_report_method(source_path: Path = DESIGN_DOCK) -> str:
    """从 design_dock.py 抽取 _build_local_design_report 的源码（去缩进）。"""
    text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(source_path))

    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == TARGET_METHOD:
            target = node
            break
    if target is None:
        raise SystemExit(
            "未在 %s 中找到方法 %s（源码结构可能已变更，请同步更新本脚本）"
            % (source_path, TARGET_METHOD))

    segment = ast.get_source_segment(text, target)
    if not segment:
        lines = text.splitlines()
        segment = "\n".join(lines[target.lineno - 1: target.end_lineno])
    return textwrap.dedent(segment)


# --------------------------------------------------------------------------- #
#  2. 编译方法 + 合成 self（纯 Python，无 QGIS）
# --------------------------------------------------------------------------- #
class _Combo:
    """QComboBox 替身。"""

    def __init__(self, text: str):
        self._text = text

    def currentText(self) -> str:  # noqa: N802 (模仿 Qt API)
        return self._text


class _Spin:
    """QDoubleSpinBox 替身。"""

    def __init__(self, value: float):
        self._value = value

    def value(self) -> float:  # noqa: N802
        return self._value


def _build_signal_analyzer(sites, band_key, tech_height, scenario):
    """返回与插件同源的 `_analyze_signal_strength` 替身（Okumura-Hata 采样）。"""
    def _analyze_signal_strength(self):
        from design_engine.rules import BAND_CONFIGS
        from design_engine.coverage_heatmap import generate_coverage_heatmap_data

        config = BAND_CONFIGS.get(band_key)
        if not config or not sites:
            return None
        radius_km = config.ideal_isr_km * 1.5
        all_rsrp = []
        for s in sites:
            data = generate_coverage_heatmap_data(
                site_lon=s.get("longitude", 0),
                site_lat=s.get("latitude", 0),
                tx_height_m=tech_height,
                frequency_mhz=config.frequency_mhz,
                tx_power_w=config.default_power_w,
                antenna_gain_dbi=config.default_gain_dbi,
                radius_km=radius_km,
                resolution_m=150,
                rsrp_threshold_dbm=-110,
                environment=scenario,
            )
            all_rsrp.extend(d["rsrp"] for d in data)
        if not all_rsrp:
            return None
        total = len(all_rsrp)
        grades = [
            ("优 (Excellent)", "≥ -65 dBm", len([r for r in all_rsrp if r >= -65])),
            ("良 (Good)", "-80 ~ -65 dBm", len([r for r in all_rsrp if -80 <= r < -65])),
            ("中 (Fair)", "-90 ~ -80 dBm", len([r for r in all_rsrp if -90 <= r < -80])),
            ("差 (Poor)", "-100 ~ -90 dBm", len([r for r in all_rsrp if -100 <= r < -90])),
            ("盲区 (None)", "< -100 dBm", len([r for r in all_rsrp if r < -100])),
        ]
        avg = round(sum(all_rsrp) / total, 1)
        covered = len([r for r in all_rsrp if r >= -80])
        blind = len([r for r in all_rsrp if r < -100])
        return {
            "total": total,
            "avg_rsrp": avg,
            "coverage_rate": round(covered / total * 100, 1),
            "blind_rate": round(blind / total * 100, 1),
            "grades": grades,
            "radius_km": round(radius_km, 2),
            "scenario": scenario,
            "band_key": band_key,
        }

    return _analyze_signal_strength


def build_synthetic_dock(sites_n: int = 3):
    """构造合成 self：每站配套 1 个机房 + 1 条管线 + 2 台设备。

    规则（与脚本头部“局限性 3”一致，决定了行数/单元格数的线性增长）：
      - 站点 N 个；机房 N 个；管线 N 条；设备 2N 台；FTTH 统计 1 张（5 行）。
      - BOM 每站 8 类物料（35m 单管塔地面站，见 models/site.bill_of_materials）。
    """
    from models.pipeline import Pipeline, PipelineType, FiberType

    heights = 35.0
    sites = []
    rooms = []
    pipes = []
    devices = []
    for i in range(sites_n):
        sid = "BTS-%03d" % (i + 1)
        lon = round(114.30 + i * 0.01, 5)
        lat = round(30.50 + i * 0.01, 5)
        sites.append({
            "site_id": sid,
            "name": "演示基站%d" % (i + 1),
            "site_type": "MACRO",
            "mount_type": "GROUND",
            "tower_type": "MONOPOLE",
            "tower_height": heights,
            "band": BAND_KEY,
            "tech_generation": TECH_KEY,
            "longitude": lon,
            "latitude": lat,
        })
        rooms.append({
            "room_id": "ROOM-%03d" % (i + 1),
            "name": "汇聚机房%d" % (i + 1),
            "room_type": "汇聚机房",
            "longitude": round(lon + 0.002, 5),
            "latitude": round(lat - 0.002, 5),
            "capacity": 50.0,
            "power_supply": "AC220V",
            "served_site_id": sid,
        })
        pipes.append(Pipeline(
            pipeline_id="PIPE-%03d" % (i + 1),
            start_site_id=sid,
            end_site_id="ROOM-%03d" % (i + 1),
            pipeline_type=PipelineType.DIRECT_BURIED,
            coordinates=[(lon, lat), (round(lon + 0.002, 5), round(lat - 0.002, 5))],
            length_m=300.0 + i * 50.0,
            depth_m=1.2,
            diameter_mm=110,
            material="PE",
            capacity=4,
            fiber_type=FiberType.G652D,
        ))
        devices.extend([
            {"parentDevice": sid, "deviceName": "AAU-3.5G", "deviceType": "AAU",
             "azimuth": 0 + i * 30, "downtilt": 6},
            {"parentDevice": sid, "deviceName": "RRU-2.1G", "deviceType": "RRU",
             "azimuth": 120 + i * 30, "downtilt": 4},
        ])

    ftth_design = {
        "mode": "greenfield",
        "stats": {
            "olt_count": sites_n,
            "fd_count": 12,
            "building_count": 51,
            "trunk_cables": 12,
            "trunk_length_km": 3.6,
            "drop_cables": 51,
            "drop_length_km": 7.65,
        },
    }

    class SyntheticDock(object):
        """合成 DesignDock：仅提供报告方法读取的属性。"""

        def __init__(self):
            self.generated_sites = sites
            self.machine_rooms = rooms
            self.generated_pipelines = pipes
            self._device_layout = devices
            self.ftth_design = ftth_design
            self._build_mode = "greenfield"
            self.selected_extent = (114.25, 30.45, 114.40, 30.60)
            self.scenario_combo = _Combo(SCENARIO_TEXT)
            self.band_combo = _Combo(BAND_KEY)
            self.tech_combo = _Combo(TECH_KEY)
            self.height_spin = _Spin(heights)

        def _log(self, msg):  # 插件日志替身：静默
            pass

        _analyze_signal_strength = _build_signal_analyzer(
            sites, BAND_KEY, heights, "URBAN")

    return SyntheticDock()


def render_report(sites_n: int = 3) -> str:
    """执行真实方法，返回 Markdown 报告文本。"""
    if str(PLUGIN_ROOT) not in sys.path:
        sys.path.insert(0, str(PLUGIN_ROOT))

    from design_engine.rules import BAND_CONFIGS            # noqa: F401 (方法内引用)
    from design_engine.pipeline import calculate_total_cost  # noqa: F401
    from models.pipeline import Pipeline, PipelineType, FiberType  # noqa: F401

    method_src = extract_report_method()
    namespace = {
        "datetime": datetime,
        "BAND_CONFIGS": BAND_CONFIGS,
        "calculate_total_cost": calculate_total_cost,
    }
    try:
        code = compile(method_src, str(DESIGN_DOCK), "exec")
    except SyntaxError as exc:  # 源码异常时给出可定位信息
        raise SystemExit("抽取的方法源码编译失败: %s" % exc)
    exec(code, namespace)  # noqa: S102 (受控来源：本仓库源码)
    builder = namespace[TARGET_METHOD]

    dock = build_synthetic_dock(sites_n)
    return builder(dock)


# --------------------------------------------------------------------------- #
#  3. Markdown 表格统计
# --------------------------------------------------------------------------- #
_TABLE_SEP = re.compile(r"^\|[\s:|-]+\|$")


def _cells(row: str) -> int:
    """统计一行 Markdown 表格的数据单元格数（去掉两侧空管）。"""
    parts = row.strip().strip("|").split("|")
    return len([p for p in parts])


def measure(markdown: str) -> dict:
    """统计表数 / 数据行数 / 字段单元格总数，并给出逐表明细。"""
    lines = markdown.splitlines()
    tables = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and i + 1 < len(lines) \
                and _TABLE_SEP.match(lines[i + 1].strip()):
            header_cols = _cells(line)
            sep_idx = i + 1
            rows = []
            j = sep_idx + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(lines[j])
                j += 1
            tables.append({
                "columns": header_cols,
                "header": line,
                "data_rows": len(rows),
                "cells": sum(_cells(r) for r in rows),
            })
            i = j
            continue
        i += 1

    data_rows = sum(t["data_rows"] for t in tables)
    field_cells = sum(t["cells"] for t in tables)

    # 章节标题（## / ###）作为“章节/小节”计数，便于交叉核对
    sections = [l.strip() for l in lines if l.startswith("## ")]
    return {
        "tables": len(tables),
        "data_rows": data_rows,
        "field_cells": field_cells,
        "chars": len(markdown),
        "lines": len(lines),
        "sections": len(sections),
        "section_titles": sections,
        "table_detail": tables,
    }


# --------------------------------------------------------------------------- #
#  4. CLI
# --------------------------------------------------------------------------- #
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="measure_report_automation.py",
        description="统计设计报告（design_dock._build_local_design_report）的"
                    "字段级自动化率：表数 / 数据行数 / 字段单元格总数 / 字符数 / 行数。",
        epilog="口径：分母 = 字段单元格总数；人工填表单元格 = 0；"
               "字段级自动化率 = 100%（当前口径）。"
               "产物：report_sample.md + metrics.json（默认写入仓库外 "
               ".workbuddy/tmp_measure，不污染仓库）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sites", type=int, default=3,
                        help="合成站点数量（默认 3；机房/管线各 N 个，设备 2N 台）")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="产物输出目录（默认 %s，位于仓库外）" % DEFAULT_OUT)
    parser.add_argument("--skip-files", action="store_true",
                        help="只打印统计，不写 report_sample.md / metrics.json")
    args = parser.parse_args(argv)
    if args.sites < 1:
        parser.error("--sites 必须 >= 1")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out)

    markdown = render_report(args.sites)
    metrics = measure(markdown)

    metrics.update(OrderedDict([
        ("sites", args.sites),
        ("source_method", "%s::%s" % (DESIGN_DOCK.relative_to(REPO_ROOT).as_posix(),
                                      TARGET_METHOD)),
        ("generated_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
        ("human_filled_cells", 0),
        ("denominator_field_cells", metrics["field_cells"]),
        ("automation_rate_percent", 100.0),
        ("formula_rows", "36 + 12N"),
        ("formula_cells", "116 + 73N"),
        ("caveat", "合成数据 / 非 QGIS GUI 真跑 / 行数与站点数线性相关"),
    ]))

    print("=" * 72)
    print("设计报告字段级自动化率统计")
    print("=" * 72)
    print("数据源方法 : %s" % metrics["source_method"])
    print("合成配置   : %d 个站点（机房 %d / 管线 %d / 设备 %d 台）"
          % (args.sites, args.sites, args.sites, 2 * args.sites))
    print("-" * 72)
    print("章节数          : %d" % metrics["sections"])
    print("表数            : %d" % metrics["tables"])
    print("数据行数        : %d" % metrics["data_rows"])
    print("字段单元格总数  : %d" % metrics["field_cells"])
    print("字符数          : %d" % metrics["chars"])
    print("行数            : %d" % metrics["lines"])
    print("-" * 72)
    print("逐表明细（列数 / 数据行 / 单元格）：")
    for idx, t in enumerate(metrics["table_detail"], 1):
        print("  %2d. %-14s 列 %2d | 行 %3d | 单元格 %4d"
              % (idx, _short_header(t["header"]), t["columns"],
                 t["data_rows"], t["cells"]))
    print("-" * 72)
    print("分母 = 字段单元格总数；人工填表单元格 = 0；"
          "字段级自动化率 = 100%（当前口径）")
    print("=" * 72)

    if not args.skip_files:
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / ("report_sample_sites%d_%s.md" % (args.sites, stamp))
        json_path = out_dir / ("metrics_sites%d_%s.json" % (args.sites, stamp))
        md_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        print("报告样例 : %s" % md_path)
        print("指标 JSON: %s" % json_path)
        print("（输出目录位于仓库外，可用 --out 指定其它位置）")
    return 0


def _short_header(header: str, width: int = 12) -> str:
    """取表头首个单元格作为表名（便于控制台逐表打印）。"""
    first = header.strip().strip("|").split("|")[0].strip().replace("**", "")
    return first[:width]


if __name__ == "__main__":
    raise SystemExit(main())
