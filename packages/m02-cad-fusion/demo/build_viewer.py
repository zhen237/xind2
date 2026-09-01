#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 geojson_viewer.html：把 engine/out 的真实产物嵌入查看器模板。

用法（在 engine 重跑全链路后执行）：
    python demo/build_viewer.py
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ENGINE_OUT = HERE.parent / "engine" / "out"
TEMPLATE = HERE / "viewer_template.html"
TARGET = HERE / "geojson_viewer.html"


def main():
    if not TEMPLATE.exists():
        raise SystemExit(f"模板缺失: {TEMPLATE}")
    if not ENGINE_OUT.exists():
        raise SystemExit(f"引擎输出目录缺失: {ENGINE_OUT}（先跑 cad_engine.cli run）")

    data = {}
    for f in sorted(ENGINE_OUT.glob("*.geojson")):
        data[f.name] = json.loads(f.read_text(encoding="utf-8"))
    summary = ENGINE_OUT / "parse_summary.json"
    if summary.exists():
        data["parse_summary.json"] = json.loads(summary.read_text(encoding="utf-8"))

    html = TEMPLATE.read_text(encoding="utf-8")
    placeholder = "/*__EMBED__*/null"
    if placeholder not in html:
        raise SystemExit("模板中未找到注入占位符 /*__EMBED__*/null")
    html = html.replace(placeholder, json.dumps(data, ensure_ascii=False))
    TARGET.write_text(html, encoding="utf-8")

    n_geo = sum(1 for k in data if k.endswith(".geojson"))
    size_kb = TARGET.stat().st_size / 1024
    print(f"OK 已生成 {TARGET}")
    print(f"   嵌入 {n_geo} 个 GeoJSON 图层 + 解析摘要，文件大小 {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
