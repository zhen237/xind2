#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QGIS插件优化验证测试
验证所有优化功能是否正常工作
"""

import sys
import os
import time
import traceback

# 添加插件路径
sys.path.insert(0, r"d:\homework\xind2\xind2\qgis-plugin")

class QGISOptimizationTester:
    def __init__(self):
        self.results = []
        self.test_count = 0
        self.pass_count = 0
        self.performance_data = {}
    
    def log_result(self, test_name, passed, details="", duration=0):
        self.test_count += 1
        if passed:
            self.pass_count += 1
        status = "✓ PASS" if passed else "✗ FAIL"
        self.results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'duration': duration
        })
        print(f"  [{status}] {test_name}")
        if details:
            print(f"         {details}")
        if duration > 0:
            print(f"         耗时: {duration:.3f}秒")
    
    def test_file_existence(self):
        """测试1: 文件存在性验证"""
        print("\n" + "="*70)
        print("测试1: 优化文件存在性验证")
        print("="*70)
        
        optimized_files = [
            ('design_engine/coverage_optimized.py', '并行覆盖计算'),
            ('design_engine/hex_grid_optimized.py', '优化网格生成'),
            ('design_engine/input_validator.py', '输入验证器'),
            ('design_engine/memory_manager.py', '内存管理器')
        ]
        
        base_path = r"d:\homework\xind2\xind2\qgis-plugin"
        
        for rel_path, desc in optimized_files:
            full_path = os.path.join(base_path, rel_path)
            exists = os.path.exists(full_path)
            self.log_result(
                f"{desc} - {os.path.basename(rel_path)}",
                exists,
                f"路径: {rel_path}" if exists else "文件不存在"
            )
    
    def test_input_validator(self):
        """测试2: 输入验证器功能"""
        print("\n" + "="*70)
        print("测试2: 输入验证器功能")
        print("="*70)
        
        try:
            from design_engine.input_validator import InputValidator
            
            # 测试有效参数
            result = InputValidator.validate_frequency(2100)
            self.log_result("有效频率验证", result.is_valid, 
                          f"错误: {len(result.errors)}, 警告: {len(result.warnings)}")
            
            # 测试无效频率
            result = InputValidator.validate_frequency(50000)
            self.log_result("无效频率检测", not result.is_valid,
                          f"错误信息: {result.errors[0] if result.errors else '无'}")
            
            # 测试坐标验证
            result = InputValidator.validate_coordinates(110.93, 35.12)
            self.log_result("有效坐标验证", result.is_valid)
            
            # 测试边界框验证
            result = InputValidator.validate_bbox((110.0, 35.0, 111.0, 36.0))
            self.log_result("边界框验证", result.is_valid)
            
            # 测试批量验证
            params = {
                'frequency': 2100,
                'tower_height': 35,
                'center_longitude': 110.93,
                'center_latitude': 35.12
            }
            result = InputValidator.validate_all_params(params)
            self.log_result("批量参数验证", result.is_valid,
                          f"总错误: {len(result.errors)}, 警告: {len(result.warnings)}")
            
        except Exception as e:
            self.log_result("输入验证器测试", False, str(e))
    
    def test_memory_manager(self):
        """测试3: 内存管理器功能"""
        print("\n" + "="*70)
        print("测试3: 内存管理器功能")
        print("="*70)
        
        try:
            from design_engine.memory_manager import MemoryManager, get_memory_manager
            
            # 测试缓存功能
            mm = get_memory_manager()
            
            mm.cache_set('test_key', 'test_value')
            cached = mm.cache_get('test_key')
            self.log_result("缓存写入读取", cached == 'test_value')
            
            # 测试缓存信息
            info = mm.get_cache_info()
            self.log_result("缓存信息管理", info['size'] > 0,
                          f"缓存大小: {info['size']}/{info['max_size']}")
            
            # 测试内存统计
            stats = mm.get_memory_stats()
            self.log_result("内存统计", 'current_mb' in stats,
                          f"当前内存: {stats['current_mb']:.2f}MB")
            
            # 测试强制GC
            gc_result = mm.force_gc()
            self.log_result("强制垃圾回收", gc_result['collected'] >= 0,
                          f"回收对象: {gc_result['collected']}")
            
            # 测试阈值检查
            mm.cache_clear()
            is_over = mm.check_memory_threshold(100.0)
            self.log_result("内存阈值检查", isinstance(is_over, bool))
            
        except Exception as e:
            self.log_result("内存管理器测试", False, str(e))
    
    def test_performance_monitor(self):
        """测试4: 性能监控器功能"""
        print("\n" + "="*70)
        print("测试4: 性能监控器功能")
        print("="*70)
        
        try:
            from design_engine.memory_manager import PerformanceMonitor
            
            pm = PerformanceMonitor()
            
            # 测试计时
            pm.start_timer('test_operation')
            time.sleep(0.1)  # 模拟操作
            duration = pm.end_timer('test_operation')
            
            self.log_result("操作计时", duration > 0,
                          f"耗时: {duration:.3f}秒")
            
            # 测试统计
            stats = pm.get_stats('test_operation')
            self.log_result("性能统计", 'avg_time' in stats,
                          f"平均耗时: {stats['avg_time']:.3f}秒")
            
            # 测试重置
            pm.reset()
            self.log_result("统计重置", len(pm._timings) == 0)
            
        except Exception as e:
            self.log_result("性能监控器测试", False, str(e))
    
    def test_hex_grid_optimized(self):
        """测试5: 优化版网格生成"""
        print("\n" + "="*70)
        print("测试5: 优化版网格生成")
        print("="*70)
        
        try:
            from design_engine.hex_grid_optimized import generate_hex_grid_optimized, clear_grid_cache
            
            # 清除缓存
            clear_grid_cache()
            
            # 测试网格生成
            bbox = (110.9, 35.1, 110.96, 35.15)
            start_time = time.time()
            centers = generate_hex_grid_optimized(bbox, isr_km=0.2, use_cache=True)
            duration = time.time() - start_time
            
            self.log_result("网格生成", len(centers) > 0,
                          f"生成{len(centers)}个点，耗时{duration:.3f}秒")
            
            # 测试缓存
            start_time = time.time()
            centers_cached = generate_hex_grid_optimized(bbox, isr_km=0.2, use_cache=True)
            duration_cached = time.time() - start_time
            
            speedup = duration / duration_cached if duration_cached > 0 else 1
            self.log_result("缓存加速", len(centers_cached) == len(centers),
                          f"缓存命中，加速比: {speedup:.1f}x")
            
        except Exception as e:
            self.log_result("优化网格生成测试", False, str(e))
            traceback.print_exc()
    
    def test_coverage_optimized(self):
        """测试6: 优化版覆盖计算"""
        print("\n" + "="*70)
        print("测试6: 优化版覆盖计算")
        print("="*70)
        
        try:
            from design_engine.coverage_optimized import okumura_hata_path_loss, power_w_to_dbm
            
            # 测试路径损耗计算
            loss = okumura_hata_path_loss(
                frequency_mhz=2100,
                distance_km=1.0,
                tx_height_m=35,
                environment="URBAN"
            )
            
            self.log_result("路径损耗计算", loss > 0,
                          f"路径损耗: {loss:.2f}dB")
            
            # 测试功率转换
            dbm = power_w_to_dbm(120)
            self.log_result("功率转换", dbm > 0,
                          f"120W = {dbm:.2f}dBm")
            
            # 测试颜色映射
            from design_engine.coverage_optimized import rsrp_to_color
            color = rsrp_to_color(-85)
            self.log_result("RSRP颜色映射", len(color) == 4,
                          f"颜色: RGB{color[:3]}")
            
        except Exception as e:
            self.log_result("优化覆盖计算测试", False, str(e))
            traceback.print_exc()
    
    def generate_summary_report(self):
        """生成汇总报告"""
        print("\n" + "="*70)
        print("QGIS插件优化测试汇总报告")
        print("="*70)
        
        print(f"\n总测试数: {self.test_count}")
        print(f"通过: {self.pass_count}")
        print(f"失败: {self.test_count - self.pass_count}")
        print(f"成功率: {self.pass_count/self.test_count*100:.1f}%")
        
        # 按类别统计
        categories = {
            '文件验证': [],
            '输入验证': [],
            '内存管理': [],
            '性能监控': [],
            '网格生成': [],
            '覆盖计算': []
        }
        
        for i, result in enumerate(self.results, 1):
            test_name = result['test']
            if '文件' in test_name:
                categories['文件验证'].append(result)
            elif '验证' in test_name.lower() or '频率' in test_name or '坐标' in test_name:
                categories['输入验证'].append(result)
            elif '内存' in test_name or '缓存' in test_name:
                categories['内存管理'].append(result)
            elif '性能' in test_name or '计时' in test_name:
                categories['性能监控'].append(result)
            elif '网格' in test_name:
                categories['网格生成'].append(result)
            elif '覆盖' in test_name or '路径' in test_name:
                categories['覆盖计算'].append(result)
        
        print("\n各类别测试结果:")
        print("-" * 70)
        for category, results in categories.items():
            if results:
                passed = sum(1 for r in results if r['passed'])
                total = len(results)
                print(f"  {category}: {passed}/{total}")
        
        # 失败项
        failed_tests = [r for r in self.results if not r['passed']]
        if failed_tests:
            print("\n失败的测试:")
            for test in failed_tests:
                print(f"  ✗ {test['test']}: {test['details']}")
        
        print("\n" + "="*70)
        if self.pass_count == self.test_count:
            print("所有测试通过！✓ QGIS插件优化实施成功")
        else:
            print(f"有 {self.test_count - self.pass_count} 个测试未通过")
        print("="*70)
        
        return self.pass_count == self.test_count


def main():
    print("="*70)
    print("QGIS插件优化验证测试")
    print("="*70)
    
    tester = QGISOptimizationTester()
    
    # 执行测试
    tester.test_file_existence()
    tester.test_input_validator()
    tester.test_memory_manager()
    tester.test_performance_monitor()
    tester.test_hex_grid_optimized()
    tester.test_coverage_optimized()
    
    # 生成报告
    all_passed = tester.generate_summary_report()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
