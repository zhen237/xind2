#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DXF 导出诊断脚本
用法：
    python inspect_dxf.py <你的文件.dxf>
或：
    "C:\\Program Files\\QGIS 3.44.11\\apps\\Python312\\python.exe" inspect_dxf.py <文件>

输出：图层列表、实体数量、坐标范围、实体类型统计。
"""
import sys
import os

try:
    import ezdxf
except Exception as e:
    print(f"[错误] 无法导入 ezdxf: {e}")
    print("[提示] 如果你用 QGIS 的 Python，请用这个解释器运行：")
    print(r'  "C:\\Program Files\\QGIS 3.44.11\\apps\\Python312\\python.exe" inspect_dxf.py 文件.dxf')
    sys.exit(1)


def inspect(dxf_path):
    if not os.path.isfile(dxf_path):
        print(f"[错误] 文件不存在: {dxf_path}")
        sys.exit(1)

    print(f"文件: {dxf_path}")
    print(f"大小: {os.path.getsize(dxf_path) / 1024:.1f} KB")

    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"[错误] ezdxf 无法读取该文件: {e}")
        sys.exit(1)

    print(f"DXF 版本: {doc.dxfversion}")

    # 图层表
    layers = list(doc.layers)
    print(f"\n图层数量: {len(layers)}")
    print("-" * 50)
    print(f"{'图层名':<20} {'颜色(ACI)':<12} {'线宽':<10}")
    print("-" * 50)
    for layer in layers:
        name = layer.dxf.name
        color = layer.dxf.color
        lw = layer.dxf.lineweight
        print(f"{name:<20} {color:<12} {lw:<10}")

    # 模型空间实体
    msp = doc.modelspace()
    entities = list(msp)
    print(f"\n模型空间实体总数: {len(entities)}")

    if not entities:
        print("[警告] 模型空间里没有任何实体！DXF 是空的。")
        return

    # 按图层统计
    by_layer = {}
    by_type = {}
    xs, ys = [], []
    for e in entities:
        t = e.dxftype()
        by_type[t] = by_type.get(t, 0) + 1
        try:
            ln = e.dxf.layer
        except Exception:
            ln = "<无图层>"
        by_layer[ln] = by_layer.get(ln, 0) + 1

        # 收集坐标
        try:
            if hasattr(e, "get_points"):
                pts = list(e.get_points())
                for p in pts:
                    xs.append(p[0]); ys.append(p[1])
            elif hasattr(e, "dxf"):
                # POINT / TEXT / MTEXT / LINE / LWPOLYLINE 等
                if hasattr(e.dxf, "location"):
                    loc = e.dxf.location
                    xs.append(loc.x); ys.append(loc.y)
                if hasattr(e.dxf, "start"):
                    s = e.dxf.start; en = e.dxf.end
                    xs.extend([s.x, en.x]); ys.extend([s.y, en.y])
                if hasattr(e.dxf, "insert"):
                    ins = e.dxf.insert
                    xs.append(ins.x); ys.append(ins.y)
                if hasattr(e.dxf, "text_midpoint"):
                    tm = e.dxf.text_midpoint
                    xs.append(tm.x); ys.append(tm.y)
        except Exception:
            pass

    print("\n按图层统计:")
    print("-" * 40)
    for ln, cnt in sorted(by_layer.items(), key=lambda x: -x[1]):
        print(f"  {ln:<20} {cnt} 个")

    print("\n按实体类型统计:")
    print("-" * 40)
    for t, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:<15} {cnt} 个")

    if xs and ys:
        print("\n坐标范围 (模型空间):")
        print("-" * 40)
        print(f"  X: {min(xs):.3f} ~ {max(xs):.3f}  (宽度 {max(xs)-min(xs):.3f})")
        print(f"  Y: {min(ys):.3f} ~ {max(ys):.3f}  (高度 {max(ys)-min(ys):.3f})")
        print(f"  中心: ({(min(xs)+max(xs))/2:.3f}, {(min(ys)+max(ys))/2:.3f})")
    else:
        print("\n[警告] 无法提取坐标范围（实体可能没有几何信息）")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python inspect_dxf.py <文件.dxf>")
        sys.exit(1)
    inspect(sys.argv[1])
