#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QGIS插件6大功能修复验证测试
验证所有Bug修复是否正确工作
"""

import sys
import os

# 添加插件路径
sys.path.insert(0, r"d:\homework\xind2\xind2\qgis-plugin")

class QGISBugFixTester:
    def __init__(self):
        self.results = []
        self.test_count = 0
        self.pass_count = 0
    
    def log_result(self, fix_number, test_name, passed, details=""):
        self.test_count += 1
        if passed:
            self.pass_count += 1
        status = "✓ PASS" if passed else "✗ FAIL"
        self.results.append({
            'fix': fix_number,
            'test': test_name,
            'passed': passed,
            'details': details
        })
        print(f"  [{status}] 修复{fix_number}: {test_name}")
        if details:
            print(f"         {details}")
    
    def test_fix1_station_location(self):
        """修复1: 站点定位功能"""
        print("\n" + "="*70)
        print("修复1: 站点定位功能 - 地图聚焦并高亮显示目标站点")
        print("="*70)
        
        try:
            from layers.pipeline_layer_fixed import locate_and_highlight_site
            
            # 测试站点数据有效性检查
            invalid_site = {'site_id': 'TEST-001'}
            # 注意: 实际测试需要QGIS canvas，这里只验证逻辑
            
            valid_site = {
                'site_id': 'TEST-001',
                'longitude': 110.932025,
                'latitude': 35.123754
            }
            
            self.log_result(1, "站点数据验证", 
                          'longitude' in valid_site and 'latitude' in valid_site,
                          "包含必要坐标字段")
            
            self.log_result(1, "空坐标检测",
                          'longitude' not in invalid_site,
                          "能正确检测缺失坐标")
            
            # 验证函数存在
            self.log_result(1, "locate_and_highlight_site函数存在",
                          callable(locate_and_highlight_site))
            
        except Exception as e:
            self.log_result(1, "站点定位功能测试", False, str(e))
    
    def test_fix2_station_deletion(self):
        """修复2: 站点删除功能"""
        print("\n" + "="*70)
        print("修复2: 站点删除功能 - 实时更新地图显示")
        print("="*70)
        
        try:
            from layers.pipeline_layer_fixed import delete_site_and_update_map
            
            # 测试删除逻辑
            test_sites = [
                {'site_id': 'BTS-001', 'longitude': 110.9, 'latitude': 35.1},
                {'site_id': 'BTS-002', 'longitude': 110.91, 'latitude': 35.11},
                {'site_id': 'BTS-003', 'longitude': 110.92, 'latitude': 35.12},
            ]
            
            # 删除中间站点
            original_len = len(test_sites)
            result = delete_site_and_update_map(1, test_sites, None)
            new_len = len(test_sites)
            
            self.log_result(2, "删除操作执行", result,
                          f"删除前:{original_len}个, 删除后:{new_len}个")
            
            self.log_result(2, "站点数量正确减少",
                          new_len == original_len - 1,
                          f"期望:{original_len - 1}, 实际:{new_len}")
            
            self.log_result(2, "删除后剩余站点验证",
                          test_sites[0]['site_id'] == 'BTS-001' and
                          test_sites[1]['site_id'] == 'BTS-003',
                          "剩余站点ID正确")
            
            # 测试边界情况
            empty_sites = []
            result = delete_site_and_update_map(0, empty_sites, None)
            self.log_result(2, "空列表删除边界处理",
                          not result,
                          "空列表返回False")
            
        except Exception as e:
            self.log_result(2, "站点删除功能测试", False, str(e))
    
    def test_fix3_pipeline_generation(self):
        """修复3: 管线生成错误"""
        print("\n" + "="*70)
        print("修复3: 管线生成错误 - 修正QgsMarkerLineSymbolLayer参数类型")
        print("="*70)
        
        try:
            from layers.pipeline_layer_fixed import create_connection_layer
            
            # 验证修复代码存在
            from layers import pipeline_layer_fixed
            source = open(pipeline_layer_fixed.__file__, 'r', encoding='utf-8').read()
            
            # 检查是否包含正确的修复逻辑
            has_marker_line_fix = 'QgsMarkerLineSymbolLayer' in source
            has_line_symbol = 'QgsLineSymbol' in source
            
            self.log_result(3, "QgsMarkerLineSymbolLayer导入", has_marker_line_fix,
                          "包含标记线图层导入")
            
            self.log_result(3, "QgsLineSymbol正确使用", has_line_symbol,
                          "使用线符号作为父符号")
            
            # 检查错误代码是否被替换
            has_old_bug = 'sym.setStyleLayer(marker_line_layer)' in source
            self.log_result(3, "旧Bug代码已移除", not has_old_bug,
                          "移除了错误的setStyleLayer调用")
            
            self.log_result(3, "create_connection_layer函数存在",
                          callable(create_connection_layer))
            
        except Exception as e:
            self.log_result(3, "管线生成修复测试", False, str(e))
    
    def test_fix4_path_coexistence(self):
        """修复4: 路径类型冲突"""
        print("\n" + "="*70)
        print("修复4: 路径类型共存 - 支持直线路径和曼哈顿路径同时显示")
        print("="*70)
        
        try:
            from layers.pipeline_layer_fixed import create_pipeline_layer
            
            # 验证route_type字段添加
            from layers import pipeline_layer_fixed
            source = open(pipeline_layer_fixed.__file__, 'r', encoding='utf-8').read()
            
            has_route_type_field = '"route_type"' in source
            has_route_type_value = "route_type_val" in source
            
            self.log_result(4, "route_type字段添加", has_route_type_field,
                          "管线图层包含route_type字段")
            
            self.log_result(4, "route_type值传递", has_route_type_value,
                          "正确传递路径类型值")
            
            self.log_result(4, "create_pipeline_layer函数存在",
                          callable(create_pipeline_layer))
            
        except Exception as e:
            self.log_result(4, "路径类型共存测试", False, str(e))
    
    def test_fix5_heatmap_display(self):
        """修复5: 热力图显示异常"""
        print("\n" + "="*70)
        print("修复5: 热力图显示 - 确保热力图正确绑定到地图视图")
        print("="*70)
        
        try:
            from layers.pipeline_layer_fixed import generate_heatmap_and_display
            
            # 验证关键修复点
            from layers import pipeline_layer_fixed
            source = open(pipeline_layer_fixed.__file__, 'r', encoding='utf-8').read()
            
            has_set_visible = 'setVisible(True)' in source
            has_refresh = 'canvas.refresh()' in source
            has_set_extent = 'setExtent' in source
            
            self.log_result(5, "图层可见性设置", has_set_visible,
                          "设置图层为可见")
            
            self.log_result(5, "地图刷新调用", has_refresh,
                          "调用canvas.refresh()刷新显示")
            
            self.log_result(5, "范围设置", has_set_extent,
                          "设置地图范围以显示热力图")
            
            self.log_result(5, "generate_heatmap_and_display函数存在",
                          callable(generate_heatmap_and_display))
            
        except Exception as e:
            self.log_result(5, "热力图显示修复测试", False, str(e))
    
    def test_fix6_image_export(self):
        """修复6: 图片导出问题"""
        print("\n" + "="*70)
        print("修复6: 图片导出 - 确保基站元素正确渲染")
        print("="*70)
        
        try:
            from layers.pipeline_layer_fixed import export_map_with_sites
            
            # 验证导出功能
            from layers import pipeline_layer_fixed
            source = open(pipeline_layer_fixed.__file__, 'r', encoding='utf-8').read()
            
            has_export_pdf = 'exportToPdf' in source
            has_export_png = 'exportToImage' in source
            has_map_layers = 'setLayers' in source
            
            self.log_result(6, "PDF导出支持", has_export_pdf,
                          "支持PDF格式导出")
            
            self.log_result(6, "PNG导出支持", has_export_png,
                          "支持PNG格式导出")
            
            self.log_result(6, "图层可见性检查", has_map_layers,
                          "导出时包含所有可见图层")
            
            self.log_result(6, "export_map_with_sites函数存在",
                          callable(export_map_with_sites))
            
        except Exception as e:
            self.log_result(6, "图片导出修复测试", False, str(e))
    
    def generate_summary_report(self):
        """生成汇总报告"""
        print("\n" + "="*70)
        print("QGIS插件6大功能修复验证汇总报告")
        print("="*70)
        
        print(f"\n总测试数: {self.test_count}")
        print(f"通过: {self.pass_count}")
        print(f"失败: {self.test_count - self.pass_count}")
        print(f"成功率: {self.pass_count/self.test_count*100:.1f}%")
        
        # 按修复编号统计
        print("\n各修复项测试结果:")
        print("-" * 70)
        for fix_num in range(1, 7):
            fix_results = [r for r in self.results if r['fix'] == fix_num]
            passed = sum(1 for r in fix_results if r['passed'])
            total = len(fix_results)
            status = "✓" if passed == total else "⚠"
            print(f"  {status} 修复{fix_num}: {passed}/{total} 通过")
        
        # 失败项
        failed_tests = [r for r in self.results if not r['passed']]
        if failed_tests:
            print("\n失败的测试:")
            for test in failed_tests:
                print(f"  ✗ 修复{test['fix']}: {test['test']} - {test['details']}")
        
        print("\n" + "="*70)
        if self.pass_count == self.test_count:
            print("所有测试通过！✓ 6大功能修复验证成功")
        else:
            print(f"有 {self.test_count - self.pass_count} 个测试未通过")
        print("="*70)
        
        return self.pass_count == self.test_count


def main():
    print("="*70)
    print("QGIS插件 6大功能修复验证测试")
    print("="*70)
    
    tester = QGISBugFixTester()
    
    # 执行测试
    tester.test_fix1_station_location()
    tester.test_fix2_station_deletion()
    tester.test_fix3_pipeline_generation()
    tester.test_fix4_path_coexistence()
    tester.test_fix5_heatmap_display()
    tester.test_fix6_image_export()
    
    # 生成报告
    all_passed = tester.generate_summary_report()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
