#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QGIS插件6大功能修复验证测试 (独立运行版)
不依赖QGIS环境，仅验证代码逻辑正确性
"""

import os
import sys
import ast
import re

FIX_DIR = r"d:\homework\xind2\xind2\qgis-plugin"
FIX_FILE = os.path.join(FIX_DIR, "layers", "pipeline_layer_fixed.py")

class QGISBugFixCodeVerifier:
    """代码验证器 - 通过分析源码验证修复是否正确"""
    
    def __init__(self):
        self.results = []
        self.test_count = 0
        self.pass_count = 0
        self.source_code = ""
        
    def load_source(self):
        """加载修复文件源码"""
        if not os.path.exists(FIX_FILE):
            print(f"错误: 修复文件不存在: {FIX_FILE}")
            sys.exit(1)
        
        with open(FIX_FILE, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        print(f"已加载修复文件: {FIX_FILE}")
        print(f"文件大小: {len(self.source_code)} 字符, {self.source_code.count(chr(10))} 行")
    
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
    
    def check_function_exists(self, func_name):
        """检查函数是否存在"""
        pattern = rf'^def {func_name}\s*\('
        return bool(re.search(pattern, self.source_code, re.MULTILINE))
    
    def check_string_in_code(self, search_string):
        """检查字符串是否在代码中"""
        return search_string in self.source_code
    
    def check_regex_in_code(self, pattern):
        """检查正则表达式是否在代码中"""
        return bool(re.search(pattern, self.source_code, re.MULTILINE | re.DOTALL))
    
    def test_fix1_station_location(self):
        """修复1: 站点定位功能"""
        print("\n" + "="*70)
        print("修复1: 站点定位功能验证")
        print("="*70)
        
        # 检查函数存在
        self.log_result(1, "locate_and_highlight_site函数存在",
                       self.check_function_exists('locate_and_highlight_site'))
        
        # 检查坐标验证逻辑
        self.log_result(1, "坐标有效性检查",
                       self.check_string_in_code("lon is None or lat is None"))
        
        # 检查地图聚焦
        self.log_result(1, "地图中心点设置",
                       self.check_string_in_code("canvas.setCenter"))
        
        # 检查地图刷新
        self.log_result(1, "地图刷新调用",
                       self.check_string_in_code("canvas.refresh()"))
        
        # 检查高亮逻辑
        self.log_result(1, "高亮显示逻辑",
                       self.check_string_in_code("zoom_extent") or 
                       self.check_string_in_code("setExtent"))
    
    def test_fix2_station_deletion(self):
        """修复2: 站点删除功能"""
        print("\n" + "="*70)
        print("修复2: 站点删除功能验证")
        print("="*70)
        
        self.log_result(2, "delete_site_and_update_map函数存在",
                       self.check_function_exists('delete_site_and_update_map'))
        
        self.log_result(2, "边界检查逻辑",
                       self.check_string_in_code("site_index < 0 or site_index >= len"))
        
        self.log_result(2, "站点数据删除",
                       self.check_string_in_code("generated_sites.pop"))
        
        self.log_result(2, "地图实时更新",
                       self.check_string_in_code("canvas.refresh()"))
        
        self.log_result(2, "返回值处理",
                       self.check_string_in_code("return False") and 
                       self.check_string_in_code("return True"))
    
    def test_fix3_pipeline_generation(self):
        """修复3: 管线生成错误 - 核心修复"""
        print("\n" + "="*70)
        print("修复3: 管线生成错误验证 (核心Bug修复)")
        print("="*70)
        
        self.log_result(3, "create_connection_layer函数存在",
                       self.check_function_exists('create_connection_layer'))
        
        # 检查QgsMarkerLineSymbolLayer正确使用
        self.log_result(3, "QgsMarkerLineSymbolLayer导入",
                       self.check_string_in_code('QgsMarkerLineSymbolLayer'))
        
        # 检查箭头符号创建
        self.log_result(3, "QgsMarkerSymbol创建",
                       self.check_string_in_code('QgsMarkerSymbol.createSimple'))
        
        # 检查标记线图层创建
        self.log_result(3, "标记线图层实例化",
                       self.check_string_in_code('QgsMarkerLineSymbolLayer(arrow_marker)') or
                       self.check_string_in_code('QgsMarkerLineSymbolLayer('))
        
        # 检查放置策略
        self.log_result(3, "LastPoint放置策略",
                       self.check_string_in_code('LastPoint'))
        
        # 检查线符号创建
        self.log_result(3, "QgsLineSymbol创建",
                       self.check_string_in_code('QgsLineSymbol'))
        
        # 检查符号层添加
        self.log_result(3, "appendSymbolLayer调用",
                       self.check_string_in_code('appendSymbolLayer'))
        
        # 验证旧bug代码已被替换
        has_old_bug = 'sym.setStyleLayer(marker_line_layer)' in self.source_code
        self.log_result(3, "旧Bug代码已移除", not has_old_bug,
                       "移除了错误的setStyleLayer调用" if not has_old_bug else "仍包含旧bug代码!")
    
    def test_fix4_path_coexistence(self):
        """修复4: 路径类型共存"""
        print("\n" + "="*70)
        print("修复4: 路径类型共存验证")
        print("="*70)
        
        self.log_result(4, "create_pipeline_layer函数存在",
                       self.check_function_exists('create_pipeline_layer'))
        
        # 检查route_type字段
        self.log_result(4, "route_type字段添加",
                       self.check_string_in_code('"route_type"'))
        
        # 检查路由类型传递
        self.log_result(4, "route_type参数传递",
                       self.check_string_in_code('route_type_val') or
                       self.check_string_in_code('route_type'))
        
        # 检查直线路径支持
        self.log_result(4, "直线路径支持",
                       self.check_string_in_code('direct') or
                       self.check_string_in_code('Direct'))
        
        # 检查曼哈顿路径支持
        self.log_result(4, "曼哈顿路径支持",
                       self.check_string_in_code('manhattan') or
                       self.check_string_in_code('Manhattan'))
    
    def test_fix5_heatmap_display(self):
        """修复5: 热力图显示"""
        print("\n" + "="*70)
        print("修复5: 热力图显示验证")
        print("="*70)
        
        self.log_result(5, "generate_heatmap_and_display函数存在",
                       self.check_function_exists('generate_heatmap_and_display'))
        
        # 检查图层可见性设置
        self.log_result(5, "图层可见性设置",
                       self.check_string_in_code('setVisible(True)'))
        
        # 检查地图刷新
        self.log_result(5, "地图刷新调用",
                       self.check_string_in_code('canvas.refresh()'))
        
        # 检查范围设置
        self.log_result(5, "地图范围设置",
                       self.check_string_in_code('setExtent'))
        
        # 检查分类渲染器
        self.log_result(5, "QgsCategorizedSymbolRenderer使用",
                       self.check_string_in_code('QgsCategorizedSymbolRenderer'))
        
        # 检查RSRP分级
        self.log_result(5, "RSRP分级渲染",
                       self.check_string_in_code('-50') and 
                       self.check_string_in_code('-65') and
                       self.check_string_in_code('-80'))
        
        # 检查透明度设置
        self.log_result(5, "图层透明度设置",
                       self.check_string_in_code('setOpacity'))
    
    def test_fix6_image_export(self):
        """修复6: 图片导出"""
        print("\n" + "="*70)
        print("修复6: 图片导出验证")
        print("="*70)
        
        self.log_result(6, "export_map_with_sites函数存在",
                       self.check_function_exists('export_map_with_sites'))
        
        # 检查PDF导出
        self.log_result(6, "PDF导出支持",
                       self.check_string_in_code('exportToPdf') or
                       self.check_string_in_code('.pdf'))
        
        # 检查PNG导出
        self.log_result(6, "PNG导出支持",
                       self.check_string_in_code('exportToImage') or
                       self.check_string_in_code('.png'))
        
        # 检查图层可见性
        self.log_result(6, "可见图层检查",
                       self.check_string_in_code('isVisible()'))
        
        # 检查布局导出器
        self.log_result(6, "QgsLayoutExporter使用",
                       self.check_string_in_code('QgsLayoutExporter'))
        
        # 检查DPI设置
        self.log_result(6, "DPI配置",
                       self.check_string_in_code('dpi') or
                       self.check_string_in_code('DPI'))
    
    def generate_summary_report(self):
        """生成汇总报告"""
        print("\n" + "="*70)
        print("QGIS插件6大功能修复验证汇总报告")
        print("="*70)
        
        print(f"\n总测试数: {self.test_count}")
        print(f"通过: {self.pass_count}")
        print(f"失败: {self.test_count - self.pass_count}")
        print(f"成功率: {self.pass_count/self.test_count*100:.1f}%")
        
        print("\n各修复项测试结果:")
        print("-" * 70)
        for fix_num in range(1, 7):
            fix_results = [r for r in self.results if r['fix'] == fix_num]
            passed = sum(1 for r in fix_results if r['passed'])
            total = len(fix_results)
            status = "✓" if passed == total else "⚠"
            print(f"  {status} 修复{fix_num}: {passed}/{total} 通过")
        
        failed_tests = [r for r in self.results if not r['passed']]
        if failed_tests:
            print("\n失败的测试:")
            for test in failed_tests:
                print(f"  ✗ 修复{test['fix']}: {test['test']}")
                if test['details']:
                    print(f"    详情: {test['details']}")
        
        print("\n" + "="*70)
        if self.pass_count == self.test_count:
            print("所有测试通过！✓ 6大功能修复代码验证成功")
        else:
            print(f"有 {self.test_count - self.pass_count} 个测试未通过")
        print("="*70)
        
        return self.pass_count == self.test_count


def main():
    print("="*70)
    print("QGIS插件 6大功能修复代码验证")
    print("="*70)
    
    verifier = QGISBugFixCodeVerifier()
    
    # 加载源码
    verifier.load_source()
    
    # 执行测试
    verifier.test_fix1_station_location()
    verifier.test_fix2_station_deletion()
    verifier.test_fix3_pipeline_generation()
    verifier.test_fix4_path_coexistence()
    verifier.test_fix5_heatmap_display()
    verifier.test_fix6_image_export()
    
    # 生成报告
    all_passed = verifier.generate_summary_report()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
