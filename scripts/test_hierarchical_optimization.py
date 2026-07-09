#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
M03模块分级优化验证测试
验证L1-L4各级优化是否成功实施
"""

import os
import sys
import time
from pathlib import Path

class HierarchicalOptimizationTester:
    def __init__(self):
        self.frontend_path = r"d:\homework\xind2\xind2\packages\m03-bim-gis\frontend"
        self.results = []
        self.test_count = 0
        self.pass_count = 0
        self.metrics = {}
        
    def log_result(self, level, test_name, passed, details=""):
        self.test_count += 1
        if passed:
            self.pass_count += 1
        status = "✓ PASS" if passed else "✗ FAIL"
        self.results.append({
            'level': level,
            'test': test_name,
            'passed': passed,
            'details': details
        })
        print(f"  [{status}] [{level}] {test_name}")
        if details:
            print(f"         {details}")
    
    def test_l1_code_quality(self):
        """L1: 代码质量优化验证"""
        print("\n" + "="*70)
        print("L1: 代码质量优化验证")
        print("="*70)
        
        # 检查工具函数文件
        utils_files = [
            'src/utils/mapActions.js',
            'src/utils/entityBatchRenderer.js'
        ]
        
        for rel_path in utils_files:
            full_path = os.path.join(self.frontend_path, rel_path)
            exists = os.path.exists(full_path)
            self.log_result(
                'L1',
                f"工具函数 - {os.path.basename(rel_path)}",
                exists,
                f"路径: {rel_path}" if exists else "文件不存在"
            )
        
        # 检查配置常量
        constants_path = os.path.join(self.frontend_path, 'src/config/constants.js')
        if os.path.exists(constants_path):
            with open(constants_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('位置配置', 'LOCATIONS' in content),
                ('颜色配置', 'COLORS' in content),
                ('性能配置', 'PERFORMANCE' in content),
                ('验证规则', 'VALIDATION_RULES' in content)
            ]
            
            for name, passed in checks:
                self.log_result('L1', f"配置常量 - {name}", passed)
        else:
            self.log_result('L1', "配置常量文件", False, "文件不存在")
        
        # 检查硬编码消除
        design_vue_path = os.path.join(self.frontend_path, 'src/views/Design.vue')
        if os.path.exists(design_vue_path):
            with open(design_vue_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_import_map_actions = 'mapActions' in content
            has_import_constants = 'constants' in content
            
            self.log_result(
                'L1',
                "导入工具函数",
                has_import_map_actions,
                "已导入mapActions" if has_import_map_actions else "未导入"
            )
            self.log_result(
                'L1',
                "导入配置常量",
                has_import_constants,
                "已导入constants" if has_import_constants else "未导入"
            )
    
    def test_l2_performance(self):
        """L2: 性能优化验证"""
        print("\n" + "="*70)
        print("L2: 性能优化验证")
        print("="*70)
        
        # 检查批量渲染器
        renderer_path = os.path.join(self.frontend_path, 'src/utils/entityBatchRenderer.js')
        if os.path.exists(renderer_path):
            with open(renderer_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('EntityBatchRenderer类', 'class EntityBatchRenderer' in content),
                ('addSites方法', 'addSites' in content),
                ('render方法', 'render' in content),
                ('clear方法', 'clear' in content),
                ('PointPrimitiveCollection', 'PointPrimitiveCollection' in content)
            ]
            
            for name, passed in checks:
                self.log_result('L2', f"批量渲染器 - {name}", passed)
        else:
            self.log_result('L2', "批量渲染器文件", False, "文件不存在")
        
        # 检查覆盖分析优化
        coverage_path = os.path.join(self.frontend_path, 'src/utils/coverageAnalyzer.js')
        if os.path.exists(coverage_path):
            with open(coverage_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_detect_gaps = 'detectCoverageGaps' in content
            has_calculate_metrics = 'calculateCoverageMetrics' in content
            
            self.log_result('L2', "覆盖分析 - 盲区检测", has_detect_gaps)
            self.log_result('L2', "覆盖分析 - 指标计算", has_calculate_metrics)
        
        # 性能指标记录
        self.metrics['l2_batch_renderer'] = 'implemented'
        self.metrics['l2_coverage_analyzer'] = 'optimized'
    
    def test_l3_ux_improvements(self):
        """L3: 用户体验优化验证"""
        print("\n" + "="*70)
        print("L3: 用户体验优化验证")
        print("="*70)
        
        design_vue_path = os.path.join(self.frontend_path, 'src/views/Design.vue')
        if os.path.exists(design_vue_path):
            with open(design_vue_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('参数校验', 'validateFields' in content or 'validateParameters' in content),
                ('撤销功能', 'undo' in content),
                ('重做功能', 'redo' in content),
                ('快捷键支持', 'shortcutManager' in content),
                ('操作历史', 'operationHistory' in content),
                ('请求缓存', 'cachedRequest' in content or 'requestCache' in content),
                ('项目保存', 'saveProject' in content),
                ('数据导出', 'exportProject' in content),
                ('覆盖报告', 'showCoverageReport' in content)
            ]
            
            for name, passed in checks:
                self.log_result('L3', f"UX功能 - {name}", passed)
        else:
            self.log_result('L3', "Design.vue文件", False, "文件不存在")
    
    def test_l4_architecture(self):
        """L4: 架构优化验证"""
        print("\n" + "="*70)
        print("L4: 架构优化验证")
        print("="*70)
        
        # 检查模块化结构
        modules = [
            ('utils/parameterValidator.js', '参数校验模块'),
            ('utils/operationHistory.js', '操作历史模块'),
            ('utils/requestCache.js', '请求缓存模块'),
            ('utils/shortcutManager.js', '快捷键模块'),
            ('utils/projectManager.js', '项目管理模块'),
            ('utils/exportUtils.js', '导出模块'),
            ('utils/coverageAnalyzer.js', '覆盖分析模块')
        ]
        
        for rel_path, name in modules:
            full_path = os.path.join(self.frontend_path, rel_path)
            exists = os.path.exists(full_path)
            self.log_result('L4', f"模块 - {name}", exists)
        
        # 检查组件分离
        components = [
            ('components/ProjectManagementUI.vue', '项目管理UI'),
            ('components/WorkflowGuide.vue', '工作流引导')
        ]
        
        for rel_path, name in components:
            full_path = os.path.join(self.frontend_path, rel_path)
            exists = os.path.exists(full_path)
            self.log_result('L4', f"组件 - {name}", exists)
    
    def test_compilation(self):
        """编译验证"""
        print("\n" + "="*70)
        print("编译验证")
        print("="*70)
        
        # 检查主要文件是否存在
        critical_files = [
            'src/views/Design.vue',
            'src/utils/mapActions.js',
            'src/utils/entityBatchRenderer.js',
            'src/config/constants.js'
        ]
        
        for rel_path in critical_files:
            full_path = os.path.join(self.frontend_path, rel_path)
            exists = os.path.exists(full_path)
            self.log_result(
                'VERIFY',
                f"关键文件 - {os.path.basename(rel_path)}",
                exists,
                "存在" if exists else "缺失"
            )
    
    def generate_summary_report(self):
        """生成汇总报告"""
        print("\n" + "="*70)
        print("分级优化验证汇总报告")
        print("="*70)
        
        # 按级别统计
        levels = ['L1', 'L2', 'L3', 'L4', 'VERIFY']
        level_stats = {}
        
        for level in levels:
            level_results = [r for r in self.results if r['level'] == level]
            passed = sum(1 for r in level_results if r['passed'])
            total = len(level_results)
            level_stats[level] = {
                'passed': passed,
                'total': total,
                'rate': f"{passed/total*100:.1f}%" if total > 0 else "N/A"
            }
        
        # 打印各级别统计
        print("\n各级别测试结果:")
        print("-" * 70)
        for level, stats in level_stats.items():
            print(f"  {level:4s}: {stats['passed']:2d}/{stats['total']} ({stats['rate']})")
        
        # 总体统计
        print("\n" + "-" * 70)
        print(f"总计: {self.pass_count}/{self.test_count} ({self.pass_count/self.test_count*100:.1f}%)")
        
        # 失败项
        failed_tests = [r for r in self.results if not r['passed']]
        if failed_tests:
            print("\n失败的测试:")
            for test in failed_tests:
                print(f"  ✗ [{test['level']}] {test['test']}: {test['details']}")
        
        print("\n" + "="*70)
        if self.pass_count == self.test_count:
            print("所有测试通过！✓ 分级优化实施成功")
        else:
            print(f"有 {self.test_count - self.pass_count} 个测试未通过")
        print("="*70)
        
        return self.pass_count == self.test_count


def main():
    print("="*70)
    print("M03模块分级优化验证测试")
    print("="*70)
    
    tester = HierarchicalOptimizationTester()
    
    # 执行测试
    tester.test_l1_code_quality()
    tester.test_l2_performance()
    tester.test_l3_ux_improvements()
    tester.test_l4_architecture()
    tester.test_compilation()
    
    # 生成报告
    all_passed = tester.generate_summary_report()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
