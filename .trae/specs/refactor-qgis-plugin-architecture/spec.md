# QGIS 插件架构重构 Spec

## Why

`design_dock.py`（1092 行主面板）内联了蜂窝网格生成、覆盖计算、避让检测等全部算法逻辑，完全未调用已有的 `design_engine/` 模块。同时存在 6 个已编写但从未接入主流程的模块和 5 个已知 Bug。这些问题阻碍了后续管线/机房功能的扩展，并在演示中存在运行时崩溃风险。

## What Changes

- 修复 `design_engine/` 层 5 个已知 Bug
- 将 `design_dock.py` 中的内联算法代码替换为对 `design_engine/` 模块的调用
- 消除 `BAND_CONFIGS` 重复定义，统一引用 `design_engine/rules.py`
- 接入 `ui/basemap.py` 替换内联底图加载
- 接入 `ui/station_dialog.py` 替换内联手动添加站点
- 接入 `tools/station_tool.py` 替换内联 QgsMapToolEmitPoint
- **BREAKING**: `design_dock.py` 的内部方法签名将变化（仅影响插件内部，不影响外部接口）

## Impact

- Affected specs: 子赛题1 — 面向专业 GIS 平台的通信工程智能辅助设计
- Affected code:
  - `qgis-plugin/ui/design_dock.py` — 主要重构目标
  - `qgis-plugin/design_engine/hex_grid.py` — Bug 修复
  - `qgis-plugin/design_engine/avoidance.py` — Bug 修复
  - `qgis-plugin/design_engine/data_sync.py` — Bug 修复
  - `qgis-plugin/design_engine/coverage.py` — Bug 修复
  - `qgis-plugin/design_engine/coverage_heatmap.py` — Bug 修复
  - `qgis-plugin/ui/basemap.py` — 接入主流程
  - `qgis-plugin/ui/station_dialog.py` — 接入主流程
  - `qgis-plugin/tools/station_tool.py` — 接入主流程

## ADDED Requirements

### Requirement: UI 层调用设计引擎模块
`design_dock.py` SHALL 将所有算法逻辑委托给 `design_engine/` 下的对应模块，而非内联实现。

#### Scenario: 蜂窝拓扑生成使用引擎模块
- **WHEN** 用户设置参数并点击"生成蜂窝拓扑"
- **THEN** `design_dock.py` 调用 `design_engine.hex_grid.generate_hex_grid()` 和 `generate_sites_from_grid()`
- **AND** 不再存在内联的六边形网格生成代码

#### Scenario: 覆盖热力图使用引擎模块
- **WHEN** 用户点击"覆盖热力图"
- **THEN** `design_dock.py` 调用 `design_engine.coverage.generate_coverage_raster()` 和 `design_engine.coverage.rsrp_to_color()`
- **AND** 不再存在内联的 Okumura-Hata 计算代码

#### Scenario: 避让检测使用引擎模块
- **WHEN** 用户加载避让数据后生成拓扑
- **THEN** `design_dock.py` 通过 `design_engine.avoidance.AvoidanceChecker` 进行避让过滤
- **AND** 使用 Shapely 或 Fallback 双模式

#### Scenario: 底图加载使用 basemap 模块
- **WHEN** 用户点击"加载底图"按钮
- **THEN** 调用 `ui/basemap.py` 的 `add_gaode_satellite()` 或 `add_osm()`
- **AND** 不再存在内联的 XYZ 图层加载代码

#### Scenario: 手动添加站点使用 station_dialog
- **WHEN** 用户在地图上点击添加站点
- **THEN** 弹出 `ui/station_dialog.py` 的 `StationDialog` 对话框
- **AND** 用户可编辑站点名称、类型、塔高等参数

#### Scenario: 地图点击工具使用 station_tool
- **WHEN** 用户进入手动添加模式
- **THEN** 使用 `tools/station_tool.py` 的 `AddStationTool`
- **AND** 不再使用内联的 `QgsMapToolEmitPoint` 实例化

### Requirement: 统一频段配置
系统 SHALL 只在 `design_engine/rules.py` 的 `BAND_CONFIGS` 中定义频段参数，所有模块（包括 UI 层）统一引用该配置。

#### Scenario: UI 和引擎使用同一 BAND_CONFIGS
- **WHEN** `design_dock.py` 需要频段配置
- **THEN** 通过 `from design_engine.rules import BAND_CONFIGS` 引用
- **AND** 不再存在 `self.BAND_CONFIGS` 的重复定义

## MODIFIED Requirements

### Requirement: 蜂窝拓扑生成
原有的内联六边形网格生成逻辑替换为引擎调用。输入参数（bbox, isr_km）不变，输出格式（Site 列表）不变。用户体验完全一致。

### Requirement: 覆盖热力图
原有的内联 Okumura-Hata 覆盖计算替换为引擎调用。颜色映射（rsrp_to_color）逻辑不变。渲染方式（内存点图层 + 分类渲染器）不变。

## REMOVED Requirements

### Requirement: design_dock.py 内联 BAND_CONFIGS
**Reason**: 与 `design_engine/rules.py` 重复定义，且结构不同，容易导致参数不一致
**Migration**: 统一引用 `design_engine/rules.py` 中的 BAND_CONFIGS

### Requirement: design_dock.py 内联六边形网格生成
**Reason**: `design_engine/hex_grid.py` 已完整实现相同功能
**Migration**: 调用 `hex_grid.generate_hex_grid()` 和 `generate_sites_from_grid()`

### Requirement: design_dock.py 内联 Okumura-Hata 计算
**Reason**: `design_engine/coverage.py` 已完整实现
**Migration**: 调用 `coverage.generate_coverage_raster()` 和 `rsrp_to_color()`

### Requirement: design_dock.py 内联底图加载
**Reason**: `ui/basemap.py` 已实现 `add_gaode_satellite()` 和 `add_osm()`
**Migration**: 调用 basemap 模块函数

### Requirement: design_dock.py 内联站点工具实例化
**Reason**: `tools/station_tool.py` 已实现 `AddStationTool`
**Migration**: 使用 `AddStationTool` 替代直接 `QgsMapToolEmitPoint`

## Bug Fixes

### Bug-1: hex_grid.py rotation_deg 未实现
**File**: `design_engine/hex_grid.py` L13
**Issue**: `generate_hex_grid()` 接收 `rotation_deg` 参数但函数体未使用
**Fix**: 实现网格旋转逻辑（或移除该参数并标记 TODO）

### Bug-2: avoidance.py MultiPolygon 处理错误
**File**: `design_engine/avoidance.py` L124-128
**Issue**: `_extract_coords()` 将多个 polygon 坐标合并成一个列表，创建无效几何
**Fix**: 分别提取每个子多边形的坐标

### Bug-3: data_sync.py validSites 统计不准确
**File**: `design_engine/data_sync.py` L50
**Issue**: `validSites = len(sites), invalidSites = 0` 忽略了无效站点
**Fix**: 使用 `avoidance_checker` 统计有效/无效站点数量

### Bug-4: coverage_heatmap.py setRanges() API 不存在
**File**: `design_engine/coverage_heatmap.py` L179
**Issue**: `renderer.setRanges(ranges)` 不是 QGIS 标准 API
**Fix**: 使用 `renderer.addClassRange()` 或 `QgsGraduatedSymbolRenderer.createRenderer()`

### Bug-5: coverage.py calculate_coverage_rate() 硬编码分辨率
**File**: `design_engine/coverage.py` L215-216
**Issue**: `point_area_km2 = (50 / 1000) ** 2` 硬编码 50m
**Fix**: 接受 `resolution_m` 参数
