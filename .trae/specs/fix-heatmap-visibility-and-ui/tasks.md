# Tasks

- [x] Task 1: 增大热力图点符号尺寸 — `_create_heatmap_layer` 中 `size: '2'` 改为 `size: '6'`，添加半透明边框
- [x] Task 2: 框选区域改为纯边框 — `_add_extent_rubber` 中 `setFillColor` 改为完全透明
- [x] Task 3: PDF导出改为使用 layout_export 标准模块
  - [x] SubTask 3.1: 添加 `from design_engine.layout_export import create_design_layout, add_map_to_layout, add_title_to_layout, add_info_box_to_layout, add_legend_to_layout, add_scale_bar_to_layout, add_north_arrow_to_layout, export_layout_to_pdf`
  - [x] SubTask 3.2: 重写 `_export_pdf` 方法，使用标准导出模块的函数组合
- [x] Task 4: 日志前缀 — `_log` 方法中自动添加"哥哥: "前缀

# Task Dependencies
- Task 1-4 无互相依赖，可并行
