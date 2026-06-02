# 数据目录

武汉光谷区域（114.30E-114.45E, 30.45N-30.55N）公开数据 + 样例数据。

## 结构

```
data/
├── dem/                  # SRTM 30m高程数据（手动下载）
├── osm/                  # OSM建筑/道路/电力线（scripts/fetch_data.py自动下载）
├── sample_designs/       # 8个虚拟基站样例设计方案
└── construction_photos/  # 施工现场照片（CV训练/测试）
```

## 数据准备

```bash
cd scripts
python fetch_data.py
```
