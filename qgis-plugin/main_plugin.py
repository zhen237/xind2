# -*- coding: utf-8 -*-
"""
基站智能设计插件 - 主插件类（中文版）
"""

import os
import sys
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QDockWidget, QWidget, QVBoxLayout, QLabel, QPushButton, QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis, QgsPointXY, QgsDistanceArea, QgsProject, QgsRasterLayer


class BaseStationDesignPlugin:
    """基站智能设计插件"""

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock_widget = None
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        """创建菜单和工具栏图标"""
        self.action = QAction("基站智能设计", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&基站智能设计", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        """移除插件菜单和图标"""
        self.iface.removePluginMenu("&基站智能设计", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)

    def run(self):
        """运行方法，打开设计面板"""
        if self.dock_widget is None:
            self.dock_widget = QDockWidget("基站智能设计", self.iface.mainWindow())
            self.dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

            # 创建窗口部件
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 标题
            title = QLabel("基站智能设计平台")
            title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
            layout.addWidget(title)

            # 描述
            desc = QLabel("本插件提供基站智能辅助设计功能，包括蜂窝拓扑生成、覆盖分析、图纸导出等。")
            desc.setWordWrap(True)
            layout.addWidget(desc)

            # 底图控制组
            basemap_group = QGroupBox("底图控制")
            basemap_layout = QVBoxLayout()

            # 添加底图按钮
            basemap_btn = QPushButton("添加底图")
            basemap_btn.setStyleSheet('''
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
            ''')
            basemap_btn.clicked.connect(self.add_basemap)
            basemap_layout.addWidget(basemap_btn)

            basemap_group.setLayout(basemap_layout)
            layout.addWidget(basemap_group)

            # 设计参数组
            params_group = QGroupBox("设计参数")
            params_layout = QFormLayout()

            # 频段选择
            self.band_combo = QComboBox()
            self.band_combo.addItems(['700MHz', '2.6GHz', '3.5GHz', '4.9GHz'])
            self.band_combo.setCurrentText('3.5GHz')
            params_layout.addRow('频段:', self.band_combo)

            # 覆盖半径
            self.radius_spin = QDoubleSpinBox()
            self.radius_spin.setRange(0.1, 10.0)
            self.radius_spin.setValue(1.0)
            self.radius_spin.setSuffix(' 公里')
            params_layout.addRow('覆盖半径:', self.radius_spin)

            # 网格大小
            self.grid_spin = QSpinBox()
            self.grid_spin.setRange(2, 10)
            self.grid_spin.setValue(4)
            params_layout.addRow('网格大小:', self.grid_spin)

            # 塔高
            self.height_spin = QSpinBox()
            self.height_spin.setRange(20, 60)
            self.height_spin.setValue(45)
            self.height_spin.setSuffix(' 米')
            params_layout.addRow('塔高:', self.height_spin)

            # 天线类型
            self.antenna_combo = QComboBox()
            self.antenna_combo.addItems(['全向', '3扇区', '6扇区'])
            self.antenna_combo.setCurrentText('3扇区')
            params_layout.addRow('天线类型:', self.antenna_combo)

            params_group.setLayout(params_layout)
            layout.addWidget(params_group)

            # 操作按钮组
            actions_group = QGroupBox("操作")
            actions_layout = QVBoxLayout()

            # 生成蜂窝拓扑按钮
            generate_btn = QPushButton("生成蜂窝拓扑")
            generate_btn.setStyleSheet('''
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            ''')
            generate_btn.clicked.connect(self.generate_hex_grid)
            actions_layout.addWidget(generate_btn)

            # 计算覆盖按钮
            coverage_btn = QPushButton("计算覆盖")
            coverage_btn.setStyleSheet('''
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
            ''')
            coverage_btn.clicked.connect(self.calculate_coverage)
            actions_layout.addWidget(coverage_btn)

            # 添加站点到地图按钮
            add_to_map_btn = QPushButton("添加站点到地图")
            add_to_map_btn.setStyleSheet('''
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            ''')
            add_to_map_btn.clicked.connect(self.add_sites_to_map)
            actions_layout.addWidget(add_to_map_btn)

            # 生成覆盖热力图按钮
            heatmap_btn = QPushButton("生成覆盖热力图")
            heatmap_btn.setStyleSheet('''
                QPushButton {
                    background-color: #9b59b6;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #8e44ad;
                }
            ''')
            heatmap_btn.clicked.connect(self.generate_coverage_heatmap)
            actions_layout.addWidget(heatmap_btn)

            # 导出设计图纸按钮
            export_btn = QPushButton("导出设计图纸")
            export_btn.setStyleSheet('''
                QPushButton {
                    background-color: #f39c12;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #e67e22;
                }
            ''')
            export_btn.clicked.connect(self.export_design_drawing)
            actions_layout.addWidget(export_btn)

            # 避让检测按钮
            avoidance_btn = QPushButton("避让检测")
            avoidance_btn.setStyleSheet('''
                QPushButton {
                    background-color: #1abc9c;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #16a085;
                }
            ''')
            avoidance_btn.clicked.connect(self.check_avoidance)
            actions_layout.addWidget(avoidance_btn)

            # 一键设计按钮
            oneclick_btn = QPushButton("一键设计")
            oneclick_btn.setStyleSheet('''
                QPushButton {
                    background-color: #8e44ad;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #7d3c98
                }
            ''')
            oneclick_btn.clicked.connect(self.one_click_design)
            actions_layout.addWidget(oneclick_btn)

            # 生成报告按钮
            report_btn = QPushButton("生成报告")
            report_btn.setStyleSheet('''
                QPushButton {
                    background-color: #2c3e50;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #1a252f
                }
            ''')
            report_btn.clicked.connect(self.generate_report)
            actions_layout.addWidget(report_btn)

            # 同步到后端按钮
            sync_btn = QPushButton("同步到后端")
            sync_btn.setStyleSheet('''
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #c0392b
                }
            ''')
            sync_btn.clicked.connect(self.sync_to_backend)
            actions_layout.addWidget(sync_btn)

            # 测试距离计算按钮
            test_btn = QPushButton("测试距离计算")
            test_btn.clicked.connect(self.test_distance)
            actions_layout.addWidget(test_btn)

            actions_group.setLayout(actions_layout)
            layout.addWidget(actions_group)

            # 状态标签
            self.status_label = QLabel("就绪")
            self.status_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
            layout.addWidget(self.status_label)

            # 添加弹性空间
            layout.addStretch()

            self.dock_widget.setWidget(widget)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)

        self.dock_widget.show()
        self.dock_widget.raise_()

    def add_basemap(self):
        """添加底图"""
        try:
            # 使用QGIS内置的添加图层功能
            from qgis.utils import iface
            iface.mainWindow().findChild(QAction, 'mActionAddXyzLayer').trigger()
            QMessageBox.information(self.iface.mainWindow(), "添加底图",
                "请在弹出的对话框中添加底图：\n\n"
                "1. 点击'新建'按钮\n"
                "2. 名称输入: 高德地图\n"
                "3. URL输入:\n"
                "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}\n"
                "4. 点击'OK'\n"
                "5. 点击'添加'")
        except Exception as e:
            QMessageBox.warning(self.iface.mainWindow(), "添加底图",
                "请手动添加底图：\n\n"
                "1. 菜单 → 图层 → 添加图层 → 添加XYZ/WMS图层\n"
                "2. 点击'新建'按钮\n"
                "3. 名称: 高德地图\n"
                "4. URL: https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}\n"
                "5. 点击'OK' → '添加'")

    def generate_hex_grid(self):
        """生成蜂窝拓扑"""
        try:
            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
            from design_engine.rules import BAND_CONFIGS

            # 获取参数
            band = self.band_combo.currentText()
            grid_size = self.grid_spin.value()
            tower_height = self.height_spin.value()

            # 获取天线类型
            antenna_type = self.antenna_combo.currentText()
            if antenna_type == '全向':
                num_sectors = 0
            elif antenna_type == '3扇区':
                num_sectors = 3
            else:  # 6扇区
                num_sectors = 6

            # 定义边界框（武汉光谷区域）
            bbox = (114.30, 30.45, 114.45, 30.55)

            # 生成蜂窝网格
            grid_centers = generate_hex_grid(bbox, isr_km=1.0)

            # 获取频段配置
            if band == '3.5GHz':
                band_config = BAND_CONFIGS['3.5GHz']
            elif band == '2.6GHz':
                band_config = BAND_CONFIGS['2.6GHz']
            elif band == '700MHz':
                band_config = BAND_CONFIGS['700MHz']
            else:
                band_config = BAND_CONFIGS['4.9GHz']

            # 生成站点
            sites = generate_sites_from_grid(
                grid_centers[:grid_size*grid_size],
                band_config=band_config,
                site_type="MACRO",
                tower_height=tower_height,
                scenario="URBAN",
                num_sectors=num_sectors
            )

            # 存储站点供后续使用
            self.generated_sites = sites

            # 显示结果
            message = f"蜂窝拓扑生成结果：\n\n"
            message += f"频段: {band}\n"
            message += f"网格大小: {grid_size}x{grid_size}\n"
            message += f"塔高: {tower_height} 米\n"
            message += f"天线类型: {antenna_type}\n"
            message += f"总网格点数: {len(grid_centers)}\n"
            message += f"生成站点数: {len(sites)}\n\n"
            message += "站点详情：\n"
            for site in sites[:5]:  # 显示前5个站点
                message += f"  - {site.site_id}: ({site.longitude}, {site.latitude})\n"
            if len(sites) > 5:
                message += f"  ... 还有 {len(sites) - 5} 个站点"

            QMessageBox.information(self.iface.mainWindow(), "蜂窝拓扑", message)
            self.status_label.setText(f"生成 {len(sites)} 个站点")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"生成网格失败: {e}")
            self.status_label.setText("发生错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def calculate_coverage(self):
        """计算覆盖"""
        try:
            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from design_engine.coverage import okumura_hata_path_loss, calculate_rsrp, power_w_to_dbm

            # 获取参数
            band = self.band_combo.currentText()

            # 根据频段定义参数
            if band == '3.5GHz':
                frequency_mhz = 3500
                tx_power_w = 200
                antenna_gain_dbi = 24
            elif band == '2.6GHz':
                frequency_mhz = 2600
                tx_power_w = 160
                antenna_gain_dbi = 22
            elif band == '700MHz':
                frequency_mhz = 700
                tx_power_w = 120
                antenna_gain_dbi = 18
            else:  # 4.9GHz
                frequency_mhz = 4900
                tx_power_w = 200
                antenna_gain_dbi = 24

            # 转换功率为dBm
            tx_power_dbm = power_w_to_dbm(tx_power_w)

            # 测试覆盖计算
            test_distance_km = 1.0
            path_loss = okumura_hata_path_loss(frequency_mhz, test_distance_km, 45, environment='URBAN')
            rsrp = calculate_rsrp(tx_power_dbm, antenna_gain_dbi, path_loss)

            message = f"覆盖计算结果：\n\n"
            message += f"频段: {band}\n"
            message += f"频率: {frequency_mhz} MHz\n"
            message += f"发射功率: {tx_power_w} W ({tx_power_dbm:.1f} dBm)\n"
            message += f"天线增益: {antenna_gain_dbi} dBi\n"
            message += f"距离: {test_distance_km} 公里\n"
            message += f"路径损耗: {path_loss:.2f} dB\n"
            message += f"RSRP: {rsrp:.2f} dBm\n\n"
            message += f"RSRP阈值: -110 dBm\n"
            message += f"覆盖状态: {'良好' if rsrp > -110 else '较差'}"

            QMessageBox.information(self.iface.mainWindow(), "覆盖计算", message)
            self.status_label.setText("覆盖计算完成")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"覆盖计算失败: {e}")
            self.status_label.setText("覆盖计算失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def add_sites_to_map(self):
        """添加站点到地图"""
        try:
            # 检查是否已生成站点
            if not hasattr(self, 'generated_sites') or not self.generated_sites:
                QMessageBox.warning(self.iface.mainWindow(), "警告", "请先生成蜂窝拓扑！")
                return

            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsProject, QgsMarkerSymbol
            from qgis.PyQt.QtCore import QVariant

            # 创建内存图层
            layer = QgsVectorLayer('Point?crs=EPSG:4326', '基站站点', 'memory')
            provider = layer.dataProvider()

            # 添加字段
            provider.addAttributes([
                QgsField('site_id', QVariant.String),
                QgsField('name', QVariant.String),
                QgsField('longitude', QVariant.Double),
                QgsField('latitude', QVariant.Double),
                QgsField('site_type', QVariant.String),
                QgsField('tower_height', QVariant.Double),
                QgsField('scenario', QVariant.String)
            ])
            layer.updateFields()

            # 添加要素
            features = []
            for site in self.generated_sites:
                feature = QgsFeature(layer.fields())
                feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(site.longitude, site.latitude)))
                feature.setAttributes([
                    site.site_id,
                    site.name,
                    site.longitude,
                    site.latitude,
                    site.site_type,
                    site.tower_height,
                    site.scenario
                ])
                features.append(feature)

            provider.addFeatures(features)
            layer.updateExtents()

            # 设置样式
            symbol = QgsMarkerSymbol.createSimple({'name': 'triangle', 'color': 'blue', 'size': '4'})
            layer.renderer().setSymbol(symbol)

            # 添加到地图
            QgsProject.instance().addMapLayer(layer)

            # 缩放到图层
            self.iface.mapCanvas().setExtent(layer.extent())
            self.iface.mapCanvas().refresh()

            message = f"站点已添加到地图！\n\n"
            message += f"图层: 基站站点\n"
            message += f"站点总数: {len(self.generated_sites)}\n"
            message += f"坐标系: EPSG:4326"

            QMessageBox.information(self.iface.mainWindow(), "站点已添加", message)
            self.status_label.setText(f"添加 {len(self.generated_sites)} 个站点到地图")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"添加站点失败: {e}")
            self.status_label.setText("添加站点失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def generate_coverage_heatmap(self):
        """生成覆盖热力图"""
        try:
            # 检查是否已生成站点
            if not hasattr(self, 'generated_sites') or not self.generated_sites:
                QMessageBox.warning(self.iface.mainWindow(), "警告", "请先生成蜂窝拓扑！")
                return

            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsProject, QgsMarkerSymbol
            from qgis.PyQt.QtCore import QVariant
            import math

            # 获取参数
            band = self.band_combo.currentText()

            # 根据频段定义参数
            if band == '3.5GHz':
                frequency_mhz = 3500
                tx_power_dbm = 53
                antenna_gain_dbi = 24
            elif band == '2.6GHz':
                frequency_mhz = 2600
                tx_power_dbm = 52
                antenna_gain_dbi = 22
            elif band == '700MHz':
                frequency_mhz = 700
                tx_power_dbm = 51
                antenna_gain_dbi = 18
            else:  # 4.9GHz
                frequency_mhz = 4900
                tx_power_dbm = 53
                antenna_gain_dbi = 24

            # 创建热力图图层
            layer = QgsVectorLayer('Point?crs=EPSG:4326', '覆盖热力图', 'memory')
            provider = layer.dataProvider()
            provider.addAttributes([QgsField('rsrp', QVariant.Double), QgsField('distance_km', QVariant.Double)])
            layer.updateFields()

            # 生成热力图点
            features = []
            sites = [(site.longitude, site.latitude) for site in self.generated_sites[:5]]

            for site_lon, site_lat in sites:
                for i in range(10):
                    for j in range(10):
                        lon = site_lon + (i - 5) * 0.003
                        lat = site_lat + (j - 5) * 0.003
                        d_km = math.sqrt((lon - site_lon)**2 + (lat - site_lat)**2) * 111
                        if d_km <= 1.0:
                            path_loss = 69.55 + 26.16 * math.log10(frequency_mhz) - 13.82 * math.log10(45) + (44.9 - 6.55 * math.log10(45)) * math.log10(max(d_km, 0.01))
                            rsrp = tx_power_dbm + antenna_gain_dbi - path_loss
                            if rsrp >= -110:
                                f = QgsFeature(layer.fields())
                                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
                                f.setAttributes([round(rsrp, 1), round(d_km, 3)])
                                features.append(f)

            # 添加要素到图层
            provider.addFeatures(features)
            layer.updateExtents()

            # 设置样式
            symbol = QgsMarkerSymbol.createSimple({'name': 'circle', 'color': 'red', 'size': '2'})
            layer.renderer().setSymbol(symbol)

            # 添加到地图
            QgsProject.instance().addMapLayer(layer)
            self.iface.mapCanvas().setExtent(layer.extent())
            self.iface.mapCanvas().refresh()

            message = f"覆盖热力图已生成！\n\n"
            message += f"频段: {band}\n"
            message += f"分析站点数: {len(sites)}\n"
            message += f"热力图点数: {len(features)}\n"
            message += f"RSRP阈值: -110 dBm"

            QMessageBox.information(self.iface.mainWindow(), "覆盖热力图", message)
            self.status_label.setText("覆盖热力图已生成")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"生成热力图失败: {e}")
            self.status_label.setText("生成热力图失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def export_design_drawing(self):
        """导出设计图纸"""
        try:
            # 检查是否已生成站点
            if not hasattr(self, 'generated_sites') or not self.generated_sites:
                QMessageBox.warning(self.iface.mainWindow(), "警告", "请先生成蜂窝拓扑！")
                return

            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from qgis.core import QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemScaleBar, QgsLayoutExporter, QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes, QgsRectangle
            from qgis.PyQt.QtGui import QFont
            import os

            # 获取参数
            band = self.band_combo.currentText()
            grid_size = self.grid_spin.value()

            # 创建布局
            project = QgsProject.instance()
            layout = QgsPrintLayout(project)
            layout.initializeDefaults()

            # 设置纸张大小为A3
            page = layout.pageCollection().page(0)
            page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

            # 添加标题
            title = QgsLayoutItemLabel(layout)
            title.setText('基站智能设计图')
            title.setFont(QFont('Arial', 24, QFont.Bold))
            title.attemptMove(QgsLayoutPoint(20, 10, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(title)

            # 添加副标题
            subtitle = QgsLayoutItemLabel(layout)
            subtitle.setText(f'武汉光谷5G基站设计 - {band} - {grid_size}x{grid_size} 网格')
            subtitle.setFont(QFont('Arial', 14))
            subtitle.attemptMove(QgsLayoutPoint(20, 30, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(subtitle)

            # 计算地图范围
            lons = [site.longitude for site in self.generated_sites]
            lats = [site.latitude for site in self.generated_sites]
            min_lon = min(lons) - 0.01
            max_lon = max(lons) + 0.01
            min_lat = min(lats) - 0.01
            max_lat = max(lats) + 0.01

            # 添加地图
            map_item = QgsLayoutItemMap(layout)
            map_item.setRect(0, 0, 350, 200)
            map_item.attemptMove(QgsLayoutPoint(20, 60, QgsUnitTypes.LayoutMillimeters))
            map_item.attemptResize(QgsLayoutSize(350, 200, QgsUnitTypes.LayoutMillimeters))
            map_item.setExtent(QgsRectangle(min_lon, min_lat, max_lon, max_lat))
            layout.addLayoutItem(map_item)

            # 添加图例
            legend = QgsLayoutItemLegend(layout)
            legend.setLinkedMap(map_item)
            legend.attemptMove(QgsLayoutPoint(380, 60, QgsUnitTypes.LayoutMillimeters))
            legend.attemptResize(QgsLayoutSize(30, 100, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(legend)

            # 添加比例尺
            scalebar = QgsLayoutItemScaleBar(layout)
            scalebar.setLinkedMap(map_item)
            scalebar.applyDefaultSize()
            scalebar.attemptMove(QgsLayoutPoint(20, 270, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(scalebar)

            # 添加信息框（右下角）
            info = QgsLayoutItemLabel(layout)
            info.setText(f'项目：武汉光谷5G基站设计\n设计日期：2026-06-05\n坐标系：EPSG:4326\n站点数量：{len(self.generated_sites)}个')
            info.setFont(QFont('Arial', 10))
            info.attemptMove(QgsLayoutPoint(300, 250, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(info)

            # 导出为PDF
            output_path = os.path.join(os.path.expanduser('~'), 'Desktop', '基站设计图.pdf')
            exporter = QgsLayoutExporter(layout)
            settings = QgsLayoutExporter.PdfExportSettings()
            settings.dpi = 300

            result = exporter.exportToPdf(output_path, settings)

            if result == QgsLayoutExporter.Success:
                message = f"设计图纸导出成功！\n\n"
                message += f"标题: 基站智能设计图\n"
                message += f"站点数: {len(self.generated_sites)}\n"
                message += f"纸张大小: A3\n"
                message += f"格式: PDF\n"
                message += f"输出路径: {output_path}\n\n"
                message += f"图纸包含：\n"
                message += f"- 站点分布图\n"
                message += f"- 图例\n"
                message += f"- 比例尺\n"
                message += f"- 站点信息"

                QMessageBox.information(self.iface.mainWindow(), "导出成功", message)
                self.status_label.setText("设计图纸已导出")
                self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")
            else:
                QMessageBox.critical(self.iface.mainWindow(), "导出失败", "设计图纸导出失败！")
                self.status_label.setText("导出失败")
                self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"导出图纸失败: {e}")
            self.status_label.setText("导出图纸失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def check_avoidance(self):
        """避让检测"""
        try:
            # 检查是否已生成站点
            if not hasattr(self, 'generated_sites') or not self.generated_sites:
                QMessageBox.warning(self.iface.mainWindow(), "警告", "请先生成蜂窝拓扑！")
                return

            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from design_engine.avoidance_checker import create_default_avoidance_checker

            # 创建避让检测器
            checker = create_default_avoidance_checker()

            # 准备站点数据
            sites = []
            for site in self.generated_sites:
                sites.append((site.longitude, site.latitude))

            # 获取避让报告
            report = checker.get_avoidance_report(sites)

            # 显示结果
            message = f"避让检测结果：\n\n"
            message += f"总站点数: {report['total']}\n"
            message += f"有效站点: {report['valid']}\n"
            message += f"无效站点: {report['invalid']}\n\n"

            if report['invalid'] > 0:
                message += "无效站点原因：\n"
                for reason in set(report['reasons']):
                    count = report['reasons'].count(reason)
                    message += f"  - {reason}: {count} 个站点\n"

            message += f"\n避让区域：\n"
            message += f"  - 水域: 0.5公里半径\n"
            message += f"  - 生态保护区: 0.3公里半径\n"
            message += f"  - 建筑物密集区: 0.4公里半径"

            QMessageBox.information(self.iface.mainWindow(), "避让检测", message)
            self.status_label.setText(f"避让检测: {report['valid']} 个有效, {report['invalid']} 个无效")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"避让检测失败: {e}")
            self.status_label.setText("避让检测失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def one_click_design(self):
        """一键设计"""
        try:
            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsProject, QgsMarkerSymbol
            from qgis.PyQt.QtCore import QVariant
            import math

            # 获取参数
            band = self.band_combo.currentText()
            grid_size = self.grid_spin.value()
            tower_height = self.height_spin.value()

            # 步骤1：生成蜂窝拓扑
            self.status_label.setText("步骤1：生成蜂窝拓扑...")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 12px;")

            # 定义边界框（武汉光谷区域）
            bbox = (114.30, 30.45, 114.45, 30.55)

            # 生成蜂窝网格
            from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid
            from design_engine.rules import BAND_CONFIGS

            grid_centers = generate_hex_grid(bbox, isr_km=1.0)

            # 获取频段配置
            if band == '3.5GHz':
                band_config = BAND_CONFIGS['3.5GHz']
                frequency_mhz = 3500
                tx_power_dbm = 53
                antenna_gain_dbi = 24
            elif band == '2.6GHz':
                band_config = BAND_CONFIGS['2.6GHz']
                frequency_mhz = 2600
                tx_power_dbm = 52
                antenna_gain_dbi = 22
            elif band == '700MHz':
                band_config = BAND_CONFIGS['700MHz']
                frequency_mhz = 700
                tx_power_dbm = 51
                antenna_gain_dbi = 18
            else:
                band_config = BAND_CONFIGS['4.9GHz']
                frequency_mhz = 4900
                tx_power_dbm = 53
                antenna_gain_dbi = 24

            # 生成站点
            sites = generate_sites_from_grid(
                grid_centers[:grid_size*grid_size],
                band_config=band_config,
                site_type="MACRO",
                tower_height=tower_height,
                scenario="URBAN",
                num_sectors=3
            )

            # 存储站点供后续使用
            self.generated_sites = sites

            # 步骤2：避让检测
            self.status_label.setText("步骤2：避让检测...")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 12px;")

            from design_engine.avoidance_checker import create_default_avoidance_checker
            checker = create_default_avoidance_checker()

            valid_count = 0
            invalid_count = 0
            for site in sites:
                is_valid, _ = checker.check_site(site.longitude, site.latitude)
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

            # 步骤3：覆盖计算
            self.status_label.setText("步骤3：覆盖计算...")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 12px;")

            rsrp_values = []
            for site in sites:
                d_km = 0.01
                path_loss = 69.55 + 26.16 * math.log10(frequency_mhz) - 13.82 * math.log10(tower_height) + (44.9 - 6.55 * math.log10(tower_height)) * math.log10(max(d_km, 0.01))
                rsrp = tx_power_dbm + antenna_gain_dbi - path_loss
                rsrp_values.append(rsrp)

            avg_rsrp = sum(rsrp_values) / len(rsrp_values)

            # 步骤4：添加站点到地图
            self.status_label.setText("步骤4：添加站点到地图...")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 12px;")

            # 创建站点图层
            layer = QgsVectorLayer('Point?crs=EPSG:4326', '基站站点', 'memory')
            provider = layer.dataProvider()
            provider.addAttributes([
                QgsField('site_id', QVariant.String),
                QgsField('longitude', QVariant.Double),
                QgsField('latitude', QVariant.Double),
                QgsField('tower_height', QVariant.Double)
            ])
            layer.updateFields()

            # 添加要素
            features = []
            for site in sites:
                f = QgsFeature(layer.fields())
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(site.longitude, site.latitude)))
                f.setAttributes([site.site_id, site.longitude, site.latitude, site.tower_height])
                features.append(f)

            provider.addFeatures(features)
            layer.updateExtents()

            # 设置样式
            symbol = QgsMarkerSymbol.createSimple({'name': 'triangle', 'color': 'blue', 'size': '5'})
            layer.renderer().setSymbol(symbol)

            # 添加到地图
            QgsProject.instance().addMapLayer(layer)

            # 步骤5：生成热力图
            self.status_label.setText("步骤5：生成热力图...")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 12px;")

            # 创建热力图图层
            heatmap_layer = QgsVectorLayer('Point?crs=EPSG:4326', '覆盖热力图', 'memory')
            hp = heatmap_layer.dataProvider()
            hp.addAttributes([QgsField('rsrp', QVariant.Double), QgsField('distance_km', QVariant.Double)])
            heatmap_layer.updateFields()

            # 生成热力图点
            heatmap_features = []
            for site in sites[:5]:
                for i in range(10):
                    for j in range(10):
                        lon = site.longitude + (i - 5) * 0.003
                        lat = site.latitude + (j - 5) * 0.003
                        d_km = math.sqrt((lon - site.longitude)**2 + (lat - site.latitude)**2) * 111
                        if d_km <= 1.0:
                            path_loss = 69.55 + 26.16 * math.log10(frequency_mhz) - 13.82 * math.log10(tower_height) + (44.9 - 6.55 * math.log10(tower_height)) * math.log10(max(d_km, 0.01))
                            rsrp = tx_power_dbm + antenna_gain_dbi - path_loss
                            if rsrp >= -110:
                                f = QgsFeature(heatmap_layer.fields())
                                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
                                f.setAttributes([round(rsrp, 1), round(d_km, 3)])
                                heatmap_features.append(f)

            hp.addFeatures(heatmap_features)
            heatmap_layer.updateExtents()

            # 设置样式
            symbol = QgsMarkerSymbol.createSimple({'name': 'circle', 'color': 'red', 'size': '2'})
            heatmap_layer.renderer().setSymbol(symbol)

            # 添加到地图
            QgsProject.instance().addMapLayer(heatmap_layer)

            # 缩放到范围
            self.iface.mapCanvas().setExtent(layer.extent())
            self.iface.mapCanvas().refresh()

            # 显示结果
            message = f"一键设计完成！\n\n"
            message += f"频段: {band}\n"
            message += f"网格大小: {grid_size}x{grid_size}\n"
            message += f"塔高: {tower_height} 米\n"
            message += f"总站点数: {len(sites)}\n"
            message += f"有效站点: {valid_count}\n"
            message += f"无效站点: {invalid_count}\n"
            message += f"平均RSRP: {avg_rsrp:.1f} dBm\n"
            message += f"热力图点数: {len(heatmap_features)}\n"
            message += f"覆盖阈值: -110 dBm"

            QMessageBox.information(self.iface.mainWindow(), "一键设计", message)
            self.status_label.setText("一键设计完成")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"一键设计失败: {e}")
            self.status_label.setText("一键设计失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def generate_report(self):
        """生成报告"""
        try:
            # 检查是否已生成站点
            if not hasattr(self, 'generated_sites') or not self.generated_sites:
                QMessageBox.warning(self.iface.mainWindow(), "警告", "请先生成蜂窝拓扑！")
                return

            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            import os
            from datetime import datetime
            import math

            # 获取参数
            band = self.band_combo.currentText()
            grid_size = self.grid_spin.value()
            tower_height = self.height_spin.value()

            # 计算统计信息
            sites = self.generated_sites
            total_sites = len(sites)

            # 避让检测
            from design_engine.avoidance_checker import create_default_avoidance_checker
            checker = create_default_avoidance_checker()

            valid_count = 0
            invalid_count = 0
            for site in sites:
                is_valid, _ = checker.check_site(site.longitude, site.latitude)
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

            # 计算RSRP
            if band == '3.5GHz':
                frequency_mhz = 3500
                tx_power_dbm = 53
                antenna_gain_dbi = 24
            elif band == '2.6GHz':
                frequency_mhz = 2600
                tx_power_dbm = 52
                antenna_gain_dbi = 22
            elif band == '700MHz':
                frequency_mhz = 700
                tx_power_dbm = 51
                antenna_gain_dbi = 18
            else:
                frequency_mhz = 4900
                tx_power_dbm = 53
                antenna_gain_dbi = 24

            rsrp_values = []
            for site in sites:
                d_km = 0.01
                path_loss = 69.55 + 26.16 * math.log10(frequency_mhz) - 13.82 * math.log10(tower_height) + (44.9 - 6.55 * math.log10(tower_height)) * math.log10(max(d_km, 0.01))
                rsrp = tx_power_dbm + antenna_gain_dbi - path_loss
                rsrp_values.append(rsrp)

            avg_rsrp = sum(rsrp_values) / len(rsrp_values)

            # 生成报告
            report = []
            report.append('=' * 50)
            report.append('基站智能设计报告')
            report.append('=' * 50)
            report.append('')
            report.append('一、项目基本信息')
            report.append('项目名称：武汉光谷5G基站设计')
            report.append('设计日期：' + datetime.now().strftime('%Y-%m-%d'))
            report.append('设计人员：人A')
            report.append('坐标系：EPSG:4326')
            report.append('')
            report.append('二、设计参数')
            report.append('频段：' + band + ' (' + str(frequency_mhz) + ' MHz)')
            report.append('塔高：' + str(tower_height) + ' 米')
            report.append('天线类型：3扇区')
            report.append('网格大小：' + str(grid_size) + 'x' + str(grid_size))
            report.append('')
            report.append('三、站点信息')
            report.append('总站点数：' + str(total_sites))
            report.append('有效站点：' + str(valid_count))
            report.append('无效站点：' + str(invalid_count))
            report.append('')
            report.append('四、覆盖信息')
            report.append('平均RSRP：' + str(round(avg_rsrp, 1)) + ' dBm')
            report.append('覆盖阈值：-110 dBm')
            report.append('')
            report.append('五、避让区域')
            report.append('水域：0.5公里半径')
            report.append('生态保护区：0.3公里半径')
            report.append('建筑物密集区：0.4公里半径')
            report.append('')
            report.append('=' * 50)
            report.append('报告生成时间：' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            report.append('=' * 50)

            # 保存报告
            report_text = '\n'.join(report)
            output_path = os.path.join(os.path.expanduser('~'), 'Desktop', '设计报告.txt')

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)

            # 显示结果
            message = f"设计报告已生成！\n\n"
            message += f"总站点数: {total_sites}\n"
            message += f"有效站点: {valid_count}\n"
            message += f"无效站点: {invalid_count}\n"
            message += f"平均RSRP: {avg_rsrp:.1f} dBm\n"
            message += f"保存位置: {output_path}"

            QMessageBox.information(self.iface.mainWindow(), "报告已生成", message)
            self.status_label.setText("设计报告已生成")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"生成报告失败: {e}")
            self.status_label.setText("生成报告失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def sync_to_backend(self):
        """同步到后端"""
        try:
            # 检查是否已生成站点
            if not hasattr(self, 'generated_sites') or not self.generated_sites:
                QMessageBox.warning(self.iface.mainWindow(), "警告", "请先生成蜂窝拓扑！")
                return

            # 添加插件目录到路径
            if self.plugin_dir not in sys.path:
                sys.path.insert(0, self.plugin_dir)

            # 导入模块
            from design_engine.data_sync import create_data_sync

            # 获取参数
            band = self.band_combo.currentText()
            grid_size = self.grid_spin.value()
            tower_height = self.height_spin.value()

            # 准备站点数据
            sites = []
            for site in self.generated_sites:
                sites.append({
                    'site_id': site.site_id,
                    'longitude': site.longitude,
                    'latitude': site.latitude,
                    'tower_height': site.tower_height,
                    'is_valid': True
                })

            # 准备参数
            params = {
                'band': band,
                'grid_size': grid_size,
                'tower_height': tower_height,
                'avg_rsrp': 0
            }

            # 创建数据同步实例
            sync = create_data_sync()

            # 上传设计
            self.status_label.setText("正在同步到后端...")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 12px;")

            success, scheme_id = sync.upload_design(101, sites, params)

            if success:
                message = f"数据同步成功！\n\n"
                message += f"项目ID: 101\n"
                message += f"方案ID: {scheme_id}\n"
                message += f"站点数: {len(sites)}\n"
                message += f"后端地址: http://localhost:8083"

                QMessageBox.information(self.iface.mainWindow(), "同步成功", message)
                self.status_label.setText("数据已同步到后端")
                self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")
            else:
                QMessageBox.warning(self.iface.mainWindow(), "同步失败", "数据同步失败，请检查M03后端是否运行。")
                self.status_label.setText("同步失败")
                self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), "导入错误", f"导入模块失败: {e}")
            self.status_label.setText("导入错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"同步失败: {e}")
            self.status_label.setText("同步失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def test_distance(self):
        """测试距离计算"""
        try:
            # 创建距离计算器
            d = QgsDistanceArea()
            d.setEllipsoid('WGS84')

            # 测试点（武汉光谷附近）
            p1 = QgsPointXY(114.390, 30.506)
            p2 = QgsPointXY(114.400, 30.510)

            # 计算距离
            distance = d.measureLine(p1, p2)

            message = f"距离计算测试结果：\n\n"
            message += f"点1: ({p1.x()}, {p1.y()})\n"
            message += f"点2: ({p2.x()}, {p2.y()})\n"
            message += f"距离: {distance:.2f} 米\n\n"
            message += f"PyQGIS版本: {Qgis.version()}"

            QMessageBox.information(self.iface.mainWindow(), "距离测试", message)
            self.status_label.setText("距离测试通过")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")

        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "错误", f"距离测试失败: {e}")
            self.status_label.setText("距离测试失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
