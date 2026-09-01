"""FastAPI HTTP 服务 —— 方案A（进程间调用）

Java 后端（8082）通过 HTTP 调用本引擎（默认 8092，避免与 M03 的 8083 冲突）：
  POST /api/engine/parse     解析 DXF（文件路径或上传内容）→ 分类 GeoJSON
  POST /api/engine/transform GeoJSON 坐标系转换
  POST /api/engine/fuse      CAD+GIS 融合
  GET  /api/engine/health    健康检查

启动（在 engine 目录下）：python -m cad_engine.server
或：uvicorn cad_engine.server:app --host 0.0.0.0 --port 8092
"""

import os
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List

from cad_engine.classifier import classify, load_mapping
from cad_engine.fusion import fuse
from cad_engine.geojson_writer import (feature_to_geojson_feature,
                                       write_layer_geojson)
from cad_engine.parser import parse_dxf
from cad_engine.transformer import (CoordinateTransformer, FourParam,
                                    SevenParam)

app = FastAPI(title="s2-cad-fusion 解析引擎", version="1.0.0")


class TransformRequest(BaseModel):
    geojson: dict
    source: str = "cgcs2000_gk111"
    target: str = "EPSG:4326"
    seven_param: Optional[dict] = None
    four_param: Optional[dict] = None


class FuseRequest(BaseModel):
    cad: dict
    gis: dict = Field(default_factory=lambda: {"type": "FeatureCollection",
                                                "features": []})
    dedup_tol_m: float = 5.0


class ParseResult(BaseModel):
    """解析响应。layers[ftype] = {feature_count, geojson?, file?}，
    geojson 为内存返回的完整 FeatureCollection（不依赖落盘），
    便于 Java 侧跨进程直接获取要素。"""
    doc_info: dict
    classify_stats: dict
    layers: dict


def _make_transformer(source, target, seven, four):
    seven_obj = SevenParam.from_json(seven) if seven else None
    four_obj = FourParam.from_json(four) if four else None
    return CoordinateTransformer(source=source, target=target,
                                 seven_param=seven_obj, four_param=four_obj)


@app.get("/api/engine/health")
def health():
    return {"status": "UP", "engine": "cad_engine", "version": "1.0.0"}


@app.post("/api/engine/parse", response_model=ParseResult)
async def parse(file: UploadFile = File(...),
                source: str = "cgcs2000_gk111",
                target: str = "EPSG:4326",
                outdir: Optional[str] = None):
    """上传 DXF 解析。outdir 为空时仅返回统计与要素，不落盘。"""
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in (".dxf", ".dwg"):
        raise HTTPException(400, f"仅支持 DXF/DWG，收到: {suffix}")
    content = await file.read()
    if suffix == ".dwg":
        raise HTTPException(501, "DWG 解析依赖 libredwg/ODA，当前版本优先支持 DXF")

    with tempfile.NamedTemporaryFile("wb", suffix=".dxf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        entities, doc_info = parse_dxf(tmp_path)
    finally:
        os.unlink(tmp_path)

    mapping = load_mapping()
    grouped, stats = classify(entities, mapping)
    transformer = _make_transformer(source, target, None, None)

    layers = {}
    for ftype, feats in grouped.items():
        if not feats:
            continue
        out_feats = [feature_to_geojson_feature(f, transformer) for f in feats]
        layer_info = {
            "feature_count": len(out_feats),
            # 内存返回完整要素，供跨进程调用（方案A）直接消费
            "geojson": {
                "type": "FeatureCollection",
                "name": ftype,
                "crs_info": {"source_crs": source, "target_crs": target},
                "features": out_feats,
            },
        }
        if outdir:
            out_path = os.path.join(outdir, f"{ftype}.geojson")
            write_layer_geojson(out_path, out_feats, source, target)
            layer_info["file"] = out_path
        layers[ftype] = layer_info

    return ParseResult(doc_info=doc_info, classify_stats=stats, layers=layers)


@app.post("/api/engine/transform")
def transform(req: TransformRequest):
    transformer = _make_transformer(req.source, req.target,
                                    req.seven_param, req.four_param)
    fc = req.geojson
    for feat in fc.get("features", []):
        geom = feat["geometry"]
        try:
            if geom["type"] == "Point":
                geom["coordinates"] = list(transformer.transform_point(*geom["coordinates"]))
            elif geom["type"] == "LineString":
                geom["coordinates"] = [list(transformer.transform_point(*p))
                                       for p in geom["coordinates"]]
            elif geom["type"] == "Polygon":
                geom["coordinates"] = [[list(transformer.transform_point(*p))
                                        for p in ring] for ring in geom["coordinates"]]
        except ValueError as e:
            raise HTTPException(400, str(e))
    fc["crs_info"] = {"source_crs": req.source, "target_crs": req.target}
    return fc


@app.post("/api/engine/fuse")
def do_fuse(req: FuseRequest):
    merged, stats = fuse(req.cad, req.gis, dedup_tol_m=req.dedup_tol_m)
    return merged


class FourParamEstimateRequest(BaseModel):
    """由控制点求解四参数"""
    points: List[dict]  # [{"local":[x,y], "national":[X,Y]}, ...]


@app.post("/api/engine/four-param/estimate")
def estimate_four_param(req: FourParamEstimateRequest):
    try:
        fp = FourParam.from_json({"points": req.points})
        return fp.to_dict()
    except ValueError as e:
        raise HTTPException(400, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8092)
