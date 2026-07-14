# QGIS 通信基站智能设计插件

## 目录结构

```
qgis-plugin/
├── design_engine/     # 子赛题1：基站智能设计引擎（人A负责）
│   ├── hex_grid.py    # 蜂窝拓扑生成
│   ├── coverage.py    # 覆盖范围计算
│   ├── viewshed.py    # 视距分析
│   ├── avoidance.py   # 障碍物避让
│   ├── rules.py       # 工程规则配置
│   └── ml_recommender.py  # ML选址推荐
├── bom_generator/     # 子赛题4：BOM生成引擎（人B负责）
│   ├── extractors/    # 分类提取器（塔桅/天馈/电源/机柜/接地）
│   ├── bom_model.py   # BOM数据模型
│   ├── bom_exporter.py # 导出Excel/JSON
│   ├── bom_api.py     # 推送至M04
│   └── bom_dialog.py  # BOM预览编辑UI
├── models/            # 共享数据模型（人A定义，人B只读）
├── layers/            # QGIS图层管理（覆盖热力图/站点渲染）
├── resources/         # 图标、Layout模板、ML模型文件
└── tests/             # 单元测试

## 开发环境

- QGIS 3.34 LTR
- QGIS 自带 Python（由 QGIS 版本决定，独立于项目统一的 Python 3.10）
- 安装依赖: 运行 install_deps.bat
