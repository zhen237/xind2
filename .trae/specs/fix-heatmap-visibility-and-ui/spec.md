# 热力图可见性优化 + 框选边框 + PDF导出增强 + 日志前缀 Spec

## Why

热力图虽然在图层面板显示，但地图上点太小（size=2）几乎看不见。框选区域有红色半透明填充遮挡底图。PDF导出的地图内容不够明显。用户要求所有日志消息前加"哥哥"前缀。

## What Changes

- 增大热力图点符号尺寸（size: 2 → 6），添加边框以增强可见性
- 框选区域橡皮筋改为纯边框（无填充）
- PDF导出改为使用 `layout_export.py` 的标准导出模块（含图例、比例尺、指北针）
- 所有 `_log()` 调用前自动添加"哥哥"前缀

## Impact

- Affected code: `qgis-plugin/ui/design_dock.py`

## MODIFIED Requirements

### Requirement: 覆盖热力图渲染

热力图点符号尺寸从 2 增大到 6，添加半透明边框以在底图上清晰可见。

#### Scenario: 热力图在地图上可见
- **WHEN** 用户生成覆盖热力图
- **THEN** 热力图点在地图上清晰可见，颜色分级明显

### Requirement: 框选区域显示

框选橡皮筋改为纯边框样式，不遮挡底图。

#### Scenario: 框选区域只有边框
- **WHEN** 用户选择设计区域
- **THEN** 橡皮筋只显示红色边框，无填充色

### Requirement: PDF导出增强

PDF导出改为使用 `design_engine/layout_export.py` 的标准导出模块，自动包含图例、比例尺、指北针。

#### Scenario: PDF导出包含完整信息
- **WHEN** 用户导出PDF
- **THEN** PDF包含标题、信息框、地图、图例、比例尺、指北针

### Requirement: 日志前缀

所有 `_log()` 方法输出的消息前自动添加"哥哥"前缀。

#### Scenario: 日志消息带前缀
- **WHEN** 任何操作触发日志
- **THEN** 日志文本显示为 "哥哥: {原始文本}"
