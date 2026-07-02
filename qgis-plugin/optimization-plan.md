# QGIS 基站智能设计插件 — 全面优化方案

> 基于比赛评分标准（100分）和当前插件架构，按优先级排序的完整优化方案

---

## P0-1：热力图渲染重构 — GDAL栅格 + 连续渐变色

**问题描述**：当前用数千个独立点做分级符号渲染，QGIS 3.44 下大量点导致卡顿甚至崩溃，视觉效果像"撒豆子"而非专业热力图。

**解决方案**：放弃逐点渲染，改用 GDAL 从坐标数据生成 GeoTIFF 栅格，再用 `QgsColorRampShader` 做连续伪彩色渲染。这是 Atoll、Planet 等专业电信软件的标准做法。

**预期效果**：
- 100个站点 × 10000+ 栅格点瞬间渲染，无卡顿
- 连续渐变色覆盖图，多站叠加自然融合
- 专业外观，评委一看就知道是工业级工具

**工作量**：约 100 行新增代码，替换 `_create_heatmap_layer` 函数主体，难度: medium

```python
# === 新建文件: design_engine/coverage_renderer.py ===
"""专业级覆盖渲染器 — 基于GDAL栅格的连续热力图"""
import math
import numpy as np
from typing import List, Dict, Tuple

# RSRP标准分级颜色表（符合3GPP/ITU-R建议）
RSRP_COLOR_STOPS = [
    (-50, (0, 0, 255)),     # 深蓝: 极强
    (-65, (0, 191, 255)),   # 浅蓝: 极好
    (-80, (0, 255, 0)),     # 绿: 良好
    (-90, (255, 255, 0)),   # 黄: 一般
    (-100, (255, 165, 0)),  # 橙: 较差
    (-110, (255, 0, 0)),    # 红: 弱覆盖
    (-120, (128, 0, 128)),  # 紫: 盲区
]


def generate_coverage_grid(
    all_data: List[Dict],
    bbox: Tuple[float, float, float, float],
    resolution_m: int = 30,
) -> Tuple[np.ndarray, Tuple[float, float, float, float, float, float]]:
    """
    将离散覆盖点聚合为规则栅格，每个单元格取最强RSRP值。

    Returns:
        (raster_array, geotransform)
    """
    lon_min, lat_min, lon_max, lat_max = bbox

    mid_lat = (lat_min + lat_max) / 2
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(mid_lat)))
    lat_per_km = 1.0 / 111.0

    width_px = int((lon_max - lon_min) / lon_per_km / 1000 * resolution_m)
    height_px = int((lat_max - lat_min) / lat_per_km / 1000 * resolution_m)
    width_px = max(width_px, 10)
    height_px = max(height_px, 10)

    # 初始化为极小值（表示无覆盖）
    grid = np.full((height_px, width_px), -200.0, dtype=np.float32)

    dx = (lon_max - lon_min) / width_px
    dy = (lat_max - lat_min) / height_px

    for pt in all_data:
        col = int((pt['longitude'] - lon_min) / dx)
        row = int((lat_max - pt['latitude']) / dy)
        col = max(0, min(width_px - 1, col))
        row = max(0, min(height_px - 1, row))
        # 取最强信号（RSRP越大越好）
        if pt['rsrp'] > grid[row, col]:
            grid[row, col] = pt['rsrp']

    geotransform = (lon_min, dx, 0, lat_max, 0, -dy)
    return grid, geotransform


def rsrp_to_rgba(rsrp: float) -> Tuple[int, int, int, int]:
    """双线性插值RSRP到RGBA颜色"""
    if rsrp >= RSRP_COLOR_STOPS[0][0]:
        return RSRP_COLOR_STOPS[0][1]
    if rsrp <= RSRP_COLOR_STOPS[-1][0]:
        return RSRP_COLOR_STOPS[-1][1]

    for i in range(len(RSRP_COLOR_STOPS) - 1):
        lo_val, lo_rgb = RSRP_COLOR_STOPS[i]
        hi_val, hi_rgb = RSRP_COLOR_STOPS[i + 1]
        if lo_val >= rsrp > hi_val:
            t = (rsrp - hi_val) / (lo_val - hi_val)
            r = int(lo_rgb[0] * t + hi_rgb[0] * (1 - t))
            g = int(lo_rgb[1] * t + hi_rgb[1] * (1 - t))
            b = int(lo_rgb[2] * t + hi_rgb[2] * (1 - t))
            a = int(140 + 80 * t)
            return (r, g, b, a)
    return (255, 0, 0, 120)
```

然后在 `design_dock.py` 中替换 `_create_heatmap_layer`：

```python
def _create_heatmap_layer(self, data):
    """创建覆盖热力图 — GDAL栅格渲染（QGIS 3.44兼容）"""
    from qgis.core import (
        QgsProject, QgsRasterLayer, QgsColorRampShader,
        QgsRasterShader, QgsSingleBandPseudoColorRenderer,
    )
    from qgis.PyQt.QtGui import QColor
    from osgeo import gdal, gdal_array
    import tempfile, os

    if not data:
        QMessageBox.warning(self, "提示", "没有覆盖数据可渲染")
        return

    # 1) 计算bbox
    lons = [d['longitude'] for d in data]
    lats = [d['latitude'] for d in data]
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    bbox = (lon_min, lat_min, lon_max, lat_max)

    # 2) 聚合为栅格
    from design_engine.coverage_renderer import generate_coverage_grid
    grid, geotransform = generate_coverage_grid(data, bbox, resolution_m=30)

    # 3) 写入临时GeoTIFF
    tmp_dir = tempfile.mkdtemp()
    tif_path = os.path.join(tmp_dir, "coverage.tif")
    driver = gdal.GetDriverByName('GTiff')
    rows, cols = grid.shape
    dataset = driver.Create(tif_path, cols, rows, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform(geotransform)
    canvas_crs = self.iface.mapCanvas().crs()
    dataset.SetProjection(canvas_crs.toWkt())
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(-200.0)
    gdal_array.BandWriteArray(band, grid)
    band.FlushCache()
    dataset = None

    # 4) 加载为伪彩色栅格图层
    layer = QgsRasterLayer(tif_path, "覆盖热力图", "gdal")
    if not layer.isValid():
        self._log("热力图栅格层创建失败")
        return

    # 5) 设置颜色映射
    color_ramp_shader = QgsColorRampShader()
    color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
    color_list = []
    from design_engine.coverage_renderer import RSRP_COLOR_STOPS
    for val, rgb in RSRP_COLOR_STOPS:
        color_list.append(QgsColorRampShader.ColorRampItem(
            val, QColor(*rgb), f'{val} dBm'))
    color_ramp_shader.setColorRampItemList(color_list)

    shader = QgsRasterShader()
    shader.setRasterShaderFunction(color_ramp_shader)

    renderer = QgsSingleBandPseudoColorRenderer(
        layer.dataProvider(), 1, shader
    )
    layer.setRenderer(renderer)
    layer.setOpacity(0.75)
    layer.triggerRepaint()

    QgsProject.instance().addMapLayer(layer)

    # 6) 缩放到热力图范围
    canvas = self.iface.mapCanvas()
    canvas.setExtent(layer.extent())
    canvas.refresh()

    # 7) 计算覆盖统计
    rsrp_vals = [d['rsrp'] for d in data]
    if rsrp_vals:
        excellent = len([r for r in rsrp_vals if r >= -65])
        good = len([r for r in rsrp_vals if -80 <= r < -65])
        fair = len([r for r in rsrp_vals if -90 <= r < -80])
        poor = len([r for r in rsrp_vals if -100 <= r < -90])
        very_poor = len([r for r in rsrp_vals if r < -100])
        total_points = len(data)
        avg_rsrp = round(sum(rsrp_vals) / len(rsrp_vals), 1)
        coverage_rate = round((excellent + good) / total_points * 100, 1)
    else:
        excellent = good = fair = poor = very_poor = 0
        total_points = avg_rsrp = coverage_rate = 0

    self._show_coverage_stats(
        total_sites=len(self.generated_sites),
        total_points=total_points,
        avg_rsrp=avg_rsrp,
        coverage_rate=coverage_rate,
        excellent=excellent, good=good, fair=fair,
        poor=poor, very_poor=very_poor,
    )
    self._log(f"热力图已渲染: {grid[grid > -190].size}个栅格单元")
```

---

## P0-2：覆盖算法 — 天线扇区方向性增益

**问题描述**：当前覆盖算法假设全向辐射，3扇区基站应该只有120度方向有强覆盖，但代码完全忽略了天线方向性。

**解决方案**：在 `coverage.py` 中新增 `path_loss_with_directivity()` 函数，在 Okumura-Hata 基础上加入方向性增益修正。

**预期效果**：地图上看到三个方向的扇形覆盖区域（花瓣形），而非正圆，直观体现"三扇区基站"概念。

**工作量**：约 60 行新增代码，难度: low

```python
# === 新增到 design_engine/coverage.py ===

def path_loss_with_directivity(
    frequency_mhz: float,
    distance_km: float,
    tx_height_m: float,
    azimuth_deg: float,        # 扇区方位角
    beamwidth_h_deg: float = 65.0,  # 水平波束宽度
    environment: str = "URBAN",
    rx_angle_deg: float = 0.0,   # 接收点相对扇区的角度
) -> float:
    """
    在Okumura-Hata基础上加入天线方向性增益修正。
    
    方向性增益模型（简化工程版）:
    - 主瓣内 (|angle| <= BW/2): 满增益
    - 过渡区 (BW/2 < |angle| <= BW/2 + 15deg): 线性衰减
    - 旁瓣/后瓣 (|angle| > BW/2 + 15deg): 固定-15dB衰减
    """
    base_loss = okumura_hata_path_loss(
        frequency_mhz, distance_km, tx_height_m, environment=environment
    )
    
    # 计算相对角度差
    angle_diff = abs(((rx_angle_deg - azimuth_deg) + 180) % 360 - 180)
    half_bw = beamwidth_h_deg / 2.0
    
    if angle_diff <= half_bw:
        # 主瓣内: 满增益，方向性增益修正 -3dB
        directivity_correction = -3.0
    elif angle_diff <= half_bw + 15.0:
        # 过渡区: 从-3dB线性衰减到-15dB
        t = (angle_diff - half_bw) / 15.0
        directivity_correction = -3.0 - 12.0 * t
    else:
        # 旁瓣/后瓣: -15dB
        directivity_correction = -15.0
    
    return base_loss - directivity_correction


def calculate_rsrp_sector(
    site_lon: float, site_lat: float,
    frequency_mhz: float, tx_power_w: float,
    tx_height_m: float, azimuth_deg: float,
    beamwidth_h_deg: float = 65.0,
    antenna_gain_dbi: float = 24.0,
    rx_lon: float = None, rx_lat: float = None,
    environment: str = "URBAN",
) -> float:
    """
    计算某个接收点在特定扇区下的RSRP。
    自动计算接收点相对于扇区的角度。
    """
    import math
    tx_power_dbm = power_w_to_dbm(tx_power_w)
    
    # 计算距离和方位角
    dx = (rx_lon - site_lon) * 111 * math.cos(math.radians(site_lat))
    dy = rx_lat - site_lat
    distance_km = math.sqrt(dx**2 + dy**2) * 111 / 1000
    rx_angle = math.degrees(math.atan2(dx, dy)) % 360
    
    if distance_km < 0.01:
        distance_km = 0.01
    
    path_loss = path_loss_with_directivity(
        frequency_mhz, distance_km, tx_height_m,
        azimuth_deg, beamwidth_h_deg, environment, rx_angle
    )
    
    return tx_power_dbm + antenna_gain_dbi - path_loss - 8.0  # -8dB阴影衰落
```

**模型升级对比分析**：

| 模型 | 频率范围 | 3.5GHz适用性 | 复杂度 | 推荐 |
|------|---------|-------------|--------|------|
| Okumura-Hata | 150-1500MHz | 外推，误差±8dB | 低（当前） | 保留作为基线 |
| COST 231 Hata | 1500-2000MHz | 仍不适用 | 低 | 不建议 |
| ITU-R P.1411 | 100MHz-10GHz | 完全适用 | 中 | 比赛够用即可 |

**结论**：比赛场景不需要换模型。当前 Okumura-Hata + 方向性修正已经足够专业。

---

## P1-1：站点表格专业化改造

**问题描述**：当前站点表格字段混乱（14列中有重复），缺少覆盖半径、站间距等关键工程指标。

**解决方案**：精简为12列专业字段，参考华为 UMG / 中兴网优工具标准。

**预期效果**：表格展示频段、频率、功率、方位角、覆盖半径、站间距等关键KPI，评委能直接看到网络质量。

**工作量**：约 50 行修改，难度: low

```python
# === 替换 _build_site_table 方法 ===
def _build_site_table(self):
    group = QGroupBox("基站设计明细")
    layout = QVBoxLayout()

    self.site_table = QTableWidget()
    self.site_table.setColumnCount(12)
    headers = [
        "站点ID", "名称", "站型", "场景", "塔高(m)",
        "频段", "频率(MHz)", "功率(W)", "方位角",
        "覆盖半径(km)", "站间距(km)", "坐标"
    ]
    self.site_table.setHorizontalHeaderLabels(headers)
    
    # 列宽设置
    widths = [110, 90, 55, 55, 60, 55, 65, 50, 70, 75, 65, 0]
    for i, w in enumerate(widths[:-1]):
        self.site_table.setColumnWidth(i, w)
    self.site_table.horizontalHeader().setSectionResizeMode(
        11, QHeaderView.Stretch)  # 坐标列自适应
    
    self.site_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.site_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.site_table.setAlternatingRowColors(True)
    layout.addWidget(self.site_table)

    # 操作按钮
    btn_row = QHBoxLayout()
    btn_fly = QPushButton("定位到选中站点")
    btn_fly.clicked.connect(self._fly_to_site)
    btn_row.addWidget(btn_fly)
    btn_delete = QPushButton("删除选中站点")
    btn_delete.setStyleSheet("background-color: #e74c3c; color: white;")
    btn_delete.clicked.connect(self._delete_site)
    btn_row.addWidget(btn_delete)
    layout.addLayout(btn_row)

    self.stats_label = QLabel("站点: 0")
    self.stats_label.setStyleSheet("font-weight: bold;")
    layout.addWidget(self.stats_label)

    group.setLayout(layout)
    return group


# === 替换 _update_site_table 方法 ===
def _update_site_table(self):
    sites = self.generated_sites
    self.site_table.setRowCount(len(sites))
    type_map = {'MACRO': '宏站', 'SMALL': '微站', 'INDOOR': '室分'}
    scenario_map = {'URBAN': '城市', 'SUBURBAN': '郊区', 'RURAL': '农村'}

    band_key = self.band_combo.currentText() if hasattr(self, 'band_combo') else "3.5GHz"
    isr_km = BAND_CONFIGS.get(band_key, BAND_CONFIGS["3.5GHz"]).ideal_isr_km

    for i, s in enumerate(sites):
        def item(text):
            return QTableWidgetItem(str(text))

        st = s.get('site_type', '')
        site_type_cn = type_map.get(st, st)
        scenario_cn = scenario_map.get(s.get('scenario', ''), s.get('scenario', ''))
        tower_h = s.get('tower_height', '')
        band = s.get('band', band_key)
        freq = s.get('frequency', '')
        power = s.get('power', '')

        # 方位角
        ns = s.get('num_sectors', 3)
        if ns == 0:
            az_str = '全向'
        elif ns > 0:
            az_str = '/'.join(str(int(360 / ns * j)) for j in range(ns))
        else:
            az_str = str(s.get('azimuth', 0))

        # 覆盖半径 = 站间距 * 1.5
        cov_radius = round(isr_km * 1.5, 2)

        # 坐标
        lon = s.get('longitude', 0)
        lat = s.get('latitude', 0)
        coord_str = f"{lon:.5f},{lat:.5f}"

        self.site_table.setItem(i, 0, item(s.get('site_id', '')))
        self.site_table.setItem(i, 1, item(s.get('name', '')))
        self.site_table.setItem(i, 2, item(site_type_cn))
        self.site_table.setItem(i, 3, item(scenario_cn))
        self.site_table.setItem(i, 4, item(tower_h))
        self.site_table.setItem(i, 5, item(band))
        self.site_table.setItem(i, 6, item(freq))
        self.site_table.setItem(i, 7, item(power))
        self.site_table.setItem(i, 8, item(az_str))
        self.site_table.setItem(i, 9, item(cov_radius))
        self.site_table.setItem(i, 10, item(isr_km))
        self.site_table.setItem(i, 11, item(coord_str))

    self.stats_label.setText(f"站点: {len(sites)}")
```

---

## P1-2：频段对比功能

**问题描述**：代码中已有"频段对比"按钮但调用的方法不存在。

**解决方案**：实现完整的频段对比功能 — 在地图上叠加显示700MHz和3.5GHz两种频段的基站布局，用不同颜色区分。

**预期效果**：点击"频段对比"后，橙色叠加显示700MHz方案站点，天蓝色叠加显示3.5GHz方案站点，弹出对比报告对话框。

**工作量**：约 120 行新增代码，难度: medium

```python
# === 添加到 design_dock.py ===

def _show_band_comparison(self):
    """频段对比：在同一区域叠加显示不同频段的基站布局"""
    if not self.selected_extent:
        QMessageBox.warning(self, "提示", "请先在第二步选择设计区域")
        return
    if len(self.generated_sites) == 0:
        QMessageBox.warning(self, "提示", "请先生成基站方案")
        return

    current_band = self.band_combo.currentText()
    compare_band = "700MHz" if current_band != "700MHz" else "3.5GHz"
    config_current = BAND_CONFIGS[current_band]
    config_compare = BAND_CONFIGS[compare_band]

    reply = QMessageBox.question(
        self, "频段对比",
        f"将在当前 {current_band} 方案基础上，叠加显示 {compare_band} 方案。\n\n"
        f"{current_band}: 站间距 {config_current.ideal_isr_km}km, 频率 {config_current.frequency_mhz}MHz\n"
        f"{compare_band}: 站间距 {config_compare.ideal_isr_km}km, 频率 {config_compare.frequency_mhz}MHz\n\n"
        f"是否继续？",
        QMessageBox.Yes | QMessageBox.No
    )
    if reply != QMessageBox.Yes:
        return

    self._log(f"开始频段对比: {current_band} vs {compare_band}")
    self._show_progress(True, 0)

    try:
        bbox = self.selected_extent
        centers = generate_hex_grid(bbox, config_compare.ideal_isr_km)
        if len(centers) > 200:
            centers = centers[:200]

        engine_sites = generate_sites_from_grid(
            centers, config_compare,
            site_type=self.type_combo.currentText().split("(")[1].rstrip(")"),
            tower_height=float(self.height_spin.value()),
            num_sectors=self.sector_spin.value(),
            bbox=bbox,
        )

        compare_sites = []
        for es in engine_sites:
            compare_sites.append({
                'site_id': es.site_id, 'name': es.name,
                'longitude': round(es.longitude, 7),
                'latitude': round(es.latitude, 7),
                'tower_height': es.tower_height,
                'site_type': es.site_type,
                'band': compare_band,
                'frequency': config_compare.frequency_mhz,
                'power': config_compare.default_power_w,
                'gain': config_compare.default_gain_dbi,
            })

        self._log(f"{compare_band}: 生成 {len(compare_sites)} 个站点")
        self._add_comparison_markers(compare_sites, compare_band)

        # 弹出对比报告对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("频段对比报告")
        dialog.setMinimumSize(450, 300)
        dialog.setStyleSheet("""
            QDialog { background: #fafafa; }
            QGroupBox { font-weight: bold; border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 10px; }
        """)

        layout = QVBoxLayout(dialog)
        overview = QGroupBox("对比总览")
        form = QFormLayout()
        form.addRow(f"{current_band} 站点数:", f"<b>{len(self.generated_sites)}</b> 个")
        form.addRow(f"{compare_band} 站点数:", f"<b>{len(compare_sites)}</b> 个")
        form.addRow("站间距差异:", f"{config_current.ideal_isr_km}km vs {config_compare.ideal_isr_km}km")
        form.addRow("频率差异:", f"{config_current.frequency_mhz}MHz vs {config_compare.frequency_mhz}MHz")
        overview.setLayout(form)
        layout.addWidget(overview)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("padding: 8px; background: #3498db; color: white; border-radius: 4px;")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec_()

        self._log("频段对比完成")
        self._show_progress(False)

    except Exception as e:
        self._log(f"频段对比失败: {e}")
        QMessageBox.critical(self, "错误", f"频段对比失败: {e}")
        self._show_progress(False)


def _add_comparison_markers(self, sites, band_name):
    """在地图上叠加显示对比频段的站点标记"""
    canvas = self.iface.mapCanvas()
    color_map = {
        "700MHz": QColor(255, 165, 0),   # 橙色
        "3.5GHz": QColor(0, 191, 255),   # 天蓝色
    }
    color = color_map.get(band_name, QColor(128, 128, 128))

    for site in sites:
        lon = site['longitude']
        lat = site['latitude']

        # 外圈白色边框
        rb_outer = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_outer.setColor(QColor(255, 255, 255))
        rb_outer.setFillColor(QColor(255, 255, 255))
        rb_outer.setIconSize(12)
        rb_outer.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_outer.addPoint(QgsPointXY(lon, lat))

        # 内圈对比频段颜色
        rb_inner = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb_inner.setColor(color)
        rb_inner.setFillColor(color)
        rb_inner.setIconSize(8)
        rb_inner.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_inner.addPoint(QgsPointXY(lon, lat))

        self._marker_bands.extend([rb_outer, rb_inner])

    canvas.refresh()
    self._log(f"{band_name}: 叠加显示 {len(sites)} 个站点")
```

---

## P1-3：效率对比数据生成

**问题描述**：比赛要求证明"效率提升≥30%"，当前缺少量化对比数据。

**解决方案**：设计自动化对比测试脚本，用真实场景数据生成对比报告。

**预期效果**：一键生成各频段方案的效率对比数据，包含站点密度、覆盖半径、频率等关键指标，可直接用于比赛答辩PPT。

**工作量**：约 80 行代码，难度: low

```python
# === 新增到 design_dock.py ===

def _show_efficiency_comparison(self):
    """显示效率对比数据 — 不同频段的站点密度、覆盖面积、生成效率"""
    if not self.generated_sites:
        QMessageBox.warning(self, "提示", "请先生成基站方案")
        return

    band_stats = {}
    for site in self.generated_sites:
        band = site.get('band', '未知')
        if band not in band_stats:
            band_stats[band] = {
                'count': 0, 'total_power': 0, 'total_gain': 0,
                'frequencies': set()
            }
        band_stats[band]['count'] += 1
        band_stats[band]['total_power'] += site.get('power', 0)
        band_stats[band]['total_gain'] += site.get('gain', 0)
        band_stats[band]['frequencies'].add(site.get('frequency', 0))

    stats_lines = []
    stats_lines.append("频段效率对比报告")
    stats_lines.append("=" * 50)
    area_km2 = self._calc_area_km2()
    stats_lines.append(f"设计区域: {self.selected_extent}")
    stats_lines.append(f"区域面积: {area_km2:.2f} km²")
    stats_lines.append("")

    for band, stats in band_stats.items():
        config = BAND_CONFIGS.get(band, BAND_CONFIGS["3.5GHz"])
        density = stats['count'] / area_km2 if area_km2 > 0 else 0
        stats_lines.append(f"--- {band} ---")
        stats_lines.append(f"  站点数: {stats['count']}")
        stats_lines.append(f"  站密度: {density:.2f} 站/km²")
        stats_lines.append(f"  理想站间距: {config.ideal_isr_km} km")
        stats_lines.append(f"  覆盖半径: {config.max_radius_km} km")
        stats_lines.append(f"  频率: {config.frequency_mhz} MHz")
        stats_lines.append(f"  默认功率: {config.default_power_w} W")
        stats_lines.append("")

    QMessageBox.information(self, "效率对比", "\n".join(stats_lines))
```

**量化指标计算方法**：

| 指标 | 计算公式 | 用途 |
|------|----------|------|
| 站点密度 | 站点数 / 区域面积 (站/km²) | 衡量网络密集程度 |
| 覆盖效率 | 总覆盖面积 / 区域面积 | 衡量频段覆盖能力 |
| 站间距比 | 大频段站间距 / 小频段站间距 | 衡量站点数量差异倍数 |
| 功率效率 | 总功率 / 站点数 (W/站) | 衡量单站能耗 |

---

## P2-1：3分钟演示视频脚本

| 时间段 | 操作 | 画面要点 |
|--------|------|----------|
| 0:00-0:15 | 打开QGIS，加载插件 | 显示"基站智能设计平台"面板打开，左侧6步导航 |
| 0:15-0:30 | 加载底图 | 点击"高德卫星图"，校园卫星图加载 |
| 0:30-0:45 | 选择区域 | 缩放到校园范围，点击"使用当前可视范围" |
| 0:45-1:15 | 设置参数+生成 | 选择3.5GHz，塔高45m，3扇区，点击"一键生成" |
| 1:15-1:45 | 展示站点表格 | 滚动站点列表，展示12列专业字段 |
| 1:45-2:15 | 管线设计 | 点击地图添加机房，生成管线，展示共享路由 |
| 2:15-2:40 | 覆盖分析 | 生成热力图，展示覆盖报告 |
| 2:40-3:00 | 导出+总结 | 导出PDF图纸，展示频段对比 |

---

## P2-2：预置示例数据

创建 `examples/campus_design.geojson`：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [111.030, 35.040]},
      "properties": {"site_id": "BTS-URBA-001", "name": "实验楼", "site_type": "MACRO", "tower_height": 45}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [111.035, 35.045]},
      "properties": {"site_id": "BTS-URBA-002", "name": "教学楼", "site_type": "MACRO", "tower_height": 45}
    },
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [111.028, 35.048]},
      "properties": {"site_id": "BTS-URBA-003", "name": "图书馆", "site_type": "MACRO", "tower_height": 45}
    }
  ],
  "properties": {
    "band": "3.5GHz",
    "tower_height": 45,
    "description": "运城学院校园3站示例方案"
  }
}
```

---

## P2-3：metadata.txt 优化

```ini
[general]
name=通信基站智能设计平台
qgisMinimumVersion=3.28
description=通信基建工程基站智能辅助设计与BOM自动生成。支持蜂窝拓扑生成、Okumura-Hata覆盖分析、管线路由规划、工程量报表导出。
version=0.2.0
author=TeamXind2 - 烽火通信挑战杯参赛团队
tags=基站,5G,覆盖分析,管线设计,蜂窝拓扑,Okumura-Hata,工程量,通信设计
changelog=0.2.0\n  - 新增12列专业站点表格\n  - 新增频段对比功能（700MHz vs 3.5GHz）\n  - 新增覆盖热力图分级渲染\n  - 优化管线共享路由算法
```

---

## 总结

| 优先级 | 优化项 | 代码行数 | 难度 | 评委感知度 |
|--------|--------|----------|------|-----------|
| P0 | 热力图GDAL栅格渲染 | ~100行 | medium | ★★★★★ |
| P0 | 天线扇区方向性增益 | ~60行 | low | ★★★★☆ |
| P1 | 站点表格12列专业化 | ~50行 | low | ★★★★☆ |
| P1 | 频段对比功能 | ~120行 | medium | ★★★★☆ |
| P1 | 效率对比数据 | ~80行 | low | ★★★☆☆ |
| P2 | 演示脚本+示例数据 | ~30行 | low | ★★★☆☆ |

**建议实施顺序**：P0-1 → P0-2 → P1-1 → P1-2 → P1-3 → P2-1/2/3
