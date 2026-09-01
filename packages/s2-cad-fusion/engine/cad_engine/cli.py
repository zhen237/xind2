"""命令行入口 —— 全链路：解析 → 分类 → 坐标转换 → GeoJSON（→ 可选融合）

用法示例：
  python -m cad_engine.cli run  --input sample.dxf --outdir out/
  python -m cad_engine.cli parse --input sample.dxf --outdir out/
  python -m cad_engine.cli transform --input out/well_point.geojson \
        --source cgcs2000_gk111 --target EPSG:4326
  python -m cad_engine.cli fuse --cad out/redline.geojson \
        --gis gis_baseline.geojson -o out/fused.geojson
"""

import argparse
import glob
import json
import os
import sys

from .classifier import classify, load_mapping
from .fusion import fuse
from .geojson_writer import (feature_to_geojson_feature, load_geojson,
                             write_layer_geojson)
from .parser import parse_dxf
from .transformer import CoordinateTransformer, FourParam, SevenParam


def _build_transformer(args, mapping):
    defaults = (mapping or {}).get("transform_defaults", {})
    source = getattr(args, "source", None) or defaults.get("source_crs", "cgcs2000_gk111")
    target = getattr(args, "target", None) or defaults.get("target_crs", "EPSG:4326")
    seven = None
    if getattr(args, "seven_param", None):
        seven = SevenParam.from_json(args.seven_param)
    four = None
    if getattr(args, "four_param", None):
        four = FourParam.from_json(args.four_param)
    return CoordinateTransformer(source=source, target=target,
                                 seven_param=seven, four_param=four), source, target


def cmd_parse(args):
    """解析 + 分类 + 坐标转换 + 输出按图层分类的 GeoJSON（不做融合）。"""
    mapping = load_mapping(args.mapping)
    entities, doc_info = parse_dxf(args.input)
    grouped, stats = classify(entities, mapping)

    transformer, source, target = _build_transformer(args, mapping)

    os.makedirs(args.outdir, exist_ok=True)
    summary = {"input": os.path.abspath(args.input), "doc_info": doc_info,
               "classify": stats, "source_crs": source, "target_crs": target,
               "layers": {}}

    for ftype, feats in grouped.items():
        if not feats:
            continue
        out_feats = [feature_to_geojson_feature(f, transformer) for f in feats]
        out_path = os.path.join(args.outdir, f"{ftype}.geojson")
        write_layer_geojson(out_path, out_feats, source, target)
        summary["layers"][ftype] = {
            "feature_count": len(out_feats),
            "file": out_path,
        }

    with open(os.path.join(args.outdir, "parse_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


def cmd_transform(args):
    """对已解析的 GeoJSON 做坐标系转换（FR-4/FR-5 独立调用）。"""
    mapping = load_mapping(args.mapping)
    fc = load_geojson(args.input)
    transformer, source, target = _build_transformer(args, mapping)

    for feat in fc["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Point":
            x, y = transformer.transform_point(*geom["coordinates"])
            geom["coordinates"] = [round(x, 8), round(y, 8)]
        elif geom["type"] == "LineString":
            geom["coordinates"] = [[round(v, 8) for v in transformer.transform_point(*p)]
                                   for p in geom["coordinates"]]
        elif geom["type"] == "Polygon":
            geom["coordinates"] = [[[round(v, 8) for v in transformer.transform_point(*p)]
                                    for p in ring] for ring in geom["coordinates"]]

    fc["crs_info"] = {"source_crs": source, "target_crs": target}
    out = args.output or args.input
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=1)
    print(f"已转换 {len(fc['features'])} 个要素: {source} → {target}, 输出 {out}")
    return fc


def cmd_fuse(args):
    """CAD + GIS 融合（FR-6/FR-7）。"""
    cad_fc = load_geojson(args.cad)
    gis_fc = load_geojson(args.gis) if args.gis else {"type": "FeatureCollection",
                                                       "features": []}
    merged, stats = fuse(cad_fc, gis_fc, dedup_tol_m=args.dedup_tol)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=1)
    print(json.dumps(merged["fusion_stats"], ensure_ascii=False, indent=1))
    if merged["conflict_details"]:
        print("冲突明细:")
        for d in merged["conflict_details"]:
            print(" -", json.dumps(d, ensure_ascii=False))
    return merged


def cmd_run(args):
    """全链路：解析 → 分类 → 转换 → 输出（+ 可选融合 gis 目录下同名文件）。"""
    summary = cmd_parse(args)
    if args.gis_dir:
        for layer_file in sorted(glob.glob(
                os.path.join(args.outdir, "*.geojson"))):
            base = os.path.splitext(os.path.basename(layer_file))[0]
            gis_file = os.path.join(args.gis_dir, base + ".geojson")
            if os.path.isfile(gis_file):
                merged, _ = fuse(load_geojson(layer_file), load_geojson(gis_file))
                out = os.path.join(args.outdir, f"fusion_{base}.geojson")
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(merged, f, ensure_ascii=False, indent=1)
                print(f"融合[{base}]: {json.dumps(merged['fusion_stats'], ensure_ascii=False)} → {out}")
    return summary


def build_argparser():
    ap = argparse.ArgumentParser(prog="cad_engine",
                                 description="多源异构工程数据融合 Python 引擎")
    sub = ap.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--mapping", default=None, help="图层映射配置 yml 路径")
        p.add_argument("--source", default=None,
                       help="源坐标系: wgs84/cgcs2000/cgcs2000_gk111/local/EPSG:xxxx/+proj=...")
        p.add_argument("--target", default=None, help="目标坐标系，默认 EPSG:4326")
        p.add_argument("--seven-param", default=None,
                       help='七参数 JSON: {"dx":..,"dy":..,"dz":..,"rx":..,"ry":..,"rz":..,"s":..}')
        p.add_argument("--four-param", default=None,
                       help='四参数 JSON（参数或控制点）: {"a":..,"b":..,"dx":..,"dy":..} '
                            '或 {"points":[{"local":[x,y],"national":[X,Y]},...]}')

    p1 = sub.add_parser("parse", help="解析 DXF → 按图层分类的 GeoJSON")
    p1.add_argument("--input", required=True, help="输入 .dxf 文件")
    p1.add_argument("--outdir", required=True)
    common(p1)
    p1.set_defaults(func=cmd_parse)

    p2 = sub.add_parser("transform", help="GeoJSON 坐标系转换")
    p2.add_argument("--input", required=True)
    p2.add_argument("--output", "-o", default=None)
    common(p2)
    p2.set_defaults(func=cmd_transform)

    p3 = sub.add_parser("fuse", help="CAD+GIS 融合")
    p3.add_argument("--cad", required=True, help="CAD GeoJSON")
    p3.add_argument("--gis", default=None, help="GIS 基准 GeoJSON（缺省为空集）")
    p3.add_argument("--output", "-o", default=None)
    p3.add_argument("--dedup-tol", type=float, default=5.0, help="去重容差(米)")
    p3.set_defaults(func=cmd_fuse)

    p4 = sub.add_parser("run", help="全链路（解析→转换→可选融合）")
    p4.add_argument("--input", required=True)
    p4.add_argument("--outdir", required=True)
    p4.add_argument("--gis-dir", default=None, help="GIS 基准 GeoJSON 目录（可选）")
    common(p4)
    p4.set_defaults(func=cmd_run)

    return ap


def main(argv=None):
    args = build_argparser().parse_args(argv)
    if args.mapping:
        import cad_engine.classifier as _c
        _c.MAPPING_FILE = args.mapping
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
